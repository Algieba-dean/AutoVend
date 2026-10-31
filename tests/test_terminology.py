"""
Comprehensive Automated Unit Tests for OEM Automotive Proprietary Terminology
and Knowledge Graph System (tests/test_terminology.py).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from src.agent.plugins import AgentPluginPipeline
from src.agent.schemas import SessionState
from src.core.terminology import (
    AutomotiveKnowledgeGraph,
    EquivalenceDomain,
    TechCategory,
    TechnologyComparator,
    TerminologyResolver,
)
from src.retrieval.query_expander import QueryExpander
from src.retrieval.query_transform import QueryTransformationEngine


# -----------------------------------------------------------------------------
# 1. Taxonomy & Registry Structure Tests
# -----------------------------------------------------------------------------
def test_taxonomy_categories_and_brands_coverage():
    """Verify that all major Chinese and global automakers and categories are registered."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    resolver = kg.resolver

    # Ensure all core categories have entities registered
    for cat in [
        TechCategory.CHASSIS_SUSPENSION,
        TechCategory.POWERTRAIN_MOTOR,
        TechCategory.BATTERY_CHARGING,
        TechCategory.AUTONOMOUS_DRIVING,
        TechCategory.PLATFORM_ARCHITECTURE,
        TechCategory.COCKPIT_OS,
        TechCategory.MANUFACTURING_SAFETY,
    ]:
        entities = resolver.list_entities_by_category(cat)
        assert len(entities) > 0, f"Category {cat} should have registered technologies"

    # Ensure required OEM brands exist
    required_brands = ["byd", "xiaomi", "hima", "tesla", "li_auto", "zeekr", "nio", "xpeng"]
    for brand in required_brands:
        techs = resolver.list_entities_by_brand(brand)
        assert len(techs) >= 30, f"Brand {brand} must have at least 30 registered proprietary technologies, got {len(techs)}"

    # Spot check specific requested technologies
    assert resolver.get_entity("byd_disus") is not None
    assert resolver.get_entity("byd_e4") is not None
    assert resolver.get_entity("byd_blade_battery") is not None
    assert resolver.get_entity("xiaomi_v800_sic") is not None
    assert resolver.get_entity("xiaomi_modena") is not None
    assert resolver.get_entity("xiaomi_hyperengine") is not None
    assert resolver.get_entity("hima_tuling") is not None
    assert resolver.get_entity("hima_ads") is not None
    assert resolver.get_entity("tesla_4680_battery") is not None
    assert resolver.get_entity("ideal_magic_carpet") is not None
    assert resolver.get_entity("zeekr_sea") is not None
    assert resolver.get_entity("zeekr_golden_battery") is not None
    assert resolver.get_entity("zeekr_haohan_ad") is not None
    assert resolver.get_entity("nio_skyride") is not None
    assert resolver.get_entity("nio_power_swap") is not None


# -----------------------------------------------------------------------------
# 2. Alias Matching & Normalization Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query_term,expected_id",
    [
        ("V800", "xiaomi_v800_sic"),
        ("v800", "xiaomi_v800_sic"),
        ("V800电车架构", "xiaomi_v800_sic"),
        ("800V碳化硅", "xiaomi_v800_sic"),
        ("871V", "xiaomi_v800_sic"),
        ("云辇", "byd_disus"),
        ("云辇系统", "byd_disus"),
        ("云辇-P", "byd_disus"),
        ("DiSus", "byd_disus"),
        ("yunnian", "byd_disus"),
        ("易四方", "byd_e4"),
        ("e4", "byd_e4"),
        ("刀片电池", "byd_blade_battery"),
        ("Blade Battery", "byd_blade_battery"),
        ("途灵", "hima_tuling"),
        ("途灵底盘", "hima_tuling"),
        ("Tuling Chassis", "hima_tuling"),
        ("乾崑智驾", "hima_ads"),
        ("ADS 3.0", "hima_ads"),
        ("摩德纳架构", "xiaomi_modena"),
        ("Modena", "xiaomi_modena"),
        ("V8s", "xiaomi_hyperengine"),
        ("27200rpm", "xiaomi_hyperengine"),
        ("魔毯", "ideal_magic_carpet"),
        ("魔毯空气悬架", "ideal_magic_carpet"),
        ("4680", "tesla_4680_battery"),
        ("4680结构化电池", "tesla_4680_battery"),
        ("金砖电池", "zeekr_golden_battery"),
        ("SEA浩瀚", "zeekr_sea"),
        ("浩瀚架构", "zeekr_sea"),
        ("浩瀚智驾", "zeekr_haohan_ad"),
        ("极氪智驾", "zeekr_haohan_ad"),
        ("浩瀚智驾2.0", "zeekr_haohan_ad"),
        ("天行底盘", "nio_skyride"),
        ("SkyRide", "nio_skyride"),
        ("天枢", "nio_skyos"),
        ("SkyOS", "nio_skyos"),
        ("换电架构", "nio_power_swap"),
        ("Power Swap", "nio_power_swap"),
        ("XNGP", "xpeng_xngp"),
        ("扶摇架构", "xpeng_fuyao"),
    ],
)
def test_alias_resolution(query_term, expected_id):
    """Test resolution of various alias formats and technical abbreviations."""
    resolver = TerminologyResolver()
    res = resolver.resolve(query_term)
    assert res is not None, f"Failed to resolve '{query_term}'"
    assert res.primary_entity is not None
    assert res.primary_entity.id == expected_id
    assert res.category == res.primary_entity.category
    assert res.confidence >= 0.7


# -----------------------------------------------------------------------------
# 3. Fuzzy Matching & Typo Tolerance Tests
# -----------------------------------------------------------------------------
def test_fuzzy_matching_and_typos():
    """Verify typo tolerance and fuzzy matching for automotive terms."""
    resolver = TerminologyResolver()

    # Typo 1: '云撵' instead of '云辇'
    res1 = resolver.resolve("云撵系统")
    assert res1 is not None
    assert res1.primary_entity.id == "byd_disus"

    # Typo 2: '图灵底盘' instead of '途灵底盘'
    res2 = resolver.resolve("图灵底盘")
    assert res2 is not None
    assert res2.primary_entity.id == "hima_tuling"

    # Typo 3: '乾昆智驾' instead of '乾崑智驾'
    res3 = resolver.resolve("乾昆智驾")
    assert res3 is not None
    assert res3.primary_entity.id == "hima_ads"

    # Typo 4: '金专电池' instead of '金砖电池'
    res4 = resolver.resolve("金专电池")
    assert res4 is not None
    assert res4.primary_entity.id == "zeekr_golden_battery"


# -----------------------------------------------------------------------------
# 4. Context-Aware Disambiguation Tests
# -----------------------------------------------------------------------------
def test_context_aware_disambiguation():
    """Verify that ambiguous acronyms (like '800V' or 'CTB') are disambiguated by context."""
    resolver = TerminologyResolver()

    # Context with Xiaomi hints
    res_xiaomi = resolver.resolve("800V架构", context="我想买小米SU7 Max，看重它那个800V")
    assert res_xiaomi is not None
    assert res_xiaomi.primary_entity.brand_key == "xiaomi"

    # Context with Huawei / HIMA hints
    res_huawei = resolver.resolve("800V架构", context="问界M9和智界S7的800V高压超充怎么样")
    assert res_huawei is not None
    assert res_huawei.primary_entity.brand_key == "hima"

    # CTB disambiguation: BYD vs Xiaomi
    res_byd_ctb = resolver.resolve("CTB", context="比亚迪海豹的CTB车身一体化技术")
    assert res_byd_ctb is not None
    assert res_byd_ctb.primary_entity.brand_key == "byd"

    res_xiaomi_ctb = resolver.resolve("CTB", context="小米SU7的倒置电芯CTB电池包")
    assert res_xiaomi_ctb is not None
    assert res_xiaomi_ctb.primary_entity.brand_key == "xiaomi"


# -----------------------------------------------------------------------------
# 5. Entity Extraction from Natural Language Sentences
# -----------------------------------------------------------------------------
def test_full_text_term_extraction():
    """Verify extracting multiple non-overlapping terms with exact spans."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    text = "我想对比一下小米的V800架构、比亚迪云辇系统以及华为途灵底盘的实际体验"

    terms = kg.extract_terms(text)
    assert len(terms) >= 3

    matched_ids = [t.entity.id for t in terms]
    assert "xiaomi_v800_sic" in matched_ids
    assert "byd_disus" in matched_ids
    assert "hima_tuling" in matched_ids

    # Spans check
    for t in terms:
        assert text[t.start_idx : t.end_idx] == t.matched_text


# -----------------------------------------------------------------------------
# 6. Cross-Brand Equivalence & Comparative Analysis Tests
# -----------------------------------------------------------------------------
def test_cross_brand_technology_comparison():
    """Verify comparative matrix generation for rival technologies (BYD vs Li Auto vs Huawei)."""
    comparator = TechnologyComparator()

    matrix = comparator.compare(["云辇", "魔毯", "途灵"])
    assert matrix.equivalence_domain == EquivalenceDomain.ACTIVE_BODY_CONTROL
    assert len(matrix.compared_entities) == 3
    assert len(matrix.dimensions) >= 3

    # Check that summary markdown contains table and guidance
    assert "| 评估维度 |" in matrix.summary_markdown
    assert "比亚迪" in matrix.summary_markdown
    assert "理想" in matrix.summary_markdown
    assert "华为" in matrix.summary_markdown
    assert "导购建议" in matrix.sales_guidance or "导购建议" in matrix.summary_markdown

    # Test rival equivalents lookup
    rivals = comparator.get_equivalents("byd_disus")
    rival_ids = [r.id for r in rivals]
    assert "ideal_magic_carpet" in rival_ids
    assert "hima_tuling" in rival_ids
    assert "nio_skyride" in rival_ids


def test_800v_platforms_comparison():
    """Verify comparative matrix for 800V fast-charging platforms across brands."""
    comparator = TechnologyComparator()

    matrix = comparator.compare(["V800", "巨鲸800V", "金砖电池"])
    assert matrix.equivalence_domain in [
        EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
    ]
    assert len(matrix.compared_entities) >= 2


# -----------------------------------------------------------------------------
# 7. Knowledge Graph Relations Tests
# -----------------------------------------------------------------------------
def test_knowledge_graph_relational_queries():
    """Verify graph queries by brand, vehicle, and synergistic co-occurrence."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    # Brand tech stack
    byd_stack = kg.get_brand_technologies("byd")
    assert len(byd_stack) >= 4
    byd_names = [e.name for e in byd_stack]
    assert any("云辇" in n for n in byd_names)
    assert any("易四方" in n for n in byd_names)
    assert any("刀片电池" in n for n in byd_names)

    # Vehicle tech stack
    u9_techs = kg.get_vehicle_technologies("仰望U9")
    u9_ids = [e.id for e in u9_techs]
    assert "byd_e4" in u9_ids
    assert "byd_disus" in u9_ids

    su7_techs = kg.get_vehicle_technologies("小米SU7")
    su7_ids = [e.id for e in su7_techs]
    assert "xiaomi_modena" in su7_ids
    assert "xiaomi_hyperengine" in su7_ids

    # Synergistic technologies
    disus_synergy = kg.get_synergistic_technologies("byd_disus")
    assert any(s.id == "byd_e4" for s in disus_synergy)


# -----------------------------------------------------------------------------
# 8. RAG Pipeline Integration Tests
# -----------------------------------------------------------------------------
def test_rag_query_expansion_with_terminology():
    """Verify RAG query expansion enriches query with formal labels and rival options."""
    # Single term query expansion
    expanded = QueryExpander.expand_query("我想找一款带云辇底盘的电车")
    assert "智能车身控制系统" in expanded or "连续可变阻尼" in expanded or "仰望U8" in expanded

    # Comparison query expansion
    expanded_compare = QueryExpander.expand_query("云辇和魔毯对比哪个更舒适")
    assert "云辇" in expanded_compare
    assert "魔毯" in expanded_compare
    # Should include rival technical labels
    assert "空气悬架" in expanded_compare or "阻尼" in expanded_compare

    # V800 query expansion
    expanded_v800 = QueryExpander.expand_query("有V800高压架构的车吗")
    assert "800V" in expanded_v800 or "碳化硅" in expanded_v800 or "小米SU7" in expanded_v800


def test_query_transformation_engine_hyde_enrichment():
    """Verify QueryTransformationEngine generates HyDE doc with proprietary tech specs."""
    engine = QueryTransformationEngine()
    hyde_doc = engine.generate_hyde_doc("请推荐带华为途灵底盘的豪华SUV")
    assert "途灵" in hyde_doc
    assert "【目标车型规格文档】" in hyde_doc


# -----------------------------------------------------------------------------
# 9. Agent Plugin Integration Tests
# -----------------------------------------------------------------------------
def test_terminology_plugin_in_agent_pipeline():
    """Verify TerminologyPlugin injects system notes and context flags for agent."""
    pipeline = AgentPluginPipeline()
    state = SessionState()
    context = {"user_input": "请问仰望U8的易四方和云辇底盘到底厉害在哪？"}

    # Run pre-response middleware
    pipeline.run_before_response(state, context)

    # Verify context flags
    assert context.get("terminology_matched", 0) >= 2
    assert "matched_technologies" in context

    # Verify state system notes
    assert len(state.system_notes) > 0
    note_text = "\n".join(state.system_notes)
    assert "[系统专有名词解析与导购策略提示]" in note_text
    assert "易四方" in note_text
    assert "云辇" in note_text


# -----------------------------------------------------------------------------
# 10. API Route Endpoints Tests
# -----------------------------------------------------------------------------
def test_terminology_api_endpoints():
    """Verify FastAPI routes for terminology resolution, extraction, and comparison."""
    client = TestClient(app)

    # 1. GET /api/terminology/resolve?term=V800
    res = client.get("/api/terminology/resolve?term=V800")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["primary_entity"]["id"] == "xiaomi_v800_sic"
    assert "800V" in data["formal_explanation"]

    # 2. POST /api/terminology/extract
    res_ext = client.post(
        "/api/terminology/extract",
        json={"text": "请问小米V800和问界途灵底盘哪个好"},
    )
    assert res_ext.status_code == 200
    ext_data = res_ext.json()
    assert ext_data["count"] == 2

    # 3. POST /api/terminology/compare
    res_cmp = client.post(
        "/api/terminology/compare",
        json={"terms": ["云辇", "魔毯", "途灵"]},
    )
    assert res_cmp.status_code == 200
    cmp_data = res_cmp.json()
    assert len(cmp_data["compared_entities"]) == 3
    assert "summary_markdown" in cmp_data

    # 4. GET /api/terminology/brand/byd
    res_brand = client.get("/api/terminology/brand/byd")
    assert res_brand.status_code == 200
    brand_data = res_brand.json()
    assert brand_data["count"] >= 4

    # 5. GET /api/terminology/categories
    res_cat = client.get("/api/terminology/categories")
    assert res_cat.status_code == 200
    cat_data = res_cat.json()
    assert "chassis_suspension" in cat_data["categories"]


# -----------------------------------------------------------------------------
# 11. Edge Cases & Robustness Regression Tests
# -----------------------------------------------------------------------------
def test_homonym_disambiguation_multi_term_sentence():
    """Verify multiple occurrences of homonyms in a single sentence are correctly disambiguated."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    # CTB disambiguation
    terms_ctb = kg.extract_terms("我想对比小米的CTB和比亚迪的CTB实际表现")
    assert len(terms_ctb) == 2
    assert terms_ctb[0].entity.id == "xiaomi_ctb_battery"
    assert terms_ctb[1].entity.id == "byd_ctb"

    # 800V disambiguation
    terms_800v = kg.extract_terms("请问小米的800V和华为的800V在充电速度上有什么区别")
    assert len(terms_800v) == 2
    assert terms_800v[0].entity.id == "xiaomi_v800_sic"
    assert terms_800v[1].entity.id == "hima_whale_800v"

    # Direct resolve with brand prefix
    res_xiaomi_800v = kg.resolve_term("小米的800V")
    assert res_xiaomi_800v is not None
    assert res_xiaomi_800v.primary_entity.id == "xiaomi_v800_sic"

    res_huawei_800v = kg.resolve_term("华为的800V")
    assert res_huawei_800v is not None
    assert res_huawei_800v.primary_entity.id == "hima_whale_800v"


def test_unlisted_fuzzy_typo_sentence_extraction():
    """Verify novel/unlisted typos in full sentences are extracted with fuzzy_alias type."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    # '图铃底盘' is not in aliases, but similar to '途灵底盘'
    terms = kg.extract_terms("请问问界M9的图铃底盘怎么样")
    assert len(terms) == 1
    assert terms[0].entity.id == "hima_tuling"
    assert terms[0].confidence >= 0.70


def test_english_word_boundary_isolation():
    """Verify pure ASCII aliases do not produce false positives inside English words."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    # 'season' must NOT match 'sea'
    terms_en = kg.extract_terms("In this season, automotive sales peaked.")
    assert len(terms_en) == 0

    # 'SEA' with Chinese must match
    terms_zh = kg.extract_terms("极氪SEA浩瀚架构支持高带宽扩展")
    assert len(terms_zh) >= 1
    assert any(t.entity.id == "zeekr_sea" for t in terms_zh)


def test_sales_note_deduplication_and_injection():
    """Verify sales notes do not duplicate advice blocks when the same term is repeated."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    note = kg.generate_system_sales_note("云辇底盘好不好？云辇有哪些版本？")
    assert note is not None
    assert note.count("【比亚迪云辇智能车身控制系统】") == 1
    assert "云辇" in note


def test_cross_domain_comparison_matrix():
    """Verify cross-domain comparisons are cleanly labelled without misattribution."""
    comparator = TechnologyComparator()

    matrix = comparator.compare(["云辇", "4680电池"])
    assert matrix.domain_chinese_name == "跨车企综合技术横评"
    assert len(matrix.compared_entities) == 2


def test_zeekr_haohan_ad_rivals():
    """Verify Zeekr Haohan Intelligent Driving entity and rival cross-brand mapping."""
    kg = AutomotiveKnowledgeGraph.get_instance()
    comparator = TechnologyComparator()

    z_ad = kg.resolver.get_entity("zeekr_haohan_ad")
    assert z_ad is not None
    assert z_ad.category == TechCategory.AUTONOMOUS_DRIVING

    rivals = comparator.get_equivalents("zeekr_haohan_ad")
    rival_ids = [r.id for r in rivals]
    assert "hima_ads" in rival_ids
    assert "xpeng_xngp" in rival_ids
    assert "tesla_fsd_hw4" in rival_ids


def test_extract_terms_and_sales_note_with_context_disambiguation():
    """Verify that ambiguous short terms (e.g. 800V) correctly disambiguate via context history."""
    kg = AutomotiveKnowledgeGraph.get_instance()

    # Ambiguous term '800V' with Huawei context
    terms_huawei = kg.extract_terms("800V充电速度怎么样？", context="我正在看问界M9")
    assert len(terms_huawei) == 1
    assert terms_huawei[0].entity.id == "hima_whale_800v"

    note_huawei = kg.generate_system_sales_note("800V充电速度怎么样？", context="我正在看问界M9")
    assert note_huawei is not None
    assert "华为巨鲸 800V 高压电池平台" in note_huawei

    # Ambiguous term '800V' with Xiaomi context
    terms_xiaomi = kg.extract_terms("800V充电速度怎么样？", context="我正在看小米SU7")
    assert len(terms_xiaomi) == 1
    assert terms_xiaomi[0].entity.id == "xiaomi_v800_sic"

    note_xiaomi = kg.generate_system_sales_note("800V充电速度怎么样？", context="我正在看小米SU7")
    assert note_xiaomi is not None
    assert "小米 800V 碳化硅高压平台 (V800架构)" in note_xiaomi


def test_sales_agent_no_false_positive_on_assistant_prior_turn(monkeypatch):
    """Verify SalesAgent does not falsely assert customer mentioned tech when only assistant previously did."""
    import json
    from unittest.mock import MagicMock

    from src.agent.sales_agent import SalesAgent
    from src.agent.schemas import AgentInput

    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"name": "Test"})
    mock_llm.complete.return_value = mock_resp

    captured_notes = []

    def mock_generate_response(*args, **kwargs):
        notes = kwargs.get("system_notes") or []
        captured_notes.extend(notes)
        return "推荐比亚迪汉EV，它搭载了云辇-C系统。"

    monkeypatch.setattr("src.agent.sales_agent.generate_response", mock_generate_response)

    agent = SalesAgent(llm=mock_llm)
    session_id = "test-fp-session"
    state = SessionState(session_id=session_id)

    # Turn 1: Customer asks general question, assistant replies mentioning 云辇-C
    agent.process(AgentInput(session_state=state, user_message="推荐20万左右的车"))

    # Turn 2: Customer asks non-tech question
    captured_notes.clear()
    agent.process(AgentInput(session_state=state, user_message="哪款更省电？"))

    # Assert that NO terminology note was generated for turn 2!
    for note in captured_notes:
        assert "专有名词解析与导购策略提示" not in note


def test_sales_agent_circuit_breaker_instance_isolation():
    """Verify different SalesAgent instances maintain isolated circuit breaker states."""
    from unittest.mock import MagicMock

    from src.agent.sales_agent import SalesAgent

    mock_llm = MagicMock()
    agent1 = SalesAgent(llm=mock_llm)
    agent2 = SalesAgent(llm=mock_llm)

    assert agent1.circuit_breaker is not agent2.circuit_breaker


