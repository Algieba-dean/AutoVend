"""
过滤模块单元测试

覆盖 label_registry, vehicle_db, filter_engine, query_parser, hybrid_pipeline
"""

import os
import tempfile

import pytest

from src.filter.filter_engine import FilterEngine
from src.filter.label_registry import LabelRegistry, LabelType
from src.filter.query_parser import QueryParser
from src.filter.vehicle_db import VehicleDB
from src.retrieval.hybrid_pipeline import HybridPipeline


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture(scope="module")
def registry():
    return LabelRegistry()


@pytest.fixture(scope="module")
def db(registry):
    """使用临时 db 文件，导入真实数据"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _db = VehicleDB(db_path=path, registry=registry)
    _db.import_from_toml_dir()
    yield _db
    _db.close()
    os.unlink(path)


@pytest.fixture(scope="module")
def engine(db, registry):
    return FilterEngine(db=db, registry=registry)


@pytest.fixture(scope="module")
def parser(registry):
    return QueryParser(registry=registry)


@pytest.fixture(scope="module")
def pipeline(registry, db, engine, parser):
    return HybridPipeline(
        registry=registry,
        db=db,
        filter_engine=engine,
        query_parser=parser,
    )


# ======================================================================
# LabelRegistry
# ======================================================================


class TestLabelRegistry:

    def test_load_labels(self, registry):
        assert len(registry.labels) > 40

    def test_label_types(self, registry):
        summary = registry.summary()
        assert summary["type_counts"]["range"] >= 10
        assert summary["type_counts"]["boolean"] >= 10
        assert summary["type_counts"]["enum"] >= 5

    def test_tree_expand_suv(self, registry):
        leaves = registry.expand_tree("suv")
        assert "compact suv" in leaves
        assert "mid-size suv" in leaves

    def test_tree_expand_european(self, registry):
        leaves = registry.expand_tree("european")
        assert "bmw" in leaves
        assert "mercedes-benz" in leaves

    def test_tree_expand_leaf(self, registry):
        leaves = registry.expand_tree("compact suv")
        assert leaves == ["compact suv"]

    def test_is_tree_value(self, registry):
        assert registry.is_tree_value("suv")
        assert registry.is_tree_value("compact suv")
        assert registry.is_tree_value("european")
        assert not registry.is_tree_value("xyznotexist")

    def test_get_tree_field(self, registry):
        assert registry.get_tree_field("suv") == "vehicle_category_bottom"
        assert registry.get_tree_field("bmw") == "brand"

    def test_range_label_alias(self, registry):
        label = registry.get_label("prize")
        assert label is not None
        assert label.label_type == LabelType.RANGE
        resolved = label.resolve_alias("cheap")
        assert "below" in resolved.lower() or "10,000" in resolved

    def test_range_gte(self, registry):
        label = registry.get_label("horsepower")
        vals = label.get_values_gte("300-400 hp")
        assert "300-400 hp" in vals
        assert "above 400 hp" in vals

    def test_range_lte(self, registry):
        label = registry.get_label("horsepower")
        vals = label.get_values_lte("200-300 hp")
        assert "100-200 hp" in vals
        assert "below 100 hp" in vals

    def test_get_all_db_columns(self, registry):
        cols = registry.get_all_db_columns()
        assert "brand" in cols
        assert "vehicle_category_bottom" in cols
        assert "prize" in cols

    def test_precise_and_ambiguous(self, registry):
        precise = registry.get_precise_labels()
        ambiguous = registry.get_ambiguous_labels()
        assert len(precise) > 0
        assert len(ambiguous) > 0
        assert "size" in ambiguous or "comfort_level" in ambiguous


# ======================================================================
# VehicleDB
# ======================================================================


class TestVehicleDB:

    def test_import_count(self, db):
        assert db.count() > 1000

    def test_distinct_brands(self, db):
        brands = db.get_distinct_values("brand")
        assert len(brands) >= 20
        assert "bmw" in brands or "toyota" in brands

    def test_distinct_categories(self, db):
        cats = db.get_distinct_values("vehicle_category_bottom")
        assert len(cats) >= 10
        assert "compact suv" in cats

    def test_query_basic(self, db):
        rows = db.query(
            ['"brand" = ?'],
            ["tesla"],
            limit=50,
        )
        assert len(rows) > 0
        for r in rows:
            assert r["brand"] == "tesla"

    def test_normalized_values(self, db):
        """确认范围值已规范化为 registry 格式"""
        rows = db.query(
            ['"horsepower" = ?'],
            ["100-200 hp"],
            limit=5,
        )
        assert len(rows) > 0


# ======================================================================
# FilterEngine
# ======================================================================


class TestFilterEngine:

    def test_tree_query_suv(self, engine):
        r = engine.filter({"vehicle_category_top": "suv"})
        assert r.total_candidates > 50

    def test_tree_query_brand_area(self, engine):
        r = engine.filter({"brand_area": "european"})
        assert r.total_candidates > 50

    def test_combo_chinese_suv(self, engine):
        r = engine.filter(
            {
                "vehicle_category_top": "suv",
                "brand_country": "china",
            }
        )
        assert r.total_candidates > 10

    def test_enum_exact(self, engine):
        r = engine.filter(
            {
                "powertrain_type": "battery electric vehicle",
            }
        )
        assert r.total_candidates > 100

    def test_range_between(self, engine):
        r = engine.filter(
            {
                "prize": {
                    "op": "between",
                    "min": "20,000 ~ 30,000",
                    "max": "40,000 ~ 60,000",
                },
            }
        )
        assert r.total_candidates > 10

    def test_range_gte(self, engine):
        r = engine.filter(
            {
                "horsepower": {"op": "gte", "value": "300-400 hp"},
            }
        )
        assert r.total_candidates > 10

    def test_degrade_on_no_result(self, engine):
        """极端条件触发降级"""
        r = engine.filter(
            {
                "brand": "bugatti",
                "prize": {"op": "lte", "value": "below 10,000"},
                "seat_layout": "7-seat",
                "size": "small",
            }
        )
        # 应该降级或返回空
        assert r.degrade_level >= 1

    def test_empty_query(self, engine):
        r = engine.filter({})
        assert r.total_candidates == 0
        assert r.degrade_level == 4


# ======================================================================
# QueryParser
# ======================================================================


class TestQueryParser:

    def test_chinese_price_range(self, parser):
        r = parser.parse("30到40万的SUV")
        assert "prize" in r.conditions
        assert r.conditions["prize"]["op"] == "between"

    def test_chinese_price_under(self, parser):
        r = parser.parse("20万以内的车")
        assert r.conditions["prize"]["op"] == "lte"

    def test_chinese_price_above(self, parser):
        r = parser.parse("50万以上的车")
        assert r.conditions["prize"]["op"] == "gte"

    def test_brand_chinese(self, parser):
        r = parser.parse("奔驰轿车")
        assert r.conditions.get("brand") == "mercedes-benz"

    def test_brand_english(self, parser):
        r = parser.parse("Tesla SUV")
        assert r.conditions.get("brand") == "tesla"

    def test_category_suv(self, parser):
        r = parser.parse("我想买SUV")
        assert r.conditions.get("vehicle_category_top") == "suv"

    def test_category_region(self, parser):
        r = parser.parse("日系车")
        assert r.conditions.get("brand_country") == "japan"

    def test_powertrain(self, parser):
        r = parser.parse("纯电动车")
        assert r.conditions.get("powertrain_type") == "battery electric vehicle"

    def test_seat_layout(self, parser):
        r = parser.parse("七座MPV")
        assert r.conditions.get("seat_layout") == "7-seat"
        assert r.conditions.get("vehicle_category_top") == "mpv"

    def test_drive_type(self, parser):
        r = parser.parse("四驱SUV")
        assert r.conditions.get("drive_type") == "all-wheel drive"

    def test_performance_alias(self, parser):
        r = parser.parse("省油的车")
        assert "fuel_consumption" in r.conditions

    def test_complex_query(self, parser):
        r = parser.parse("20万以内的国产纯电SUV，七座，四驱")
        assert "prize" in r.conditions
        assert r.conditions.get("brand_country") == "china"
        assert r.conditions.get("powertrain_type") == "battery electric vehicle"
        assert r.conditions.get("vehicle_category_top") == "suv"
        assert r.conditions.get("seat_layout") == "7-seat"
        assert r.conditions.get("drive_type") == "all-wheel drive"

    def test_matched_keywords(self, parser):
        r = parser.parse("比亚迪纯电SUV")
        assert len(r.matched_keywords) >= 3


# ======================================================================
# HybridPipeline (filter-only, no RAG)
# ======================================================================


class TestHybridPipeline:

    def test_filter_only(self, pipeline):
        r = pipeline.filter_only("30到40万的纯电SUV")
        assert len(r.car_models) > 5

    def test_get_candidates(self, pipeline):
        models = pipeline.get_candidates("Tesla electric SUV with AWD")
        assert len(models) > 0
        for m in models:
            assert "tesla" in m.lower() or "Tesla" in m

    def test_search_no_retriever(self, pipeline):
        r = pipeline.search("奔驰四驱轿车")
        assert r.candidate_count > 0
        assert r.rag_result_count == 0
        assert r.parse_method == "rule"

    def test_search_degrade_info(self, pipeline):
        r = pipeline.search("比亚迪 续航长 5座")
        assert r.degrade_level >= 0
        assert r.candidate_count > 0

    def test_search_metadata(self, pipeline):
        r = pipeline.search("省油的日系紧凑型suv")
        s = r.summary()
        assert "parsed_conditions" in s
        assert "candidate_count" in s
        assert s["candidate_count"] > 0


# ======================================================================
# Integration: parser → engine end-to-end
# ======================================================================


class TestIntegration:

    def test_parser_to_engine(self, parser, engine):
        """规则引擎解析后直接传入过滤引擎"""
        parsed = parser.parse("20万以内的国产七座MPV")
        result = engine.filter(parsed.conditions)
        assert result.total_candidates > 0
        # 结果应包含中国品牌的车
        for model in result.car_models[:5]:
            assert isinstance(model, str)
            assert len(model) > 0

    def test_multiple_queries_consistency(self, pipeline):
        """多次查询结果一致"""
        q = "奔驰四驱SUV"
        r1 = pipeline.filter_only(q)
        r2 = pipeline.filter_only(q)
        assert set(r1.car_models) == set(r2.car_models)
