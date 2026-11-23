"""
Next-Best-Action (NBA) Proactive Dialogue Planner for AutoVend Agent (src/agent/nba_planner.py).

Replaces passive "missing-slot interrogation" with an explicit pre-generation strategy layer
that balances requirement convergence, proactive dual-car comparisons, value hooks
(trade-in subsidies, TCO), objection handling, and test-drive closing.
"""

from dataclasses import dataclass
from enum import Enum

from src.agent.schemas import SessionState, Stage


class NextBestAction(str, Enum):
    ASK_CLARIFICATION = "ask_clarification"
    PROACTIVE_RECOMMEND = "proactive_recommend"
    COMPARE_MODELS = "compare_models"
    VALUE_HOOK_TRADEIN = "value_hook_tradein"
    OBJECTION_HANDLING = "objection_handling"
    INVITE_TEST_DRIVE = "invite_test_drive"
    COLLECT_RESERVATION = "collect_reservation"
    CONFIRM_RESERVATION = "confirm_reservation"
    HANDOFF_TO_HUMAN = "handoff_to_human"
    WARM_GREETING = "warm_greeting"
    FAREWELL_WRAPUP = "farewell_wrapup"


@dataclass(frozen=True)
class NBADecision:
    action: NextBestAction
    rationale: str
    directive: str


_OBJECTION_KEYWORDS = (
    "太贵", "超预算", "续航焦虑", "充电不方便", "没地方充", "保值率", "担心安全", "自燃", "犹豫", "再看看"
)
_HESITATION_OR_VALUE_KEYWORDS = (
    "优惠", "补贴", "置换", "划算", "性价比", "月供", "利息", "落地价", "怎么选", "纠结"
)
_POSITIVE_INTEREST_KEYWORDS = (
    "不错", "挺好", "喜欢", "想看", "试驾", "体验", "就这款", "考虑这"
)
_COMPARISON_KEYWORDS = ("对比", "区别", "哪个好", "选谁", "vs", "还是")


class NextBestActionPlanner:
    """Deterministic strategic dialogue planner executed before reply generation."""

    MAX_CONSECUTIVE_ASKS = 2

    @classmethod
    def plan(
        cls,
        sess: SessionState,
        user_message: str,
        topic_intent: str = "",
        hitl_triggered: bool = False,
    ) -> NBADecision:
        if hitl_triggered:
            return NBADecision(
                action=NextBestAction.HANDOFF_TO_HUMAN,
                rationale="hitl_trigger_active",
                directive="[NBA策略: 转人工交接] 已触发人工专家接管条件，请简明安抚客户并说明专属顾问即将接入。",
            )

        msg = (user_message or "").strip()
        stage = sess.stage
        matched = sess.matched_cars or []
        consecutive_asks = int(getattr(sess, "consecutive_ask_turns", 0))

        if stage == Stage.FAREWELL:
            return NBADecision(
                action=NextBestAction.FAREWELL_WRAPUP,
                rationale="farewell_stage",
                directive="[NBA策略: 礼貌收尾] 确认试驾预约已妥善安排，简要提醒到店注意事项并温暖道别。",
            )

        if stage == Stage.RESERVATION_CONFIRMATION:
            return NBADecision(
                action=NextBestAction.CONFIRM_RESERVATION,
                rationale="reservation_confirmation_stage",
                directive="[NBA策略: 确认预约] 清晰汇总试驾车型、时间、门店与联系人，邀请客户最终确认。",
            )

        if stage == Stage.RESERVATION_4S:
            return NBADecision(
                action=NextBestAction.COLLECT_RESERVATION,
                rationale="reservation_collection_stage",
                directive="[NBA策略: 收集预约要素] 礼貌核对缺失的试驾日期、时段、门店或手机号（每次最多补问1-2项）。",
            )

        # Objection handling takes priority in active consultation stages
        if any(k in msg for k in _OBJECTION_KEYWORDS):
            return NBADecision(
                action=NextBestAction.OBJECTION_HANDLING,
                rationale="customer_raised_objection",
                directive="[NBA策略: 痛点破冰与异议化解] 先共情客户的顾虑（价格/续航/充电/安全），用真实数据或替代动力方案化解，再自然推进。",
            )

        # Explicit comparison request or >= 2 matched cars with comparison signal
        if len(matched) >= 2 and (
            any(k in msg.lower() for k in _COMPARISON_KEYWORDS)
            or topic_intent == "spec_comparison"
            or (stage == Stage.CAR_SELECTION and consecutive_asks >= 1)
        ):
            m1 = matched[0].get("car_model", "车型A")
            m2 = matched[1].get("car_model", "车型B")
            return NBADecision(
                action=NextBestAction.COMPARE_MODELS,
                rationale="two_or_more_candidates_available",
                directive=f"[NBA策略: 主动双车对比] 主动对「{m1}」与「{m2}」做核心维度差异对比（价格/动力/空间/亮点），帮客户快速做减法。",
            )

        # Positive interest in CAR_SELECTION -> invite test drive
        if stage == Stage.CAR_SELECTION and matched and any(k in msg for k in _POSITIVE_INTEREST_KEYWORDS):
            return NBADecision(
                action=NextBestAction.INVITE_TEST_DRIVE,
                rationale="positive_signal_with_matched_cars",
                directive="[NBA策略: 邀约试驾] 客户对候选车型表现出兴趣，顺势邀约到店静态体验与动态试驾。",
            )

        # Anti-interrogation guard: never ask 3 consecutive turns in a row
        if consecutive_asks >= cls.MAX_CONSECUTIVE_ASKS or any(k in msg for k in _HESITATION_OR_VALUE_KEYWORDS):
            if matched:
                return NBADecision(
                    action=NextBestAction.PROACTIVE_RECOMMEND,
                    rationale="anti_interrogation_pivot_to_recommend",
                    directive="[NBA策略: 主动推荐破冰] 避免继续追问，直接结合已掌握偏好推荐1-2款最匹配车型，并附带一句价值锚点。",
                )
            return NBADecision(
                action=NextBestAction.VALUE_HOOK_TRADEIN,
                rationale="anti_interrogation_value_hook",
                directive="[NBA策略: 置换补贴/用车痛点破冰] 避免像查户口一样连续追问！本轮先抛出置换补贴/用车成本或常见选车痛点作为价值钩子，再轻度引导偏好。",
            )

        if stage == Stage.WELCOME and not sess.needs.explicit.price and not sess.needs.explicit.powertrain_type:
            return NBADecision(
                action=NextBestAction.WARM_GREETING,
                rationale="initial_welcome",
                directive="[NBA策略: 温暖破冰] 简短热情问候，用1个开放式问题了解客户日常用车场景或大致预算即可。",
            )

        if matched and stage in (Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION):
            return NBADecision(
                action=NextBestAction.PROACTIVE_RECOMMEND,
                rationale="candidates_ready_to_present",
                directive="[NBA策略: 精准推荐] 结合硬约束与软偏好展示候选车型核心亮点，并明确说明是否符合客户排除项。",
            )

        return NBADecision(
            action=NextBestAction.ASK_CLARIFICATION,
            rationale="converge_missing_core_constraints",
            directive="[NBA策略: 聚焦追问收敛] 每次仅围绕1个最关键缺失条件（如预算区间或动力偏好）温和追问，切忌一次连问多个问题。",
        )

    @staticmethod
    def update_ask_counter(sess: SessionState, decision: NBADecision) -> None:
        sess.last_nba_action = decision.action.value
        if decision.action in (NextBestAction.ASK_CLARIFICATION, NextBestAction.COLLECT_RESERVATION):
            sess.consecutive_ask_turns = int(getattr(sess, "consecutive_ask_turns", 0)) + 1
        else:
            sess.consecutive_ask_turns = 0
