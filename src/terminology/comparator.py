"""
Cross-Brand Automotive Technology Comparator (src/terminology/comparator.py).

Implements:
1. Cross-brand functional equivalence domain mapping
2. Multi-dimensional technical matrix comparison
3. Differentiator analysis and customer sales advisory generation
"""

import logging
from typing import Dict, List, Optional, Set

from src.terminology.resolver import TerminologyResolver
from src.terminology.schemas import (
    EquivalenceDomain,
    TechComparisonDimension,
    TechComparisonMatrix,
    TechnologyEntity,
)

logger = logging.getLogger(__name__)

EQUIVALENCE_DOMAIN_NAMES: Dict[EquivalenceDomain, str] = {
    EquivalenceDomain.ACTIVE_BODY_CONTROL: "智能车身控制与主动底盘悬架",
    EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM: "800V/900V高压碳化硅极速补能平台",
    EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING: "端到端无图全场景城市高阶智驾",
    EquivalenceDomain.INTEGRATED_BATTERY_SAFETY: "高安全电芯与电池车身一体化架构",
    EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING: "多电机独立驱动与极致扭矩矢量控制",
    EquivalenceDomain.INTELLIGENT_COCKPIT_OS: "跨端多屏互联全场景智能座舱系统",
    EquivalenceDomain.GIGACASTING_STRUCTURE: "超大吨位一体化压铸车身轻量化制造",
    EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM: "智能多挡混动与电四驱系统架构",
    EquivalenceDomain.SOLID_STATE_BATTERY_TECH: "半固态与全固态高能量密度电池系统",
    EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING: "数字化智慧底盘与全轮线控转向",
}

EQUIVALENCE_DOMAIN_TARGETS: Dict[EquivalenceDomain, str] = {
    EquivalenceDomain.ACTIVE_BODY_CONTROL: "抑制车身俯仰侧倾、过滤路面颠簸、提升乘坐舒适度与操控稳定性",
    EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM: "缩短长途服务区充电时间、降低电能传输损耗、提升冬季低温充电性能",
    EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING: "减轻复杂城市道路与高速驾驶疲劳、提升未知危险障碍物紧急主动避险能力",
    EquivalenceDomain.INTEGRATED_BATTERY_SAFETY: "防止动力电池热失控起火扩散、提高整车抗扭刚度与车内乘坐垂直空间",
    EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING: "实现超跑级极限加速、原地掉头转向、极端爆胎险境下的毫秒级车辆防失控",
    EquivalenceDomain.INTELLIGENT_COCKPIT_OS: "手机车机生态丝滑无缝流转、多音区拟人化语音交互与全车智能设备联动",
    EquivalenceDomain.GIGACASTING_STRUCTURE: "精简焊点与零部件数量、车身深度减重抗扭、提升碰撞被动安全",
    EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM: "兼顾强劲动力爆发与超低馈电油耗，解决长途跨省续航焦虑与严寒低温衰减",
    EquivalenceDomain.SOLID_STATE_BATTERY_TECH: "突破动力电池能量密度天花板，提升极致安全不起火性能，实现千公里纯电长续航",
    EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING: "彻底解耦转向与悬架物理约束，缩小大型车转弯半径，实现蟹行变道与极致灵动",
}


class TechnologyComparator:
    """
    Cross-Brand Technology Equivalence & Comparative Analysis Engine.
    """

    def __init__(self, resolver: Optional[TerminologyResolver] = None):
        self.resolver = resolver or TerminologyResolver()

    def get_equivalents(self, term_or_id: str) -> List[TechnologyEntity]:
        """
        Get all equivalent rival technologies across competing brands for a given term or ID.
        """
        entity: Optional[TechnologyEntity] = self.resolver.get_entity(term_or_id)
        if not entity:
            res = self.resolver.resolve(term_or_id)
            if res and res.primary_entity:
                entity = res.primary_entity

        if not entity or not entity.equivalence_group_id:
            return []

        # Find all other entities sharing the same equivalence domain across competing brands
        rivals: List[TechnologyEntity] = []
        for cand in self.resolver.registry.values():
            if (
                cand.equivalence_group_id == entity.equivalence_group_id
                and cand.id != entity.id
                and cand.brand_key != entity.brand_key
            ):
                rivals.append(cand)

        # Sort rivals: proprietary OEM technologies take precedence over generic concepts
        if not entity.is_generic:
            rivals.sort(key=lambda x: (1 if x.is_generic else 0, x.name))
        else:
            rivals.sort(key=lambda x: (0 if x.is_generic else 1, x.name))

        return rivals

    def compare(self, terms_or_ids: List[str]) -> TechComparisonMatrix:
        """
        Generate a comprehensive comparative matrix across 2 or more technology terms or IDs.

        Args:
            terms_or_ids: List of terms, e.g. ['云辇', '途灵', '魔毯'] or ['V800', '巨鲸800V']
        """
        resolved_entities: List[TechnologyEntity] = []
        seen_ids: Set[str] = set()

        for item in terms_or_ids:
            ent = self.resolver.get_entity(item)
            if not ent:
                res = self.resolver.resolve(item)
                if res and res.primary_entity:
                    ent = res.primary_entity
            if ent and ent.id not in seen_ids:
                resolved_entities.append(ent)
                seen_ids.add(ent.id)

        if not resolved_entities:
            return TechComparisonMatrix(
                domain_chinese_name="未知技术对比",
                target_function="未检测到有效技术实体",
                summary_markdown="未能成功识别待对比的技术名词，请提供具体的车企专有名词。",
            )

        # If only 1 item provided as a compound query string (e.g. "双腔空悬和魔毯哪个好"), extract multiple terms
        if len(terms_or_ids) == 1 and len(resolved_entities) <= 1:
            extracted = self.resolver.extract_terms(terms_or_ids[0])
            if len(extracted) >= 2:
                resolved_entities = []
                seen_ids = set()
                for m in extracted:
                    if m.entity.id not in seen_ids:
                        resolved_entities.append(m.entity)
                        seen_ids.add(m.entity.id)

        # If only 1 entity provided, automatically find its cross-brand equivalents to compare!
        if len(resolved_entities) == 1:
            primary = resolved_entities[0]
            rivals = self.get_equivalents(primary.id)
            for r in rivals[:3]:  # Top rivals
                resolved_entities.append(r)

        # Detect primary common domain (majority vote among entities)
        from collections import Counter
        domain_counts = Counter(e.equivalence_group_id for e in resolved_entities if e.equivalence_group_id)
        if domain_counts:
            primary_domain, top_count = domain_counts.most_common(1)[0]
            if len(domain_counts) > 1 and top_count <= 1:
                primary_domain = None
        else:
            primary_domain = None

        if primary_domain:
            domain_name = EQUIVALENCE_DOMAIN_NAMES.get(primary_domain, "跨车企技术体系横向对比")
            target_function = EQUIVALENCE_DOMAIN_TARGETS.get(primary_domain, "综合新能源三电与整车智能化能力对比")
        else:
            domain_name = "跨车企综合技术横评"
            target_function = "对比不同领域的核心技术架构与整车体验侧重"

        # Build comparison dimensions
        dimensions: List[TechComparisonDimension] = [
            TechComparisonDimension(
                dimension_name="车企品牌与定位",
                tech_evaluations={e.name: f"{e.brand} ({e.english_name})" for e in resolved_entities},
            ),
            TechComparisonDimension(
                dimension_name="核心硬件与实现路线",
                tech_evaluations={
                    e.name: "；".join(e.technical_principles[:2]) if e.technical_principles else e.subcategory
                    for e in resolved_entities
                },
            ),
            TechComparisonDimension(
                dimension_name="独家差异化优势",
                tech_evaluations={
                    e.name: "；".join(e.advantages[:2]) if e.advantages else e.summary
                    for e in resolved_entities
                },
            ),
            TechComparisonDimension(
                dimension_name="代表量产车型",
                tech_evaluations={
                    e.name: "、".join(e.representative_vehicles[:3]) if e.representative_vehicles else "全系车型"
                    for e in resolved_entities
                },
            ),
        ]

        # Build key differentiators
        differentiators: Dict[str, str] = {}
        for e in resolved_entities:
            top_adv = e.advantages[0] if e.advantages else e.summary
            differentiators[e.name] = f"侧重于{e.subcategory}，核心亮点是：{top_adv}"

        # Build sales guidance summary
        sales_guidance_parts: List[str] = []
        for e in resolved_entities:
            pt = e.sales_talking_points[0] if e.sales_talking_points else f"突出{e.name}的独家优势"
            sales_guidance_parts.append(f"【{e.brand}】{pt}")
        sales_guidance = "\n".join(sales_guidance_parts)

        # Format markdown comparison table
        markdown_table = self.format_comparison_table(
            domain_name=domain_name,
            target_function=target_function,
            entities=resolved_entities,
            dimensions=dimensions,
            sales_guidance=sales_guidance,
        )

        return TechComparisonMatrix(
            equivalence_domain=primary_domain,
            domain_chinese_name=domain_name,
            target_function=target_function,
            compared_entities=resolved_entities,
            dimensions=dimensions,
            key_differentiators=differentiators,
            sales_guidance=sales_guidance,
            summary_markdown=markdown_table,
        )

    def format_comparison_table(
        self,
        domain_name: str,
        target_function: str,
        entities: List[TechnologyEntity],
        dimensions: List[TechComparisonDimension],
        sales_guidance: str,
    ) -> str:
        """Render a formatted markdown comparison report."""
        lines = [
            f"### 🚗 跨车企技术横评：{domain_name}",
            f"> **功能目标**：{target_function}\n",
        ]

        # Table header
        headers = ["评估维度"] + [e.name for e in entities]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Table rows
        for dim in dimensions:
            row = [dim.dimension_name]
            for e in entities:
                val = dim.tech_evaluations.get(e.name, "-")
                # Clean line breaks for table cell
                val_clean = val.replace("\n", " ")
                row.append(val_clean)
            lines.append("| " + " | ".join(row) + " |")

        lines.append("\n#### 💡 导购建议与销售对策")
        lines.append(sales_guidance)

        return "\n".join(lines)
