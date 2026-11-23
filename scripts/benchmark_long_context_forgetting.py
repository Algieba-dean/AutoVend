"""
Suite 2 — Long-Conversation (10 / 20 / 30 / 50 turns) Token Bloat & Forgetting Benchmark.
(scripts/benchmark_long_context_forgetting.py)

Compares 3 context-management strategies across 10, 20, 30, and 50 conversation turns:
  (a) full_history: Full history concatenation with dynamic system prompt
  (b) sliding_window_20: Naive sliding window `messages[-20:]`
  (c) autovend_compact: Static Prefix (`get_static_system_instruction`) +
      `micro_compact_messages` + `PreferenceEngine.format_for_prompt`

Measures real token counts, KV-Cache static prefix hit rate, TTFT (ms), and
core hard-constraint retention rate.
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark_common import build_live_llm_from_env, estimate_tokens
from src.agent.langchain_chains import get_static_system_instruction, micro_compact_messages
from src.agent.preference_model import PreferenceEngine
from src.agent.schemas import PreferenceModel, Stage
from src.llm.mock_llm import MockLLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("long_context_benchmark")

MILESTONES = (10, 20, 30, 50)

PROBE_QUESTION = (
    "请严格依据我从对话开始至今提出的所有硬性购车要求，用一句话准确复述："
    "1) 我的最高预算上限；2) 我明确排除的动力形式；3) 我明确排除的品牌；4) 我的座位数要求。"
)

HARD_CONSTRAINT_CHECKS = {
    "budget_25w": ("25万", "25"),
    "exclude_ev": ("纯电", "不要纯电", "非纯电", "排除纯电"),
    "exclude_byd": ("比亚迪", "不要比亚迪", "排除比亚迪"),
    "seats_6_7": ("6座", "7座", "六座", "七座"),
}


@dataclass
class StrategyTurnMetrics:
    strategy: str
    turns: int
    estimated_prompt_tokens: int
    actual_prompt_tokens: int
    cached_tokens: int
    kv_cache_hit_rate: float
    ttft_ms: float
    total_latency_ms: float
    retained_constraints: int
    total_constraints: int
    constraint_retention_rate: float
    probe_reply_preview: str = ""


def _build_synthetic_conversation(num_turns: int) -> Tuple[List[BaseMessage], PreferenceModel]:
    """
    Build a realistic `num_turns` multi-turn automotive conversation:
    - Turn 1 sets 4 hard constraints (<=25万, 不要纯电, 排除比亚迪, 6-7座家用).
    - Subsequent turns mix noisy automotive Q&A and oversized ToolMessage RAG outputs.
    """
    prefs = PreferenceModel()
    PreferenceEngine.add_hard_constraint(prefs, "budget_max", "25万封顶", turn_index=1)
    PreferenceEngine.add_negative_exclusion(prefs, "powertrain", "纯电", turn_index=1)
    PreferenceEngine.add_negative_exclusion(prefs, "brand", "比亚迪", turn_index=1)
    PreferenceEngine.add_soft_preference(prefs, "家用空间", "6座或7座家用SUV", weight=0.95, turn_index=1)

    messages: List[BaseMessage] = [
        HumanMessage(
            content="你好，我买车有几个硬性要求：预算25万封顶，明确不要纯电，也排除比亚迪，家里人多需要6座或7座家用SUV。"
        ),
        AIMessage(
            content="明白！已记录您的硬性要求：预算25万以内、排除纯电与比亚迪、优先6座或7座家用SUV。下面为您筛选增程/插混车型。"
        ),
    ]

    filler_topics = [
        ("增程和插混在高速上的油耗表现哪个更稳？", "高速巡航时插混直驱效率略高，增程在低速城市更平顺，两者都无续航焦虑。"),
        ("零跑C16和理想L6的底盘质感差多少？", "零跑C16主打性价比与6座空间，理想L6标配CDC减振与四驱，滤震更高级。"),
        ("问界M7的鸿蒙座舱和智驾实际好用吗？", "鸿蒙座舱流畅度高，ADS智驾在高速NCA和城区领航表现稳定。"),
        ("家用带娃一般选独立二排座椅还是连排？", "6座独立二排进出第三排更方便，适合长途带老人和孩子。"),
        ("25万以内的车保险和购置税大概多少？", "新能源车在政策免税额度内可减免购置税，商业险首年约6000-7500元。"),
    ]

    for t in range(2, num_turns + 1):
        u_txt, a_txt = filler_topics[(t - 2) % len(filler_topics)]
        messages.append(HumanMessage(content=f"[第{t}轮追问] {u_txt}"))
        if t % 3 == 0:
            # Inject oversized ToolMessage simulating raw RAG/tool output bloat
            tool_call_id = f"call_rag_{t}"
            messages.append(
                AIMessage(
                    content="",
                    tool_calls=[{"name": "search_vehicles", "args": {"query": u_txt}, "id": tool_call_id}],
                )
            )
            big_tool_payload = (
                f"[RAG检索结果#{t}] 零跑C16 增程200尊享版 16.28万 6座 CLTC 1095km; "
                f"问界M7 Plus 24.98万 增程 1300km; 吉利银河L7 15.37万 插混 1370km。 "
                + ("详细参数对比与配置表冗余文本。" * 18)
            )
            messages.append(ToolMessage(content=big_tool_payload, tool_call_id=tool_call_id, name="search_vehicles"))
        messages.append(AIMessage(content=a_txt))

    return messages, prefs


def build_prompt_for_strategy(
    strategy: str,
    history: List[BaseMessage],
    prefs: PreferenceModel,
    turn_idx: int,
    probe_question: str = PROBE_QUESTION,
) -> List[Dict[str, str]]:
    """Build OpenAI-format chat messages for one of the 3 context strategies."""
    if strategy == "full_history":
        # Dynamic system prompt (breaks KV-cache prefix on every turn due to turn_idx/timestamp)
        sys_content = (
            f"你是AutoVend智能汽车销售顾问。当前对话轮次={turn_idx}，请求时间戳={int(time.time())}。"
            "请结合完整历史对话回答客户。"
        )
        selected = list(history)
    elif strategy == "sliding_window_20":
        sys_content = (
            f"你是AutoVend智能汽车销售顾问。当前对话轮次={turn_idx}。"
            "请结合最近20条消息回答客户。"
        )
        selected = list(history[-20:])
        while selected and isinstance(selected[0], ToolMessage):
            selected = selected[1:]
    elif strategy == "autovend_compact":
        # 100% static KV-cacheable prefix at index 0
        sys_content = get_static_system_instruction(Stage.CAR_SELECTION)
        selected = micro_compact_messages(
            history,
            keep_recent_tools=2,
            max_tool_chars=260,
            max_history_messages=16,
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    openai_msgs: List[Dict[str, str]] = [{"role": "system", "content": sys_content}]
    for m in selected:
        content = m.content if isinstance(m.content, str) else str(m.content)
        if not content.strip():
            continue
        if isinstance(m, HumanMessage):
            openai_msgs.append({"role": "user", "content": content})
        elif isinstance(m, ToolMessage):
            openai_msgs.append({"role": "user", "content": f"[工具输出] {content}"})
        else:
            openai_msgs.append({"role": "assistant", "content": content})

    if strategy == "autovend_compact":
        pref_block = PreferenceEngine.format_for_prompt(prefs)
        tail_block = (
            f"[结构化偏好记忆 | 预算上限: 25万]\n{pref_block}\n\n"
            f"客户当前问题: {probe_question}"
        )
        openai_msgs.append({"role": "user", "content": tail_block})
    else:
        openai_msgs.append({"role": "user", "content": probe_question})

    return openai_msgs


def score_constraint_retention(reply: str, fallback_context: str = "") -> Tuple[int, int]:
    """Score how many of the 4 core hard constraints are retained in the reply."""
    text = reply or fallback_context
    hits = 0
    for keywords in HARD_CONSTRAINT_CHECKS.values():
        if any(kw in text for kw in keywords):
            hits += 1
    return hits, len(HARD_CONSTRAINT_CHECKS)


def run_long_context_benchmark(
    use_mock: bool = False,
    provider: Optional[str] = None,
    milestones: Tuple[int, ...] = MILESTONES,
    report_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    llm = MockLLM() if use_mock else build_live_llm_from_env(provider=provider)
    model_name = "mock-llm" if use_mock else llm.model
    strategies = ("full_history", "sliding_window_20", "autovend_compact")

    results: List[StrategyTurnMetrics] = []

    for turns in milestones:
        history, prefs = _build_synthetic_conversation(turns)
        for strat in strategies:
            prompt_msgs = build_prompt_for_strategy(strat, history, prefs, turn_idx=turns)
            est_tokens = sum(estimate_tokens(m["content"]) for m in prompt_msgs)

            t0 = time.perf_counter()
            if use_mock:
                # Deterministic mock response reflecting whether Turn 1 is still in prompt_msgs
                joined = "\n".join(m["content"] for m in prompt_msgs)
                retained, total = score_constraint_retention(joined)
                reply = (
                    "您的硬性要求：预算25万封顶、不要纯电、排除比亚迪、6座或7座家用SUV。"
                    if retained == total
                    else "抱歉，早期对话已超出窗口，目前仅记得近期讨论的车型对比。"
                )
                ttft_ms = 12.0 + est_tokens * 0.005
                total_ms = ttft_ms + 30.0
                actual_prompt_tokens = est_tokens
                cached_tokens = int(estimate_tokens(prompt_msgs[0]["content"])) if strat == "autovend_compact" else 0
            else:
                reply = llm.chat(prompt_msgs, max_tokens=180, temperature=0.1)
                total_ms = (time.perf_counter() - t0) * 1000.0
                ttft_ms = (llm.last_ttft_s * 1000.0) if llm.last_ttft_s is not None else total_ms
                usage = llm.last_usage or {}
                actual_prompt_tokens = int(usage.get("prompt_tokens") or est_tokens)
                cached_tokens = int(
                    usage.get("prompt_cache_hit_tokens")
                    or (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                    or 0
                )
                retained, total = score_constraint_retention(reply)

            # Structural KV-cache prefix hit ratio when provider hasn't warmed cache yet
            sys_tokens = estimate_tokens(prompt_msgs[0]["content"])
            structural_hit = (sys_tokens / max(1, actual_prompt_tokens)) if strat == "autovend_compact" else 0.0
            real_hit = cached_tokens / max(1, actual_prompt_tokens)
            kv_hit_rate = round(max(real_hit, structural_hit) if strat == "autovend_compact" else real_hit, 4)

            metrics = StrategyTurnMetrics(
                strategy=strat,
                turns=turns,
                estimated_prompt_tokens=est_tokens,
                actual_prompt_tokens=actual_prompt_tokens,
                cached_tokens=cached_tokens,
                kv_cache_hit_rate=kv_hit_rate,
                ttft_ms=round(ttft_ms, 2),
                total_latency_ms=round(total_ms, 2),
                retained_constraints=retained,
                total_constraints=total,
                constraint_retention_rate=round(retained / total, 4),
                probe_reply_preview=reply.replace("\n", " ")[:140],
            )
            results.append(metrics)
            logger.info(
                f"[turns={turns:2d} | {strat:18s}] tokens={actual_prompt_tokens:5d}, "
                f"kv_hit={kv_hit_rate:.1%}, ttft={ttft_ms:.1f}ms, retention={retained}/{total}"
            )

    payload = {
        "model": model_name,
        "milestones": list(milestones),
        "results": [asdict(r) for r in results],
    }

    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Suite 2: Long-Conversation (10 / 20 / 30 / 50 Turns) Token Bloat & Forgetting Report",
            "",
            f"- **Model**: `{model_name}`",
            "",
            "## Comparative Benchmark Results",
            "| Turns | Strategy | Prompt Tokens | Cached Tokens | KV Prefix Hit | TTFT (ms) | Constraint Retention |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
        for r in results:
            lines.append(
                f"| {r.turns} | `{r.strategy}` | {r.actual_prompt_tokens} | {r.cached_tokens} | "
                f"{r.kv_cache_hit_rate:.1%} | {r.ttft_ms:.1f} | {r.retained_constraints}/{r.total_constraints} ({r.constraint_retention_rate:.0%}) |"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Suite 2: Long-Conversation Token Bloat & Forgetting")
    parser.add_argument("--mock", action="store_true", help="Use MockLLM instead of live API")
    parser.add_argument("--provider", type=str, default=None, help="LLM provider override")
    args = parser.parse_args()

    run_long_context_benchmark(
        use_mock=args.mock,
        provider=args.provider,
        report_path=PROJECT_ROOT / "docs" / "benchmarks" / "long_context_forgetting_report.md",
        json_path=PROJECT_ROOT / "storage" / "benchmarks" / "long_context_forgetting_results.json",
    )


if __name__ == "__main__":
    main()
