"""
Dynamic Intent Interruptibility & Topic Hopping Engine (src/agent/topic_manager.py).

Enables flexible, mixed-initiative dialog management with enterprise guardrails:
1. Detects spontaneous technical questions, spec inquiries, competitor comparisons,
   and out-of-order slots (Topic Hopping & Side Questions).
2. Manages an interrupted goal stack on SessionState so the agent can answer user side-questions directly
   and smoothly resume prior sales objectives without state-machine deadlocks.
3. Coordinates with Anti-Loop Circuit Breaker to prevent false-positive rejection trips
   during healthy multi-turn technical consultations.
4. Supports Multi-Intent Joint Fulfillment: simultaneously answers inquiries while
   opportunistically capturing customer profile, needs, and booking slots.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.agent.schemas import SessionState, Stage

logger = logging.getLogger(__name__)


class UserDialogueIntent(str, Enum):
    """User dialogue intent classification."""

    SALES_PROGRESSION = "sales_progression"  # Direct answer to sales step (e.g. provides budget, name, date)
    SIDE_QUESTION = "side_question"          # Spontaneous technical / spec question or side inquiry
    SPEC_COMPARISON = "spec_comparison"      # Compares two or more cars / technologies
    CONSTRAINT_UPDATE = "constraint_update"  # Modifies previously stated budget/preference
    OBJECTION_OR_CHALLENGE = "objection"    # Challenges price, delivery date, range, safety
    MULTI_INTENT = "multi_intent"            # Combines a question with new slot information
    CHITCHAT = "chitchat"                    # Off-topic small talk or greeting


@dataclass
class TopicAnalysisResult:
    """Result of conversational topic and intent inspection."""

    intent: UserDialogueIntent
    is_interrupt: bool
    is_multi_intent: bool
    topic_label: str = ""
    detected_entities: List[str] = field(default_factory=list)
    suggested_directive: str = ""
    extracted_slots_hint: Dict[str, Any] = field(default_factory=dict)
    resumed_goal: Optional[Dict[str, Any]] = None
    negative_constraints: Dict[str, Any] = field(default_factory=dict)


# Patterns identifying side questions and technical consultations
TECHNICAL_QUERY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"零百|百公里加速|加速几秒|破百|能跑多快|最高车速|极速"), "动力性能与加速"),
    (re.compile(r"续航|跑多少公里|纯电续航|能跑多远|耗电|电耗|省油|油耗"), "续航与能耗表现"),
    (re.compile(r"电池(?:容量|包|品牌|供应商|类型|安全)?|三元锂|磷酸铁锂|麒麟电池|神行电池|刀片电池|电芯|自燃|起火|温控"), "电池安全与规格"),
    (re.compile(r"电机|转速|hyperengine|双电机|单电机|马力|扭矩|功率"), "电机动力与转速"),
    (re.compile(r"800v|碳化硅|高压平台|快充|超充|充满要多久|充电速度"), "高压超快充架构"),
    (re.compile(r"智驾|辅助驾驶|自动驾驶|英伟达|orin|算力|激光雷达|高速领航|城市领航|nob"), "智能驾驶与辅助感知"),
    (re.compile(r"后备箱|空间|轴距|长宽高|尺寸|储物|几座|坐几个人"), "车身尺寸与空间"),
    (re.compile(r"底盘|悬挂|空气悬架|空悬|cdc|双叉臂|多连杆|云辇|魔毯"), "底盘操控与舒适性"),
    (re.compile(r"对比|区别|差距|差别|比一比|更推荐|哪个好|vs|PK"), "跨车型横向对比"),
    (re.compile(r"优惠|降价|便宜点|能少多少|落地价|保险费|购置税|送什么"), "价格与提车权益"),
    (re.compile(r"现车|提车周期|等多久|门店地址|营业时间|电话多少"), "门店服务与提车周期"),
    (re.compile(r"刹车|制动|踏板|踩断|踩不动|卡钳|刹停|百公里刹车|失灵|线控"), "制动安全与线控踏板"),
    (re.compile(r"保值率|保值|残值|折旧|二手车|跌价|贬值|腰斩"), "二手残值与保值率"),
    (re.compile(r"碰撞|安全|中保研|c-ncap|iihs|a柱|气囊|刚度|防撞梁"), "车身安全与碰撞评级"),
]

# Patterns identifying slot updates provided out of order
SLOT_HINT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b1[3-9]\d{9}\b"), "phone_number"),
    (re.compile(r"(?:我叫|姓名|叫我|先生|女士|本人|我是|我姓)\s*([^\s，,。]{1,6})"), "name"),
    (re.compile(r"(\d+(?:\.\d+)?)\s*万|\d+W|\d+w|预算(?:\s*[\d一二两三四五六七八九十百]+(?:\s*[-至到]\s*[\d一二两三四五六七八九十百]+)?\s*万?)"), "price"),
    (re.compile(r"(?:明天|后天|大后天|这周(?:末|[一二三四五六日天])?|下周(?:末|[一二三四五六日天])?|本周(?:末|[一二三四五六日天])?|周[一二三四五六日天]|星期[一二三四五六日天]|\d{1,2}月\d{1,2}[日号]|(?:[12]?\d|3[01])[日号](?![汽油]))"), "reservation_date"),
    (re.compile(r"(?:上午|下午|晚上|中午|早晨|\d{1,2}点(?:\d{1,2}分)?|\d{1,2}:\d{2})"), "reservation_time"),
    (re.compile(r"(?:店|体验中心|4s店|交付中心)", re.IGNORECASE), "reservation_location"),
    (re.compile(r"(?:纯电|插混|增程|油电混动)"), "powertrain_type"),
    (re.compile(r"(?:suv|轿车|mpv|猎装|轿跑|跑车|两厢|三厢|旅行车|越野)", re.IGNORECASE), "vehicle_category_bottom"),
]

QUESTION_CLUES_PATTERN = re.compile(
    r"[?？]|是多少|几秒|多大|多久|有没有|是不是|能不能|哪个好|怎么|如何|什么|吗|呢|到底|怎么样|多少钱|查下|请问|帮查|知道.*吗"
)
COMPARISON_CLUES_PATTERN = re.compile(
    r"对比|相比|PK|vs|VS|差距|区别|差别|比一比|更推荐|哪个好|选哪个"
)
REQUIREMENT_STATEMENT_PATTERN = re.compile(
    r"我(?:想要|希望|需要|打算|主要)|主要(?:是)?|看中|平时|代步|通勤|家用|接娃|喜欢|自驾|买来"
)
RESUMPTION_CLUES_PATTERN = re.compile(
    r"(?:好的?|知道了?|明白(?:了)?|行|了解|原来如此|懂了|那继续吧?|继续吧?|接着说|听你的|没问题|继续(?:看车|预约|推进)?|回到刚才|刚才说到)"
)


class TopicManager:
    """
    Manages conversational topic hopping and seamless goal resumption.
    """

    @classmethod
    def get_stage_action_description(cls, stage: Stage, state: Optional[SessionState] = None) -> str:
        """Friendly human-readable sales goal description per stage."""
        stage_names = {
            Stage.WELCOME: "初次相识与建立客户画像",
            Stage.PROFILE_ANALYSIS: "了解客户基本用车场景与出行需求",
            Stage.NEEDS_ANALYSIS: "确认购车预算、动力形式与车型级别需求",
            Stage.CAR_SELECTION: "车型价值呈现并挑选心仪推荐车型",
            Stage.RESERVATION_4S: "收集4S店线下试驾预约信息（试驾人、时间、门店及联系电话）",
            Stage.RESERVATION_CONFIRMATION: "核对并确认线下试驾预约信息全部细节",
            Stage.FAREWELL: "完成试驾预约服务道别与关怀",
        }
        return stage_names.get(stage, stage.value)

    @classmethod
    def push_goal(cls, state: SessionState, current_stage: Stage, topic_label: str = "") -> None:
        """Push current interrupted sales goal onto the state stack if not already top."""
        if not hasattr(state, "interrupted_goals") or state.interrupted_goals is None:
            state.interrupted_goals = []

        stage_str = current_stage.value
        action_desc = cls.get_stage_action_description(current_stage, state)
        if not state.interrupted_goals or state.interrupted_goals[-1].get("stage") != stage_str:
            state.interrupted_goals.append({
                "stage": stage_str,
                "topic_label": topic_label,
                "target_action": action_desc,
            })
            logger.info(f"[{state.session_id}] Interrupted goal pushed: {stage_str} ({action_desc})")

    @classmethod
    def pop_goal(cls, state: SessionState) -> Optional[Dict[str, Any]]:
        """Pop and return the top interrupted goal from the stack."""
        if getattr(state, "interrupted_goals", None):
            popped = state.interrupted_goals.pop()
            logger.info(f"[{state.session_id}] Interrupted goal popped: {popped.get('stage')}")
            return popped
        return None

    @classmethod
    def peek_goal(cls, state: SessionState) -> Optional[Dict[str, Any]]:
        """Inspect the top interrupted goal without popping."""
        if getattr(state, "interrupted_goals", None):
            return state.interrupted_goals[-1]
        return None

    @classmethod
    def is_resumption_cue(cls, message: str) -> bool:
        """Whether user input signals conversational acknowledgment / goal resumption."""
        msg = message.strip()
        return bool(RESUMPTION_CLUES_PATTERN.search(msg))

    @classmethod
    def build_resumption_directive(cls, goal: Dict[str, Any]) -> str:
        """Build directive instructing agent to smoothly return to prior sales goal."""
        stage_name = goal.get("stage", "")
        target_action = goal.get("target_action", "")
        return (
            f"[主线目标平滑恢复] 客户此前的侧向咨询已解答完毕，当前已平稳返回销售主线（当前阶段：{stage_name}）。"
            f"请顺畅引导客户回到主线目标【{target_action}】，自然提出下一步推进建议或确认问题，切忌生硬断层。"
        )

    @classmethod
    def analyze_user_turn(
        cls,
        user_message: str,
        current_stage: Stage,
        state: SessionState,
    ) -> TopicAnalysisResult:
        """
        Analyze user message to determine if it is a side question, topic hop,
        constraint update, or multi-intent statement.
        """
        msg = user_message.strip()
        if not msg:
            return TopicAnalysisResult(
                intent=UserDialogueIntent.SALES_PROGRESSION,
                is_interrupt=False,
                is_multi_intent=False,
            )

        # 1. Detect technical questions or topic hops
        detected_topics: List[str] = []
        for pattern, label in TECHNICAL_QUERY_PATTERNS:
            if pattern.search(msg):
                detected_topics.append(label)

        # 2. Detect provided slots
        detected_slots: Dict[str, Any] = {}
        for pattern, slot_name in SLOT_HINT_PATTERNS:
            match = pattern.search(msg)
            if match:
                detected_slots[slot_name] = match.group(0)

        # Enhanced negative & positive constraint discrimination for vehicle category and powertrain
        negative_constraints: Dict[str, Any] = {}

        neg_cat_match = re.search(
            r"(?:不要|别要|绝对不要|排除|除外|绝不|不考虑|不能是|不要买)\s*(suv|轿车|mpv|猎装|轿跑|跑车|两厢|三厢|旅行车|越野)",
            msg,
            re.IGNORECASE,
        )
        pos_cat_match = re.search(
            r"(?<![不别])(?:只要|想要|看|换成|选|买|考虑|需要|要)\s*(suv|轿车|mpv|猎装|轿跑|跑车|两厢|三厢|旅行车|越野)",
            msg,
            re.IGNORECASE,
        )
        if neg_cat_match:
            negative_constraints["vehicle_category_bottom"] = neg_cat_match.group(1)
        if pos_cat_match:
            detected_slots["vehicle_category_bottom"] = pos_cat_match.group(1)

        neg_power_match = re.search(
            r"(?:不要|别要|绝对不要|排除|除外|绝不|不考虑|不能是|不要买)\s*(纯电|插混|增程|油车|混动|新能源|电车|油电混动|电动车|燃油车)",
            msg,
            re.IGNORECASE,
        )
        pos_power_match = re.search(
            r"(?<![不别])(?:只要|想要|看|换成|选|买|考虑|需要|要)\s*(纯电|插混|增程|油车|混动|新能源|电车|油电混动|电动车|燃油车)",
            msg,
            re.IGNORECASE,
        )
        if neg_power_match:
            negative_constraints["powertrain_type"] = neg_power_match.group(1)
        if pos_power_match:
            detected_slots["powertrain_type"] = pos_power_match.group(1)

        # 3. Check question, comparison, and requirement cues
        has_question_clues = bool(QUESTION_CLUES_PATTERN.search(msg))
        is_comparison = bool(COMPARISON_CLUES_PATTERN.search(msg))
        has_req_statement = bool(REQUIREMENT_STATEMENT_PATTERN.search(msg))

        # Check constraint modification clues
        is_constraint_mod = bool(
            re.search(
                r"改一下|换成|预算调整为|改选|重新考虑|重新选车|重新选|不要(?:suv|轿车|mpv|纯电|插混|增程|油车|电车|混动)|不想要|先别急着约|先不约|先别约|不急着约",
                msg,
                re.IGNORECASE,
            )
        )

        # Check if query targets a specific vehicle model
        has_specific_car = False
        try:
            from src.core.tiered_engine import FastSpecIndex
            matched_car = FastSpecIndex.get_instance().match_vehicle_model(msg)
            has_specific_car = matched_car is not None
        except Exception:
            has_specific_car = bool(
                re.search(r"su7|model|极氪|001|es6|汉ev|汉dm|l7|m7|问界|理想", msg, re.IGNORECASE)
            )

        # Determine if this turn is an active technical inquiry or side question
        is_tech_query = False
        if is_comparison:
            is_tech_query = True
        elif has_specific_car and (len(detected_topics) > 0 or has_question_clues):
            is_tech_query = True
        elif len(detected_topics) > 0 and has_question_clues:
            is_tech_query = True
        elif len(detected_topics) > 0 and not has_req_statement and len(msg) <= 15:
            # Concise spec query e.g. "SU7续航", "电机转速是多少"
            is_tech_query = True

        topic_label = detected_topics[0] if detected_topics else "车辆参数与技术咨询"

        # Check conversational goal resumption
        has_pending_goal = bool(getattr(state, "interrupted_goals", []))
        is_resumption = cls.is_resumption_cue(msg) and has_pending_goal

        resumed_goal = None
        directive = ""

        # Determine composite intent
        if is_constraint_mod and is_tech_query:
            intent = UserDialogueIntent.MULTI_INTENT
            is_interrupt = True
            is_multi = True
        elif is_constraint_mod:
            intent = UserDialogueIntent.CONSTRAINT_UPDATE
            is_interrupt = True
            is_multi = bool(detected_slots)
        elif is_resumption:
            intent = UserDialogueIntent.SALES_PROGRESSION
            is_interrupt = False
            is_multi = False
            resumed_goal = cls.pop_goal(state)
            if resumed_goal:
                directive = cls.build_resumption_directive(resumed_goal)
        elif is_tech_query and detected_slots:
            intent = UserDialogueIntent.MULTI_INTENT
            is_interrupt = True
            is_multi = True
        elif is_tech_query:
            if is_comparison or "横向对比" in topic_label or "对比" in msg:
                intent = UserDialogueIntent.SPEC_COMPARISON
            else:
                intent = UserDialogueIntent.SIDE_QUESTION
            is_interrupt = True
            is_multi = False
        else:
            intent = UserDialogueIntent.SALES_PROGRESSION
            is_interrupt = False
            is_multi = False

        current_stage_name = cls.get_stage_action_description(current_stage, state)

        if intent in (UserDialogueIntent.SIDE_QUESTION, UserDialogueIntent.SPEC_COMPARISON):
            directive = (
                f"[灵活意图应答与主线推进] 客户在【{current_stage_name}】阶段提出了具体技术咨询（关注点：{topic_label}）。"
                f"请遵照以下管控指引回复：\n"
                f"1. 【直接客观解答】：优先用准确、专业、严谨的数据直接回答客户关于【{topic_label}】的问题，切忌答非所问；\n"
                f"2. 【自然平滑过渡】：在答复完毕后，自然地将话题引回主线目标（当前阶段：{current_stage_name}），"
                f"例如建议客户在到店试驾中亲身体验该性能，避免机械生硬地重复索要信息。"
            )
        elif intent == UserDialogueIntent.MULTI_INTENT:
            if is_constraint_mod:
                directive = (
                    f"[多意图复合处理] 客户同时调整了购车需求/约束并咨询了技术参数（{topic_label}）。"
                    f"请在直接清晰客观解答技术问题的同时，明确确认需求调整，顺畅推进对话流程。"
                )
            else:
                directive = (
                    f"[多意图复合处理] 客户同时提出了技术咨询（{topic_label}）并提供了有效信息。"
                    f"请在直接清晰解答技术问题的同时，自然确认客户提供的新信息，顺畅推进对话流程。"
                )
        elif intent == UserDialogueIntent.CONSTRAINT_UPDATE:
            directive = (
                f"[客户约束条件修正] 客户更新了选车要求或约束条件。"
                f"请遵照客户最新提出的要求调整匹配逻辑，并在回复中明确确认该变更，自然推进主线目标（当前阶段：{current_stage_name}）。"
            )

        if negative_constraints and directive:
            directive += (
                f"\n【否定排除约束遵循】：客户明确提出了否定排除要求（排除项：{negative_constraints}），"
                f"在推荐及比对车型时务必严格遵循该排除约束，切勿推荐被排除的类型。"
            )

        return TopicAnalysisResult(
            intent=intent,
            is_interrupt=is_interrupt,
            is_multi_intent=is_multi,
            topic_label=topic_label,
            detected_entities=detected_topics,
            suggested_directive=directive,
            extracted_slots_hint=detected_slots,
            resumed_goal=resumed_goal,
            negative_constraints=negative_constraints,
        )
