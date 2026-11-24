"""
Goal-Oriented Voice-First Skill Router, Lightweight Entity Matcher,
0ms Conversational Fillers, and 0-LLM Pending Action Executor (`src/agent/voice_skills.py`).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from src.agent.schemas import SessionState


@dataclass(frozen=True)
class VoiceSkill:
    """A focused capability bundle with concise prompt guidance and <=4 tools."""

    name: str
    prompt_snippet: str
    tool_names: Tuple[str, ...]
    needs_retrieval: bool = False


VOICE_SKILLS: Dict[str, VoiceSkill] = {
    "vehicle_discovery": VoiceSkill(
        name="vehicle_discovery",
        prompt_snippet=(
            "当前目标：选车与对比咨询。请用口语化短句直接给出最匹配车型或两款车的核心差异"
            "（只讲价格、续航/动力、空间3个维度），每次只推进一个焦点，不超过80字。"
        ),
        tool_names=(
            "search_vehicles",
            "compare_two_vehicles",
            "get_vehicle_detail",
            "check_constraint_conflicts",
        ),
        needs_retrieval=True,
    ),
    "pricing_finance": VoiceSkill(
        name="pricing_finance",
        prompt_snippet=(
            "当前目标：落地价、金融月供、优惠与二手车置换估价咨询。直接调用算价、金融或置换估价工具给出清晰数字，"
            "用口语短句播报首付、月供、优惠或残值区间，禁止使用列表和Markdown，不超过80字。"
        ),
        tool_names=(
            "calculate_drive_away_price",
            "calculate_financing_plan",
            "query_dealer_promotions",
            "estimate_trade_in_valuation",
        ),
        needs_retrieval=False,
    ),
    "dealer_visit": VoiceSkill(
        name="dealer_visit",
        prompt_snippet=(
            "当前目标：门店信息咨询。直接查询门店地址、停车、营业时间及今日展车/试驾车时段，"
            "口语化简明回复，不超过80字。"
        ),
        tool_names=("query_dealer_info",),
        needs_retrieval=False,
    ),
    "test_drive_booking": VoiceSkill(
        name="test_drive_booking",
        prompt_snippet=(
            "当前目标：试驾预约/改期/取消/查询。创建或改期前必须确认手机号、门店和时间；"
            "信息齐全时口语复述关键信息请客户确认，不超过80字。"
        ),
        tool_names=(
            "manage_test_drive",
            "query_dealer_info",
            "validate_test_drive_slot",
        ),
        needs_retrieval=False,
    ),
    "advisor_handoff": VoiceSkill(
        name="advisor_handoff",
        prompt_snippet=(
            "当前目标：转接人工销售顾问。礼貌告知已同步需求并安排专属顾问联系，不超过60字。"
        ),
        tool_names=("handoff_to_sales_advisor",),
        needs_retrieval=False,
    ),
    "general_chat": VoiceSkill(
        name="general_chat",
        prompt_snippet=(
            "当前目标：自然口语对话引导。简短亲切回应客户并顺势引导其说出看车、算价或试驾需求，不超过60字。"
        ),
        tool_names=(),
        needs_retrieval=False,
    ),
}

TOOL_FILLERS: Dict[str, str] = {
    "search_vehicles": "好的，我帮您找一下合适的车型，请稍等。",
    "compare_two_vehicles": "行，我帮您对比一下这两款车的核心差异。",
    "get_vehicle_detail": "好的，我帮您查一下这款车的具体参数。",
    "check_constraint_conflicts": "我帮您核对一下这几个条件能不能兼顾。",
    "calculate_drive_away_price": "好的，我帮您算一下落地价，稍等。",
    "estimate_trade_in_valuation": "好的，我帮您查一下这台车的保值率和置换估价区间。",
    "calculate_financing_plan": "没问题，我帮您算一下首付和月供方案。",
    "query_dealer_promotions": "我帮您查一下门店最新的优惠政策。",
    "query_dealer_info": "好的，我帮您查一下门店信息和可约时段。",
    "validate_test_drive_slot": "我帮您核对一下预约信息。",
    "manage_test_drive": "好的，我帮您处理试驾预约。",
    "submit_test_drive_reservation": "好的，我帮您核对并提交试驾预约。",
    "handoff_to_sales_advisor": "好的，我马上为您转接专属销售顾问。",
}

VOICE_EXPRESSION_PROTOCOL = (
    "[Voice-First 口语表达协议]\n"
    "1. 严禁使用任何 Markdown（如 **、#、-、1.、代码块）或括号注释。\n"
    "2. 必须使用自然口语短句，单轮总字数严格控制在80字以内。\n"
    "3. 每次只说清一个核心信息或只问一个问题，禁止连续追问。"
)

_AFFIRM_RE = re.compile(
    r"^(好|好的|好啊|好嘞|行|行吧|可以|可以的|没问题|对|对的|是的|没错|确认|嗯|OK|ok|那就这样|就这么定了|帮我提交|提交吧|请帮我提交)"
    r"(?:[，,、\s]*(?:确认|提交|提交吧|帮我提交|就这么定了|没问题|可以|好的))?[！!。,.，~？?]*$"
)
_REJECT_RE = re.compile(
    r"^(不|不对|不是|不行|不用|不要|算了|取消|改一下|换个|重新)[！!。,.，~？?]*$"
)

_HANDOFF_RE = re.compile(r"转人工|人工客服|真人|找顾问|销售经理|投诉")
_TEST_DRIVE_RE = re.compile(r"试驾|预约|约个|改期|改约|取消预约|查预约|几点去试")
_DEALER_INFO_RE = re.compile(r"营业时间|几点关门|几点开门|地址|在哪|怎么走|停车|车位|展车|门店")
_PRICING_RE = re.compile(r"落地价|多少钱|首付|月供|分期|贷款|利率|优惠|补贴|折扣|置换|全款|估价|保值率|二手车")
_DISCOVERY_RE = re.compile(
    r"推荐|选车|买车|对比|区别|哪个好|续航|纯电|增程|插混|混动|油车|SUV|轿车|MPV|猎装|万左右|万以内|预算"
)

_BUDGET_RE = re.compile(r"(\d+(?:\.\d+)?)\s*万")
_PHONE_RE = re.compile(r"(1[3-9]\d{9})")
_KNOWN_BRANDS = (
    "小米",
    "特斯拉",
    "理想",
    "比亚迪",
    "问界",
    "极氪",
    "蔚来",
    "小鹏",
    "宝马",
    "奔驰",
    "奥迪",
    "丰田",
    "本田",
    "大众",
)


@dataclass
class SkillRouteResult:
    """Result of microsecond goal-oriented skill & entity routing."""

    skill: VoiceSkill
    entities: Dict[str, Any] = field(default_factory=dict)
    is_affirm: bool = False
    is_reject: bool = False
    semantic_intent: Optional[str] = None


def extract_lightweight_entities(text: str) -> Dict[str, Any]:
    """Extract key entities (<1ms, zero LLM) for hot-path pre-retrieval & validation."""
    entities: Dict[str, Any] = {}
    if not text:
        return entities

    m_budget = _BUDGET_RE.findall(text)
    if m_budget:
        nums = [float(x) for x in m_budget]
        if len(nums) >= 2:
            entities["budget_min"] = min(nums[0], nums[1])
            entities["budget_max"] = max(nums[0], nums[1])
        else:
            entities["budget_max"] = nums[0]

    for kw, ptype in (
        ("纯电", "纯电"),
        ("增程", "增程"),
        ("插混", "插混"),
        ("混动", "插混"),
        ("燃油", "燃油"),
        ("油车", "燃油"),
    ):
        if kw in text:
            entities["powertrain_type"] = ptype
            break

    matched_brands = [b for b in _KNOWN_BRANDS if b in text]
    if matched_brands:
        entities["brands"] = matched_brands

    m_phone = _PHONE_RE.search(text)
    if m_phone:
        entities["phone_number"] = m_phone.group(1)

    for store in ("朝阳", "海淀"):
        if store in text:
            entities["store_name"] = store
            break

    return entities


def route_voice_skill(
    user_message: str,
    semantic_decision: Optional[Any] = None,
    session_state: Optional[SessionState] = None,
) -> SkillRouteResult:
    """Route user utterance to a focused VoiceSkill in microseconds (<1ms)."""
    text = (user_message or "").strip()
    entities = extract_lightweight_entities(text)
    sem_intent = (
        getattr(semantic_decision, "intent", None)
        if semantic_decision is not None and getattr(semantic_decision, "matched", False)
        else None
    )

    is_affirm = sem_intent == "affirm" or bool(_AFFIRM_RE.match(text))
    is_reject = sem_intent == "reject" or bool(_REJECT_RE.match(text))

    if _HANDOFF_RE.search(text):
        skill = VOICE_SKILLS["advisor_handoff"]
    elif _TEST_DRIVE_RE.search(text):
        skill = VOICE_SKILLS["test_drive_booking"]
    elif _DEALER_INFO_RE.search(text):
        skill = VOICE_SKILLS["dealer_visit"]
    elif _PRICING_RE.search(text):
        skill = VOICE_SKILLS["pricing_finance"]
    elif _DISCOVERY_RE.search(text) or entities.get("brands") or entities.get("budget_max") or sem_intent in (
        "budget",
        "powertrain",
        "usage",
        "request_detail",
        "update_constraint",
    ):
        skill = VOICE_SKILLS["vehicle_discovery"]
    elif session_state is not None and session_state.pending_action and (is_affirm or is_reject):
        skill = VOICE_SKILLS["test_drive_booking"]
    else:
        skill = VOICE_SKILLS["general_chat"]

    return SkillRouteResult(
        skill=skill,
        entities=entities,
        is_affirm=is_affirm,
        is_reject=is_reject,
        semantic_intent=sem_intent,
    )


def get_filler_for_tool(tool_name: str) -> str:
    """Return a 0ms natural conversational filler for `tool_name`."""
    return TOOL_FILLERS.get(tool_name, "好的，我帮您查一下，请稍等。")


def format_pending_action_oral_prompt(tool_name: str, args: Dict[str, Any]) -> str:
    """Build a concise oral confirmation prompt (no UI card) for a staged write action."""
    if tool_name in ("manage_test_drive", "submit_test_drive_reservation"):
        action = args.get("action", "create")
        car = args.get("car_model") or "试驾车型"
        date = args.get("reservation_date") or "近期"
        time_slot = args.get("reservation_time") or ""
        loc = args.get("reservation_location") or "门店"
        phone = args.get("phone_number") or ""
        if action == "cancel":
            return f"确认帮您取消{loc}的{car}试驾预约吗？"
        verb = "改期到" if action == "reschedule" else "预约"
        phone_tail = f"，手机号尾号{phone[-4:]}" if len(phone) >= 4 else ""
        return f"帮您{verb}{date}{time_slot}去{loc}试驾{car}{phone_tail}，确认提交吗？"
    return "关键信息已为您核对好，确认现在帮您提交吗？"


def execute_pending_action(pending_action: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    0-LLM direct execution of a staged write tool after user oral affirmation.

    Returns (success, spoken_reply, raw_payload).
    """
    from src.agent.langchain_tools import (
        manage_test_drive_tool,
        submit_test_drive_reservation_tool,
    )

    tool_name = str(pending_action.get("tool_name") or "")
    args = dict(pending_action.get("args") or {})
    tool_map = {
        "manage_test_drive": manage_test_drive_tool,
        "submit_test_drive_reservation": submit_test_drive_reservation_tool,
    }
    target_tool = tool_map.get(tool_name)
    if target_tool is None:
        return False, "抱歉，待确认操作已失效，请重新告诉我您的需求。", {}

    try:
        raw_str = target_tool.invoke(args)
        payload = json.loads(raw_str) if isinstance(raw_str, str) else {}
    except Exception as exc:
        return False, "抱歉，提交预约时遇到点问题，请稍后再试。", {"error": str(exc)}

    if payload.get("submitted"):
        action = payload.get("action", "create")
        if action == "cancel":
            return True, "好的，已经帮您取消这次试驾预约了，有需要随时再联系我。", payload
        car = payload.get("car_model") or args.get("car_model") or "试驾车"
        date = payload.get("reservation_date") or args.get("reservation_date") or ""
        time_slot = payload.get("reservation_time") or args.get("reservation_time") or ""
        loc = payload.get("reservation_location") or args.get("reservation_location") or "门店"
        verb = "改约好了" if action == "reschedule" else "约好了"
        return True, f"好的，已经帮您{verb}{date}{time_slot}去{loc}试驾{car}，到时候直接到店就行。", payload

    err = payload.get("error") or "信息还不完整"
    return False, f"还差一点信息没核对上，{err}，您补充一下我马上帮您办。", payload
