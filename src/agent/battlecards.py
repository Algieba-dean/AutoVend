"""
Competitor Battlecards & Comparative Pitching Module for AutoVend Agent.

Detects competitor vehicle mentions in customer input and provides grounded
tactical battlecard guidance for value positioning and comparison.
"""

import logging
import re
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Battlecard(BaseModel):
    """Battlecard data structure for a competitor model or brand."""

    name: str
    category: str
    target_competitors: List[str]
    strengths: List[str]  # What competitor is known for
    counter_points: List[str]  # Pitching angles & value positioning for AutoVend models

    def to_system_note(self) -> str:
        """Format battlecard into a concise system note for response generator."""
        strengths_str = "、".join(self.strengths)
        counter_str = "；".join([f"({i+1}) {cp}" for i, cp in enumerate(self.counter_points)])
        return (
            f"[系统竞品战术卡提示]: 检测到客户提及/关注竞品【{self.name}】（竞品卖点: {strengths_str}）。"
            f"请在回复中予以客观尊重，同时从以下维度突出推荐车型的差异化优势：{counter_str}。"
        )


# Comprehensive automotive battlecard registry
BATTLECARDS_REGISTRY: List[Battlecard] = [
    Battlecard(
        name="特斯拉 Model Y / Model 3",
        category="纯电中型车/SUV",
        target_competitors=["model y", "model 3", "特斯拉", "tesla"],
        strengths=["品牌影响力", "三电效率高", "辅助驾驶体验"],
        counter_points=[
            "强调我方推荐车型的内饰豪华感与做工舒适度（如 Nappa 真皮、座椅通风/按摩/加热）",
            "对比二排乘坐空间与后排静音 NVH 表现（特斯拉底盘偏硬、胎噪明显）",
            "突出本地化智能座舱生态（语音控制、车机本土 App 兼容）",
        ],
    ),
    Battlecard(
        name="理想 L7 / L8",
        category="增程式中大型SUV",
        target_competitors=["理想l7", "理想l8", "理想", "l7", "l8"],
        strengths=["大空间二排", "家庭冰箱彩电大沙发", "无续航焦虑"],
        counter_points=[
            "若对比纯电车型，突出800V高压快充超低用能成本与纯电极致平顺",
            "若对比混动/增程，突出底盘机械素质、双叉臂悬架调校与底盘操控稳健性",
            "对比购车落地性价比及终身质保保障",
        ],
    ),
    Battlecard(
        name="问界 M7 / M9",
        category="增程/纯电智能SUV",
        target_competitors=["问界", "问界m7", "问界m9", "m7", "m9", "huawei", "鸿蒙"],
        strengths=["华为鸿蒙座舱", "高阶智驾 ADS 2.0/3.0"],
        counter_points=[
            "客观认可其智驾能力，引导聚焦于日常使用最频繁的“空间实操性”与“整车质感”",
            "对比相同配置下的实际落地价格优势（性价比）",
            "强调三电核心技术积累与电池安全防护体系",
        ],
    ),
    Battlecard(
        name="比亚迪 汉 / 唐",
        category="插混/纯电中大型车",
        target_competitors=["比亚迪", "byd", "汉ev", "汉dmi", "唐dmi"],
        strengths=["DM-i混动油耗低", "三电自研电池安全", "保有量大"],
        counter_points=[
            "对比车机系统的流畅度与智能化人机交互体验",
            "对比底盘悬架的质感与高规格铝合金用料",
            "强调个性化外观设计与年轻化运动基因",
        ],
    ),
    Battlecard(
        name="蔚来 ES6 / ET5",
        category="纯电高端车",
        target_competitors=["蔚来", "nio", "es6", "et5"],
        strengths=["换电服务", "NOMI人机交互", "品牌社群"],
        counter_points=[
            "对比车价及电池租用 BaaS 长期费率成本",
            "强调超充网络覆盖普及度与无电池租赁费用的自主产权",
        ],
    ),
    Battlecard(
        name="传统燃油豪车 (BBA - 奔驰C/E/GLC, 宝马3/5/X3, 奥迪A4/A6/Q5)",
        category="传统豪华燃油车",
        target_competitors=["奔驰", "宝马", "奥迪", "bba", "glc", "x3", "q5", "3系", "5系", "c级", "e级"],
        strengths=["品牌溢价高", "机械底盘调校底蕴", "保值率预期"],
        counter_points=[
            "对比智能座舱体验（大屏交互、语音全车控、智能化感知）",
            "对比用能成本（电驱相比燃油车每年节省1-2万元油费）与无购置税优惠",
            "对比同价位下配置丰富度（标配即高配，无需昂贵选装）",
        ],
    ),
]


def match_battlecards(conversation_text: str) -> List[Battlecard]:
    """
    Search conversation history or latest text for competitor keywords
    and return matching Battlecards.
    """
    if not conversation_text:
        return []

    text_lower = conversation_text.lower()
    matched: List[Battlecard] = []

    for card in BATTLECARDS_REGISTRY:
        for kw in card.target_competitors:
            if kw in text_lower:
                matched.append(card)
                break

    return matched
