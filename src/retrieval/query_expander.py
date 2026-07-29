"""
Automotive Domain Query & Synonym Expander (src/retrieval/query_expander.py).

Expands natural language user queries with domain-specific car terminology,
brand alliances, and usage scenario synonyms to boost RAG Recall and Hit Rate.
"""

from typing import Dict, List

# Domain Synonym Registry for Automotive RAG
AUTOMOTIVE_SYNONYMS: Dict[str, List[str]] = {
    "奶爸车": ["大空间", "家庭舒适", "后排宽敞", "5座", "6座", "SUV", "MPV"],
    "德系": ["奔驰", "宝马", "奥迪", "大众", "保时捷"],
    "日系": ["丰田", "本田", "日产", "雷克萨斯"],
    "美系": ["特斯拉", "凯迪拉克", "别克", "福特"],
    "自主": ["比亚迪", "吉利", "奇瑞", "长安", "长城"],
    "新势力": ["理想", "蔚来", "小鹏", "问界", "零跑", "极氪", "小米"],
    "代步车": ["紧凑型", "小型", "灵活好停车", "低油耗", "纯电动"],
    "绿牌": ["纯电动", "插电混动", "增程式"],
    "油车": ["燃油", "汽油"],
    "跑长途": ["长续航", "增程式", "插电混动", "燃油"],
    "保值": ["高保值率", "热销", "主流品牌"],
}


class QueryExpander:
    """Expands queries with domain synonyms and multi-perspective rewrites."""

    @staticmethod
    def expand_query(query_text: str) -> str:
        """Expand natural language query with domain synonyms."""
        if not query_text:
            return query_text

        expanded_tokens: List[str] = [query_text]

        for key, synonyms in AUTOMOTIVE_SYNONYMS.items():
            if key in query_text:
                expanded_tokens.extend(synonyms[:3])

        return " ".join(expanded_tokens)
