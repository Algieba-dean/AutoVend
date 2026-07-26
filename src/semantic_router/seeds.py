"""
Seed utterances for anchor construction.

These are the offline half of the semantic router: representative ways a
customer says each recurring thing. They are embedded once, clustered, and the
centroids become the anchors the online router compares against. The seeds
themselves never ship — only the vectors do.

Two families, split by what the system should *do* with the utterance:

**Control flow** — the turn steers the conversation without stating a
requirement. "行，听你的" carries no vehicle attribute; running a 70B model to
discover that is waste. These route to deterministic handling.

**Needs flow** — the turn states or revises a requirement. These must reach the
extractor, and the matched intent tells it which slot to look at.

Coverage over polish: each intent needs enough surface variety that K-means
finds real modes rather than paraphrases of one sentence. Formal and colloquial
registers both appear because customers use both, sometimes in one turn.
"""

from typing import Dict, List

# ── Control flow ──────────────────────────────────────────────────────

CONTROL_SEEDS: Dict[str, List[str]] = {
    "affirm": [
        "行，听你的",
        "好的，就这样吧",
        "可以，没问题",
        "嗯，我觉得不错",
        "对，就是这个意思",
        "是的没错",
        "OK，那就这么定了",
        "好啊，我同意",
        "行吧，那就这样",
        "可以的，继续",
        "没错，你说得对",
        "好，我接受这个方案",
    ],
    "reject": [
        "不太行",
        "这个我不喜欢",
        "不是我想要的",
        "换一个吧",
        "不合适",
        "我不太满意",
        "这个不行，再看看别的",
        "都不喜欢",
        "感觉不对",
        "不要这款",
        "这些都不符合我的要求",
        "算了，这个不考虑",
    ],
    "defer": [
        "我再想想吧",
        "让我考虑一下",
        "先不急",
        "回去和家人商量一下",
        "我再看看",
        "过两天再说",
        "暂时不着急决定",
        "容我考虑考虑",
        "我需要点时间",
        "先放着吧，我想想",
    ],
    "budget_objection": [
        "我预算不够",
        "太贵了",
        "超出我的预算了",
        "这个价格有点高",
        "便宜点的有吗",
        "我承受不起这个价位",
        "有没有实惠一点的",
        "价格能不能再低一些",
        "这超预算了",
        "我出不起这么多钱",
    ],
    "request_detail": [
        "详细说说这款车",
        "能介绍一下配置吗",
        "还有别的信息吗",
        "这车具体怎么样",
        "多讲讲这款",
        "参数是什么",
        "能不能说得更清楚一点",
        "我想了解更多细节",
    ],
    "smalltalk": [
        "你好",
        "在吗",
        "谢谢你",
        "麻烦了",
        "辛苦了",
        "哈喽",
        "早上好",
        "再见",
        "拜拜",
        "感谢",
    ],
    # The interrupt intent. Distinct from a first-time statement of a
    # requirement: these all contradict something already agreed, which is what
    # makes them a rollback trigger rather than another slot to fill. The
    # phrasings therefore lean on revision markers — 改成 / 还是 / 重新 / 其实.
    "update_constraint": [
        "我想改一下预算",
        "预算改成50万吧",
        "其实我还是想要油车",
        "算了，还是看SUV吧",
        "我改主意了，不要这个品牌",
        "刚才说的不算，重新来",
        "能不能换个价位看看",
        "我重新说一下需求",
        "之前说的预算作废",
        "还是想看看别的类型",
        "我想调整一下要求",
        "把品牌限制去掉吧",
    ],
}

# ── Needs flow ────────────────────────────────────────────────────────

NEEDS_SEEDS: Dict[str, List[str]] = {
    "budget": [
        "我有30万的预算",
        "预算大概20到30万",
        "价格控制在15万以内",
        "我想买50万左右的车",
        "预算比较充足，100万以上都可以",
        "最多花25万",
        "我的预算是40万",
        "十几万的车就行",
        "希望不超过60万",
        "手头有80万左右",
    ],
    "powertrain": [
        "我要油车，不要电车",
        "想买纯电动的",
        "混动的怎么样",
        "我不考虑电车",
        "插电混动可以吗",
        "还是燃油车靠谱",
        "增程式的有推荐吗",
        "我想要新能源车",
        "柴油的也行",
        "只看电动车",
    ],
    "usage": [
        "我日常通勤使用",
        "主要是上下班开",
        "周末带家人出去玩",
        "经常跑长途",
        "偶尔越野",
        "市区代步为主",
        "接送孩子上学",
        "商务接待用",
        "拉货用的",
        "自驾游比较多",
    ],
    "category": [
        "我想要一台SUV",
        "轿车比较适合我",
        "看看MPV",
        "想买个跑车",
        "紧凑型的就行",
        "要中大型SUV",
        "小车方便停",
        "七座的车有哪些",
        "两厢车怎么样",
        "皮卡有推荐吗",
    ],
    "brand": [
        "我比较喜欢宝马",
        "有没有丰田的",
        "德系车质量好",
        "想看看比亚迪",
        "国产品牌可以考虑",
        "只看BBA",
        "特斯拉怎么样",
        "日系车省油吧",
        "不要国产的",
        "蔚来有什么车型",
    ],
    "feature": [
        "要有自动驾驶辅助",
        "空间一定要大",
        "续航至少600公里",
        "安全配置要好",
        "座椅要舒服",
        "内饰质感要高级",
        "后备箱能装东西",
        "四驱的比较好",
        "智能化程度要高",
        "隔音效果要好",
        "油耗越低越好",
        "加速要快",
    ],
    "constraint": [
        "我家车位比较小",
        "小区充电不方便",
        "北方冬天冷，续航会不会打折",
        "我驾龄不长，要好开的",
        "限牌城市，要新能源指标",
        "经常要走烂路",
        "家里有老人，上下车要方便",
    ],
}

#: Family labels. The router reports these so callers can branch on "does this
#: turn need the extractor" without enumerating every intent.
CONTROL_FLOW = "control"
NEEDS_FLOW = "needs"


def all_seeds() -> Dict[str, Dict[str, List[str]]]:
    """Seeds grouped by family, then by intent."""
    return {CONTROL_FLOW: CONTROL_SEEDS, NEEDS_FLOW: NEEDS_SEEDS}


def family_of(intent: str) -> str:
    """Which family an intent belongs to."""
    if intent in CONTROL_SEEDS:
        return CONTROL_FLOW
    if intent in NEEDS_SEEDS:
        return NEEDS_FLOW
    raise KeyError(f"Unknown intent: {intent!r}")


def seed_count() -> int:
    return sum(len(utterances) for family in all_seeds().values() for utterances in family.values())
