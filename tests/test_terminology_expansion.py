"""
Comprehensive Unit and Integration Tests for Extended Automotive Terminology
and Generic Technology Systems (tests/test_terminology_expansion.py).

Covers:
1. 9 New OEM Proprietary Technologies (IM, GAC Aion, GWM, Chery, Porsche, Mercedes, BMW, HIMA Maextro/Xuanwu).
2. 23 Generic Automotive Engineering Concepts (Chassis, Battery, Autonomous Driving, Powertrain & Charging).
3. Ambiguity resolution & Brand Context weighting.
4. Equivalence Domains and Comparative Analysis.
5. Query Expansion and Retrieval Integration.
"""

import pytest

from src.core.terminology import (
    AutomotiveKnowledgeGraph,
    EquivalenceDomain,
    TechMaturity,
    TechnologyComparator,
    TerminologyResolver,
)
from src.retrieval.query_expander import QueryExpander
from src.retrieval.query_transform import QueryTransformationEngine
from src.terminology.generic_registry import GENERIC_AUTOMOTIVE_TECHNOLOGIES

# =============================================================================
# 1. OEM Registry Expansion Tests
# =============================================================================

def test_oem_expanded_entities_exist():
    """Verify all 9 new OEM technologies are registered in the knowledge graph."""
    resolver = AutomotiveKnowledgeGraph.get_instance().resolver

    new_oem_ids = [
        "im_lizard_chassis",
        "gac_magazine_battery",
        "gwm_hi4_hybrid",
        "chery_kunpeng_cdm",
        "porsche_active_ride",
        "mercedes_eva_amg",
        "bmw_gen6_edrive",
        "hima_maextro_platform",
        "hima_xuanwu_body",
    ]

    for entity_id in new_oem_ids:
        entity = resolver.get_entity(entity_id)
        assert entity is not None, f"Expected OEM entity '{entity_id}' to be registered"
        assert not entity.is_generic
        assert len(entity.aliases) >= 3
        assert len(entity.technical_principles) >= 1
        assert len(entity.advantages) >= 1
        assert len(entity.limitations) >= 1
        assert len(entity.sales_talking_points) >= 1
        assert len(entity.representative_vehicles) >= 1
        assert entity.maturity in (TechMaturity.MASS_PRODUCTION, TechMaturity.PRE_RESEARCH, TechMaturity.CONCEPT)


@pytest.mark.parametrize(
    "query_term,brand_context,expected_id",
    [
        ("灵蜥数字底盘", None, "im_lizard_chassis"),
        ("灵蜥底盘", "im", "im_lizard_chassis"),
        ("弹匣电池", None, "gac_magazine_battery"),
        ("弹匣电池2.0", "gac_aion", "gac_magazine_battery"),
        ("Hi4-T", None, "gwm_hi4_hybrid"),
        ("坦克Hi4-T", "gwm", "gwm_hi4_hybrid"),
        ("长城Hi4", None, "gwm_hi4_hybrid"),
        ("鲲鹏超能混动", None, "chery_kunpeng_cdm"),
        ("鲲鹏C-DM", "chery", "chery_kunpeng_cdm"),
        ("Active Ride", None, "porsche_active_ride"),
        ("保时捷主动悬架", "porsche", "porsche_active_ride"),
        ("EVA平台", "mercedes", "mercedes_eva_amg"),
        ("AMG电驱", "mercedes", "mercedes_eva_amg"),
        ("第六代eDrive", "bmw", "bmw_gen6_edrive"),
        ("宝马大圆柱电池", "bmw", "bmw_gen6_edrive"),
        ("尊界S800", "hima", "hima_maextro_platform"),
        ("龙行平台", "hima", "hima_maextro_platform"),
        ("玄武车身", "hima", "hima_xuanwu_body"),
        ("玄武架构", None, "hima_xuanwu_body"),
    ],
)
def test_oem_resolution_and_aliases(query_term, brand_context, expected_id):
    """Test resolution of expanded OEM terms with and without brand context."""
    resolver = TerminologyResolver()
    res = resolver.resolve(query_term, context=brand_context or "")
    assert res is not None, f"Failed to resolve '{query_term}'"
    assert res.primary_entity.id == expected_id
    assert res.confidence >= 0.7


# =============================================================================
# 2. Generic Technology Registry Tests
# =============================================================================

def test_generic_technologies_coverage_and_metadata():
    """Verify that all generic technologies are structured and present across 6 categories."""
    assert len(GENERIC_AUTOMOTIVE_TECHNOLOGIES) >= 100

    resolver = TerminologyResolver()
    categories_found = set()

    for tech in GENERIC_AUTOMOTIVE_TECHNOLOGIES:
        assert tech.is_generic is True
        assert tech.brand_key == "generic"
        assert tech.generic_category in ["悬架形式", "电池形态", "智驾与算法", "补能与电气", "智能座舱", "车身安全"]
        categories_found.add(tech.generic_category)

        # Ensure registered in resolver
        entity = resolver.get_entity(tech.id)
        assert entity is not None, f"Generic tech {tech.id} missing in resolver"
        assert entity.is_generic is True

    assert len(categories_found) >= 6, f"All 6 generic categories must be covered, got {categories_found}"


@pytest.mark.parametrize(
    "query_term,expected_id",
    [
        # 1. 悬架形式
        ("麦弗逊", "generic_macpherson_suspension"),
        ("麦弗逊式独立悬架", "generic_macpherson_suspension"),
        ("双叉臂", "generic_double_wishbone_suspension"),
        ("双叉臂式独立悬架", "generic_double_wishbone_suspension"),
        ("五连杆", "generic_multilink_suspension"),
        ("五连杆独立悬架", "generic_multilink_suspension"),
        ("CDC减振器", "generic_cdc_damping"),
        ("CDC电磁减振", "generic_cdc_damping"),
        ("单腔空气悬架", "generic_air_suspension"),
        ("空气悬架", "generic_air_suspension"),
        # 2. 电池形态
        ("三元锂", "generic_ternary_lithium_battery"),
        ("磷酸铁锂电池", "generic_lfp_battery"),
        ("半固态电池", "generic_solid_state_battery"),
        ("全固态电池", "generic_solid_state_battery"),
        ("CTB电池车身一体化", "generic_ctb_technology"),
        ("CTC电芯底盘一体化", "generic_ctc_technology"),
        # 3. 智驾与算法
        ("端到端大模型", "generic_end_to_end_autonomous_driving"),
        ("E2E智驾", "generic_end_to_end_autonomous_driving"),
        ("Occupancy占用网络", "generic_occupancy_network"),
        ("BEV+Transformer", "generic_bev_transformer"),
        ("车载激光雷达", "generic_lidar_sensor"),
        ("无图城市NOA", "generic_mapless_urban_noa"),
        # 4. 补能与电气
        ("EREV", "generic_erev_powertrain"),
        ("增程式电动", "generic_erev_powertrain"),
        ("插电式混合动力", "generic_phev_powertrain"),
        ("三电机驱动", "generic_multi_motor_drive"),
        ("四电机独立驱动", "generic_multi_motor_drive"),
        ("4C超充", "generic_ultra_fast_charging_4c_5c"),
        ("5C极速充电", "generic_ultra_fast_charging_4c_5c"),
    ],
)
def test_generic_resolution_aliases(query_term, expected_id):
    """Test resolution of generic automotive technical terms."""
    resolver = TerminologyResolver()
    res = resolver.resolve(query_term)
    assert res is not None, f"Failed to resolve '{query_term}'"
    assert res.primary_entity.id == expected_id
    assert res.primary_entity.is_generic is True


# =============================================================================
# 3. Brand Context and Disambiguation Tests
# =============================================================================

def test_brand_context_disambiguation():
    """Verify that brand context tilts ambiguous terms to the brand-specific tech."""
    resolver = TerminologyResolver()

    # Case 1: '800V' with Xiaomi vs Generic
    res_xiaomi = resolver.resolve("800V高压碳化硅", context="xiaomi")
    assert res_xiaomi.primary_entity.id == "xiaomi_v800_sic"

    res_generic = resolver.resolve("800V高压碳化硅", context="generic")
    assert res_generic.primary_entity.id == "generic_800v_sic_architecture"

    # Case 2: '后轮转向' with IM Motors vs Generic
    res_im = resolver.resolve("后轮转向", context="im")
    assert res_im.primary_entity.id == "im_lizard_chassis"

    res_gen_steer = resolver.resolve("后轮转向", context="generic")
    assert res_gen_steer.primary_entity.id == "generic_rear_wheel_steering"

    # Case 3: '混动' with GWM vs Chery
    res_gwm = resolver.resolve("智能混动系统", context="长城魏牌坦克")
    assert res_gwm.primary_entity.id == "gwm_hi4_hybrid"

    res_chery = resolver.resolve("超能混动", context="奇瑞风云星途")
    assert res_chery.primary_entity.id == "chery_kunpeng_cdm"


# =============================================================================
# 4. Equivalence Domains & Comparator Tests
# =============================================================================

def test_new_equivalence_domains():
    """Test new equivalence domains: Hybrid powertrain, solid state battery, intelligent chassis."""
    resolver = TerminologyResolver()
    comparator = TechnologyComparator(resolver=resolver)

    # 1. Hybrid Powertrain Domain
    hybrids = [e for e in resolver.registry.values() if e.equivalence_group_id == EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM]
    hybrid_ids = {h.id for h in hybrids}
    assert "gwm_hi4_hybrid" in hybrid_ids
    assert "chery_kunpeng_cdm" in hybrid_ids

    # 2. Intelligent Chassis Steering Domain
    steerings = [e for e in resolver.registry.values() if e.equivalence_group_id == EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING]
    steering_ids = {s.id for s in steerings}
    assert "im_lizard_chassis" in steering_ids

    # 3. Solid State Battery Domain
    solids = [e for e in resolver.registry.values() if e.equivalence_group_id == EquivalenceDomain.SOLID_STATE_BATTERY_TECH]
    solid_ids = {s.id for s in solids}
    assert "generic_solid_state_battery" in solid_ids

    # Cross-brand equivalents lookup
    rivals_hi4 = comparator.get_equivalents("gwm_hi4_hybrid")
    rival_ids = {r.id for r in rivals_hi4}
    assert "chery_kunpeng_cdm" in rival_ids


def test_comparison_report_between_new_technologies():
    """Verify structured comparison matrix generation between newly added technologies."""
    comparator = TechnologyComparator()

    matrix = comparator.compare(["gwm_hi4_hybrid", "chery_kunpeng_cdm"])
    assert matrix is not None
    assert matrix.equivalence_domain == EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM
    compared_ids = {e.id for e in matrix.compared_entities}
    assert "gwm_hi4_hybrid" in compared_ids
    assert "chery_kunpeng_cdm" in compared_ids
    assert len(matrix.dimensions) >= 3
    assert len(matrix.summary_markdown) > 50


# =============================================================================
# 5. Query Expansion and Retrieval Integration Tests
# =============================================================================

def test_query_expander_with_expanded_terms():
    """Verify QueryExpander and TerminologyResolver enrich queries with new terms."""
    resolver = TerminologyResolver()

    # Test RAG expansion for IM Lizard Chassis
    expanded_im = resolver.expand_for_rag("智己灵蜥底盘")
    assert len(expanded_im) >= 1
    assert any("灵蜥" in term or "智己" in term for term in expanded_im)

    # Test QueryExpander integration
    expanded_query = QueryExpander.expand_query("我想了解智己灵蜥底盘和弹匣电池")
    assert "智己" in expanded_query
    assert "弹匣电池" in expanded_query


def test_query_transformation_engine_integration():
    """Verify QueryTransformationEngine generates enriched search representations for new tech."""
    engine = QueryTransformationEngine()

    result = engine.transform_all("我想了解长城Hi4和奇瑞C-DM混动有什么区别")
    assert result["original_query"] == "我想了解长城Hi4和奇瑞C-DM混动有什么区别"
    assert "rewritten_query" in result
    assert "expanded_query" in result
    assert len(result["expanded_query"]) >= len(result["original_query"])
    assert "multi_queries" in result
    assert len(result["multi_queries"]) >= 1


# =============================================================================
# 6. Graph Relational Traversal & Domain Mapping Rigor Tests
# =============================================================================

def test_knowledge_graph_indexes_generic_and_oem_technologies():
    """Verify AutomotiveKnowledgeGraph indices cover both OEM and generic engineering concepts."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    # 1. Brand index check for generic tech
    generic_techs = kg.get_brand_technologies("generic")
    assert len(generic_techs) == len(GENERIC_AUTOMOTIVE_TECHNOLOGIES)
    assert any(t.id == "generic_macpherson_suspension" for t in generic_techs)

    # 2. Vehicle index check for vehicles mapped to generic technologies
    dolphin_techs = kg.get_vehicle_technologies("比亚迪海豚")
    assert len(dolphin_techs) >= 1
    assert any(t.id == "generic_macpherson_suspension" for t in dolphin_techs)


def test_hybrid_domain_mapping_and_rival_prioritization():
    """Verify that BYD DM-i, Ideal Range Extender, GWM Hi4, and Chery C-DM form a complete rival cluster."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    comparator = kg.comparator
    resolver = kg.resolver

    # 1. BYD DM-i and Ideal Range Extender have HYBRID_POWERTRAIN_SYSTEM
    byd_dmi = resolver.get_entity("byd_dmi_dmp")
    assert byd_dmi is not None
    assert byd_dmi.equivalence_group_id == EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM

    ideal_ext = resolver.get_entity("ideal_range_extender")
    assert ideal_ext is not None
    assert ideal_ext.equivalence_group_id == EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM

    nio_swap = resolver.get_entity("nio_power_swap")
    assert nio_swap is not None
    assert nio_swap.equivalence_group_id == EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM

    # 2. GWM Hi4 rivals must include BYD DM-i and Chery C-DM
    hi4_rivals = comparator.get_equivalents("gwm_hi4_hybrid")
    hi4_rival_ids = [r.id for r in hi4_rivals]
    assert "chery_kunpeng_cdm" in hi4_rival_ids
    assert "byd_dmi_dmp" in hi4_rival_ids
    assert "ideal_range_extender" in hi4_rival_ids

    # 3. OEM rivals must be prioritized ahead of generic concepts in get_equivalents
    disus_rivals = comparator.get_equivalents("byd_disus")
    top_3_names = [r.name for r in disus_rivals[:3]]
    # Top 3 rivals must all be OEM proprietary technologies, NOT generic suspension
    for name in top_3_names:
        assert "麦弗逊" not in name
        assert "双叉臂" not in name


# =============================================================================
# 7. Disambiguation, Multi-term Extraction & Compound Query Tests
# =============================================================================

@pytest.mark.parametrize(
    "query_term,expected_id",
    [
        ("双腔空悬", "generic_dual_chamber_air_suspension"),
        ("后轮转向", "generic_rear_wheel_steering"),
        ("一体化压铸", "generic_gigacasting_integrated_die_casting"),
        ("车载冰箱", "generic_in_car_refrigerator_cooling_heating"),
        ("换电", "generic_automated_battery_swapping"),
    ],
)
def test_zero_context_generic_resolution(query_term, expected_id):
    """Verify zero-context queries resolve to generic engineering entities instead of arbitrary OEMs."""
    resolver = TerminologyResolver()
    res = resolver.resolve(query_term)
    assert res is not None, f"Failed to resolve '{query_term}'"
    assert res.primary_entity.id == expected_id, f"Expected {expected_id}, got {res.primary_entity.id}"
    assert res.primary_entity.is_generic is True


def test_multi_term_sentence_extraction():
    """Verify multi-term extraction accurately parses both generic and OEM entities without hint collision."""
    resolver = TerminologyResolver()
    extracted = resolver.extract_terms("双腔空悬和魔毯哪个好")
    extracted_ids = {item.entity.id for item in extracted}

    assert "generic_dual_chamber_air_suspension" in extracted_ids
    assert "ideal_magic_carpet" in extracted_ids


def test_comparator_compound_query_resolution():
    """Verify TechnologyComparator handles compound query strings by extracting and comparing both entities."""
    comparator = TechnologyComparator()
    matrix = comparator.compare(["双腔空悬和魔毯哪个好"])

    assert matrix is not None
    compared_ids = {e.id for e in matrix.compared_entities}
    assert "generic_dual_chamber_air_suspension" in compared_ids
    assert "ideal_magic_carpet" in compared_ids
    assert len(matrix.dimensions) >= 3


