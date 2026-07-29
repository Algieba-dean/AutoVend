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

    # 1. Query Rewriting (指代消解与长尾干扰过滤)
    def rewrite_query(self, query_text: str, conversation_history: str = "") -> str:
        """
        Rewrite query to resolve coreference/pronouns ('它', '这车') using context.
        """
        if not query_text:
            return query_text

        rewritten = query_text.strip()

        # Pronoun coreference resolution heuristic
        pronouns = ["它", "这车", "这几款", "前面的", "刚才提到的"]
        if any(p in rewritten for p in pronouns) and conversation_history:
            # Extract most recent car models or brands mentioned in conversation history
            models = re.findall(
                r"([\u4e00-\u9fa5A-Za-z0-9]+(?:-[A-Za-z0-9]+|EV|DM-i|Max|Pro)?)",
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
                        "Model",
                        "ES6",
                        "L7",
                        "M7",
                        "SU7",
                    ]
                )
            ]
            if car_mentions:
                recent_car = car_mentions[-1]
                for p in pronouns:
                    rewritten = rewritten.replace(p, recent_car)

        # Strip conversational filler noise
        fillers = ["麻烦问一下", "请问", "帮我查查", "我想知道", "能不能告诉我", "随便看看"]
        for f in fillers:
            rewritten = rewritten.replace(f, "")

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
        hyde_doc = (
            f"【目标车型规格文档】 车型需求: {query_text}。"
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
        """
        if not query_text:
            return [query_text]

        # Check comparison or compound pattern ('对比', '相比', 'PK')
        if any(k in query_text for k in ["对比", "相比", "PK"]):
            clean = re.sub(r"^(?:对比|相比)\s*", "", query_text).strip()
            feature_suffix = ""
            if "的" in clean:
                clean, feature_suffix = clean.split("的", 1)

            # Split vehicles by 和/与/PK/,
            parts = re.split(r"\s*(?:和|与|PK|,)\s*", clean)
            parts = [p.strip() for p in parts if p.strip()]

            if len(parts) >= 2:
                return [f"{p} {feature_suffix}".strip() for p in parts]

        return [query_text]

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

        return {
            "original_query": query_text,
            "rewritten_query": rewritten,
            "expanded_query": expanded,
            "hyde_document": hyde_doc,
            "multi_queries": multi_queries,
            "sub_queries": sub_queries,
        }
