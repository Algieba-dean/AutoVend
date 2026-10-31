"""
Advanced Query Transformation Engine for AutoVend RAG (src/retrieval/query_transform.py).

Implements 5 core RAG query transformation strategies:
1. Query Rewriting (Contextual rewriting & coreference resolution)
2. Query Expansion (Industry synonym & abbreviation expansion)
3. HyDE (Hypothetical Document Embeddings generation)
4. Multi-Query Expansion (Multi-perspective query generation)
5. Sub-Query Decomposition (Compound intent & comparison breaking)
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryTransformationEngine:
    """
    Unified Query Transformation Engine implementing 5 advanced retrieval strategies.
    """

    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm

    # 1. Query Rewriting (指代消解、长尾干扰过滤与隐式意图丰富)
    def rewrite_query(self, query_text: str, conversation_history: str = "") -> str:
        """
        Rewrite query to resolve coreference/pronouns ('它', '这车', '前一款') using context,
        and enrich implicit scenario intents with automotive domain search keywords.
        """
        if not query_text:
            return query_text

        rewritten = query_text.strip()

        # Pronoun coreference resolution heuristic
        pronouns = [
            "它",
            "这车",
            "这几款",
            "前面的",
            "刚才提到的",
            "第一款",
            "上一款",
            "前一个",
            "上一台",
            "刚才那台",
            "那个车",
        ]
        if any(p in rewritten for p in pronouns) and conversation_history:
            # Extract most recent car models or brands mentioned in conversation history
            models = re.findall(
                r"([\u4e00-\u9fa5A-Za-z0-9]+(?:-[A-Za-z0-9]+|EV|DM-i|Max|Pro|Plus|Ultra)?)",
                conversation_history,
            )
            car_mentions = [
                m
                for m in models
                if any(
                    k in m
                    for k in [
                        "特斯拉",
                        "蔚来",
                        "理想",
                        "问界",
                        "比亚迪",
                        "保时捷",
                        "奔驰",
                        "宝马",
                        "奥迪",
                        "极氪",
                        "小鹏",
                        "小米",
                        "Model",
                        "ES6",
                        "ET5",
                        "L7",
                        "L8",
                        "L9",
                        "M7",
                        "M9",
                        "SU7",
                        "001",
                        "007",
                        "G6",
                        "G9",
                        "宋",
                        "汉",
                        "唐",
                        "秦",
                    ]
                )
            ]
            if car_mentions:
                recent_car = car_mentions[-1]
                for p in pronouns:
                    rewritten = rewritten.replace(p, recent_car)

        # Strip conversational filler noise
        fillers = ["麻烦问一下", "请问", "帮我查查", "我想知道", "能不能告诉我", "随便看看", "跟我说说"]
        for f in fillers:
            rewritten = rewritten.replace(f, "")

        # Implicit intent scenario enrichment
        implicit_mappings = [
            (r"(?:二胎|二孩|三代同堂|全家老小)", "大空间 6座 7座 舒适座椅"),
            (r"(?:跑长途|自驾游|高速长距离)", "长续航 快充 800V 辅助驾驶"),
            (r"(?:东北|北方寒冬|极寒|零下)", "热泵空调 电池低温加热 四驱"),
            (r"(?:露营|野营|户外轻越野)", "对外放电 大后备箱 离地间隙"),
            (r"(?:新手|刚拿驾照|难停车|窄车位)", "自动泊车 360全景影像 灵巧转向"),
            (r"(?:城市代步|上下班通勤|买菜接娃)", "低电耗 紧凑车身 好调头 经济实惠"),
        ]
        for pattern, enrichment in implicit_mappings:
            if re.search(pattern, rewritten) and not any(k in rewritten for k in enrichment.split()):
                rewritten = f"{rewritten} {enrichment}"

        return rewritten.strip() or query_text

    # 2. Query Expansion (同义词与行业简称扩展)
    def expand_query(self, query_text: str) -> str:
        """Expand domain terminology, abbreviations, and informal usage terms."""
        from src.retrieval.query_expander import QueryExpander

        return QueryExpander.expand_query(query_text)

    # 3. HyDE (Hypothetical Document Embeddings / 假设性文档嵌入)
    def generate_hyde_doc(self, query_text: str) -> str:
        """
        Generate a hypothetical mock vehicle specification document for the query.
        Retrieving doc-to-doc embedding vectors yields significantly higher similarity.
        """
        if not query_text:
            return query_text

        # Generate structured hypothetical spec document string
        tech_note = ""
        try:
            from src.core.terminology import AutomotiveKnowledgeGraph
            kg = AutomotiveKnowledgeGraph.get_instance()
            matched = kg.extract_terms(query_text)
            if matched:
                tech_names = "、".join([f"{m.entity.name}（{m.entity.summary}）" for m in matched[:2]])
                tech_note = f" 搭载核心技术：{tech_names}。"
        except Exception:
            pass

        hyde_doc = (
            f"【目标车型规格文档】 车型需求: {query_text}。{tech_note}"
            f"车辆类型包含中大型SUV/纯电轿跑，配置包含大空间二排、高阶智驾系统、800V高压快充及气囊安全防护。"
            f"官方指导价格区间与参数指标精准匹配该需求。"
        )

        if self.llm is not None:
            prompt = (
                f"请为以下汽车采购需求生成一段假设性的标准车辆配置说明文档（HyDE文档，200字以内）：\n"
                f"需求: {query_text}\n"
                f"假想说明文档:"
            )
            try:
                res = self.llm.complete(prompt)
                if res and res.text:
                    hyde_doc = res.text.strip()
            except Exception as e:
                logger.warning(f"HyDE LLM generation fallback to rule: {e}")

        return hyde_doc

    # 4. Multi-Query Expansion (多路查询展开)
    def generate_multi_queries(self, query_text: str) -> List[str]:
        """
        Generate multiple distinct phrasing variations of the query.
        """
        if not query_text:
            return [query_text]

        variations = [query_text]
        expanded = self.expand_query(query_text)
        if expanded != query_text:
            variations.append(expanded)

        # Generate category/attribute perspective variant
        variations.append(f"{query_text} 详细配置对比 参数亮点 落地价格")

        return list(dict.fromkeys(variations))

    # 5. Sub-Query Decomposition (子查询拆解与对比分发)
    def decompose_sub_queries(self, query_text: str) -> List[str]:
        """
        Decompose compound or comparative queries into atomic sub-queries.
        Example: '对比理想L7和问界M7的续航与售价' -> ['理想L7 续航与售价', '问界M7 续航与售价']
        Example: 'Model Y、蔚来ES6与极氪001对比' -> ['Model Y 对比', '蔚来ES6 对比', '极氪001 对比']
        """
        if not query_text:
            return [query_text]

        # Check comparison or compound pattern ('对比', '相比', 'PK', 'vs', 'VS')
        if any(k in query_text for k in ["对比", "相比", "PK", "vs", "VS", "选哪个", "哪个好"]):
            clean = re.sub(r"^(?:对比|相比)\s*", "", query_text).strip()
            clean = re.sub(r"(?:对比|相比|选哪个|哪个好)$", "", clean).strip()
            feature_suffix = ""
            if "的" in clean:
                parts = clean.split("的", 1)
                clean = parts[0]
                feature_suffix = parts[1]

            # Split vehicles by 和/与/PK/vs/VS/、/,/空格
            parts = re.split(r"\s*(?:和|与|PK|vs|VS|、|,)\s*", clean)
            parts = [p.strip() for p in parts if p.strip()]

            if len(parts) >= 2:
                suffix = f" {feature_suffix}".strip()
                return [f"{p} {suffix}".strip() for p in parts]

        return [query_text]

    # 6. Multi-Perspective Decomposition (多维度透镜拆解)
    def decompose_multi_perspective(self, query_text: str) -> List[Dict[str, str]]:
        """
        Decompose complex multi-faceted automotive queries into orthogonal perspectives:
        - space_and_comfort: 空间与家庭舒适度
        - range_and_energy: 续航能耗与补能
        - intelligent_driving: 智能座舱与高阶辅助驾驶
        - budget_and_value: 预算价格与保值性价比
        """
        if not query_text:
            return []

        perspectives: List[Dict[str, str]] = []

        # Perspective 1: Space & Family
        if any(k in query_text for k in ["空间", "大", "家", "二胎", "小孩", "父母", "老人", "座", "SUV", "MPV", "后备箱"]):
            perspectives.append({
                "perspective": "space_and_comfort",
                "focus": "空间布局与乘坐舒适度",
                "query": f"{query_text} 二排空间 座椅舒适性 后备箱容积",
            })

        # Perspective 2: Range & Energy
        if any(k in query_text for k in ["续航", "电耗", "油耗", "纯电", "混动", "增程", "充电", "800V", "长途", "自驾"]):
            perspectives.append({
                "perspective": "range_and_energy",
                "focus": "续航达成率与补能效率",
                "query": f"{query_text} CLTC纯电续航 快充时间 综合能耗",
            })

        # Perspective 3: Intelligence & Tech
        if any(k in query_text for k in ["智驾", "自动驾驶", "辅助驾驶", "芯片", "激光雷达", "车机", "座舱", "高科技", "NOA"]):
            perspectives.append({
                "perspective": "intelligent_driving",
                "focus": "智能座舱与高阶辅助驾驶能力",
                "query": f"{query_text} 高阶智驾 NOA 激光雷达 智能座舱芯片",
            })

        # Perspective 4: Budget & Value
        if any(k in query_text for k in ["万", "预算", "价格", "落地", "性价比", "便宜", "优惠", "权益"]):
            perspectives.append({
                "perspective": "budget_and_value",
                "focus": "指导价与购车落地性价比",
                "query": f"{query_text} 官方指导价 购车优惠 落地预算",
            })

        if not perspectives:
            perspectives.append({
                "perspective": "general_overview",
                "focus": "综合车型参数与竞争力",
                "query": f"{query_text} 核心参数 车型亮点",
            })

        return perspectives

    # Master Transformation Entry
    def transform_all(self, query_text: str, conversation_history: str = "") -> Dict[str, Any]:
        """
        Execute full Query Transformation suite and return enriched search representations.
        """
        rewritten = self.rewrite_query(query_text, conversation_history)
        expanded = self.expand_query(rewritten)
        hyde_doc = self.generate_hyde_doc(rewritten)
        multi_queries = self.generate_multi_queries(rewritten)
        sub_queries = self.decompose_sub_queries(rewritten)
        perspective_queries = self.decompose_multi_perspective(rewritten)

        return {
            "original_query": query_text,
            "rewritten_query": rewritten,
            "expanded_query": expanded,
            "hyde_document": hyde_doc,
            "multi_queries": multi_queries,
            "sub_queries": sub_queries,
            "perspective_queries": perspective_queries,
        }
