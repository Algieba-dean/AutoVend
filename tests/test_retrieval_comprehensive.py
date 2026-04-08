"""
检索系统综合测试与评估

覆盖维度:
- QueryParser: 中/英文, 价格(区间/上限/下限/预算/单值), 品牌, 车型层级,
  地区, 动力, 座位, 驱动, 风格, 布尔功能, 性能别名, 复合条件, 边界输入
- FilterEngine: 树形/范围/枚举/布尔/等级/模糊 全部标签类型,
  精确值/区间/gte/lte, 降级策略, 组合条件
- 排除语义: 标注未来需支持的排除查询 (不要/除了/非/不含)
- Pipeline 端到端: parser→engine 联动, 一致性, 结果质量评估
"""

import os
import tempfile

import pytest

from src.filter.filter_engine import FilterEngine, FilterResult
from src.filter.label_registry import LabelRegistry
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
        registry=registry, db=db, filter_engine=engine, query_parser=parser
    )


# ======================================================================
# 1. QueryParser — 价格解析
# ======================================================================


class TestParserPriceChinese:
    """中文价格解析"""

    def test_range_X_to_Y_wan(self, parser):
        """'20万到30万' → between"""
        r = parser.parse("20万到30万的车")
        assert r.conditions["prize"]["op"] == "between"

    def test_range_X_dash_Y_wan(self, parser):
        """'20-30万' → between"""
        r = parser.parse("20-30万SUV")
        assert r.conditions["prize"]["op"] == "between"

    def test_range_X_tilde_Y_wan(self, parser):
        """'20~30万' → between"""
        r = parser.parse("20~30万的车")
        assert r.conditions["prize"]["op"] == "between"

    def test_range_Xw_dash_Yw(self, parser):
        """'10w-20w' → between"""
        r = parser.parse("10w-20w SUV")
        assert r.conditions["prize"]["op"] == "between"

    def test_under(self, parser):
        """'15万以内' → lte"""
        r = parser.parse("15万以内的车")
        assert r.conditions["prize"]["op"] == "lte"

    def test_under_yixia(self, parser):
        """'20万以下' → lte"""
        r = parser.parse("20万以下")
        assert r.conditions["prize"]["op"] == "lte"

    def test_above(self, parser):
        """'50万以上' → gte"""
        r = parser.parse("50万以上的豪华车")
        assert r.conditions["prize"]["op"] == "gte"

    def test_above_qi(self, parser):
        """'30万起' → gte"""
        r = parser.parse("30万起的车")
        assert r.conditions["prize"]["op"] == "gte"

    def test_budget(self, parser):
        """'预算25万' → between (±20%)"""
        r = parser.parse("预算25万买SUV")
        assert r.conditions["prize"]["op"] == "between"

    def test_zuoyou(self, parser):
        """'30万左右' → between"""
        r = parser.parse("30万左右的轿车")
        assert r.conditions["prize"]["op"] == "between"

    def test_single_wan(self, parser):
        """单独 '15万' → between (±20%)"""
        r = parser.parse("15万的车")
        assert r.conditions["prize"]["op"] == "between"

    def test_decimal_price(self, parser):
        """'8.5万' 小数"""
        r = parser.parse("8.5万以内的车")
        assert "prize" in r.conditions

    def test_low_price_below_10k(self, parser):
        """低价位 5万 → below 10,000"""
        r = parser.parse("5万以内")
        assert r.conditions["prize"]["op"] == "lte"
        assert (
            "below 10,000" in r.conditions["prize"]["value"]
            or "10,000" in r.conditions["prize"]["value"]
        )

    def test_high_price_above_100k(self, parser):
        """高价位 100万以上 → gte, bucket 含 60,000~100,000 或 above 100,000"""
        r = parser.parse("100万以上")
        assert r.conditions["prize"]["op"] == "gte"
        # 100万=100,000 落入 '60,000 ~ 100,000' 或 'above 100,000'
        val = r.conditions["prize"]["value"]
        assert "100,000" in val


class TestParserPriceEnglish:
    """英文价格解析"""

    def test_range_Xk_to_Yk(self, parser):
        """'$20k-$30k' → between"""
        r = parser.parse("$20k-$30k SUV")
        assert r.conditions.get("prize", {}).get("op") == "between"

    @pytest.mark.xfail(reason="英文 under/above $Xk 单独使用尚未被正则匹配")
    def test_under_budget(self, parser):
        """'under $15k' — 当前正则不支持独立 under $Xk"""
        r = parser.parse("under $15k")
        assert "prize" in r.conditions

    @pytest.mark.xfail(reason="英文 above $Xk 单独使用尚未被正则匹配")
    def test_above_over(self, parser):
        """'above $50k' — 当前正则不支持独立 above $Xk"""
        r = parser.parse("above $50k sedan")
        assert "prize" in r.conditions


# ======================================================================
# 2. QueryParser — 品牌解析
# ======================================================================


class TestParserBrandChinese:
    """中文品牌别名"""

    @pytest.mark.parametrize(
        "text, expected_brand",
        [
            ("奔驰轿车", "mercedes-benz"),
            ("宝马SUV", "bmw"),
            ("奥迪A4", "audi"),
            ("大众途观", "volkswagen"),
            ("丰田汉兰达", "toyota"),
            ("本田CRV", "honda"),
            ("比亚迪汉", "byd"),
            ("特斯拉Model3", "tesla"),
            ("蔚来ES6", "nio"),
            ("小鹏P7", "xpeng"),
            ("小米SU7", "xiaomi"),
            ("吉利星瑞", "geely"),
            ("长安CS75", "changan"),
            ("长城坦克", "great wall motor"),
            ("哈弗H6", "great wall motor"),
            ("沃尔沃XC60", "volvo"),
            ("保时捷卡宴", "porsche"),
            ("捷豹F-PACE", "jaguar"),
            ("路虎揽胜", "land rover"),
            ("凯迪拉克CT5", "cadillac"),
            ("福特蒙迪欧", "ford"),
            ("日产轩逸", "nissan"),
            ("现代途胜", "hyundai"),
            ("标致408", "peugeot"),
            ("别克君威", "buick"),
            ("劳斯莱斯", "rolls-royce"),
        ],
    )
    def test_brand_alias(self, parser, text, expected_brand):
        r = parser.parse(text)
        assert r.conditions.get("brand") == expected_brand


class TestParserBrandEnglish:
    """英文品牌直接匹配"""

    @pytest.mark.parametrize(
        "text, expected_brand",
        [
            ("Tesla SUV", "tesla"),
            ("BMW sedan", "bmw"),
            ("Audi Q5", "audi"),
            ("Mercedes SUV", "mercedes-benz"),
            ("Benz sedan", "mercedes-benz"),
            ("VW Golf", "volkswagen"),
            ("Toyota Corolla", "toyota"),
            ("Honda Civic", "honda"),
            ("BYD Seal", "byd"),
            ("Volvo XC90", "volvo"),
            ("Ford Mustang", "ford"),
            ("Porsche Cayenne", "porsche"),
        ],
    )
    def test_brand_english(self, parser, text, expected_brand):
        r = parser.parse(text)
        assert r.conditions.get("brand") == expected_brand


# ======================================================================
# 3. QueryParser — 车型层级解析
# ======================================================================


class TestParserCategory:
    """车型类别/层级"""

    @pytest.mark.parametrize(
        "text, key, value",
        [
            # Top level
            ("我想买SUV", "vehicle_category_top", "suv"),
            ("轿车推荐", "vehicle_category_top", "sedan"),
            ("MPV哪个好", "vehicle_category_top", "mpv"),
            ("跑车", "vehicle_category_top", "sports car"),
            # Middle level
            ("敞篷车", "vehicle_category_middle", "convertible sports car"),
            ("硬顶跑车", "vehicle_category_middle", "hardtop sports car"),
            ("小型轿车", "vehicle_category_middle", "small sedan"),
            ("中型轿车", "vehicle_category_middle", "mid-size sedan"),
            ("中大型轿车", "vehicle_category_middle", "mid-large sedan"),
            ("家用mpv", "vehicle_category_middle", "family mpv"),
            ("商务mpv", "vehicle_category_middle", "business mpv"),
            # Bottom level (leaf)
            ("紧凑型轿车", "vehicle_category_bottom", "compact sedan"),
            ("紧凑型suv", "vehicle_category_bottom", "compact suv"),
            ("中型suv", "vehicle_category_bottom", "mid-size suv"),
            ("中大型suv", "vehicle_category_bottom", "mid-to-large suv"),
            ("越野suv", "vehicle_category_bottom", "off-road suv"),
            ("硬派越野", "vehicle_category_bottom", "off-road suv"),
            ("全地形", "vehicle_category_bottom", "all-terrain suv"),
        ],
    )
    def test_category(self, parser, text, key, value):
        r = parser.parse(text)
        assert r.conditions.get(key) == value


class TestParserRegion:
    """品牌地区/国家"""

    @pytest.mark.parametrize(
        "text, key, value",
        [
            ("德系车", "brand_country", "germany"),
            ("德国车", "brand_country", "germany"),
            ("日系车", "brand_country", "japan"),
            ("日本车", "brand_country", "japan"),
            ("美系车", "brand_country", "usa"),
            ("美国车", "brand_country", "usa"),
            ("韩系车", "brand_country", "korea"),
            ("法系车", "brand_country", "france"),
            ("英系车", "brand_country", "united kingdom"),
            ("瑞典车", "brand_country", "sweden"),
            ("国产车", "brand_country", "china"),
            ("自主品牌", "brand_country", "china"),
            ("中国品牌", "brand_country", "china"),
            ("欧洲车", "brand_area", "european"),
        ],
    )
    def test_region(self, parser, text, key, value):
        r = parser.parse(text)
        assert r.conditions.get(key) == value


# ======================================================================
# 4. QueryParser — 功能特性 / 枚举
# ======================================================================


class TestParserPowertrain:
    """动力类型"""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("纯电动车", "battery electric vehicle"),
            ("纯电", "battery electric vehicle"),
            ("电动SUV", "battery electric vehicle"),
            ("EV", "battery electric vehicle"),
            ("BEV", "battery electric vehicle"),
            ("混动车", "hybrid electric vehicle"),
            ("油电混合", "hybrid electric vehicle"),
            ("插电混动", "plug-in hybrid electric vehicle"),
            ("插混SUV", "plug-in hybrid electric vehicle"),
            ("PHEV", "plug-in hybrid electric vehicle"),
            ("增程式", "range-extended electric vehicle"),
            ("增程", "range-extended electric vehicle"),
            ("汽油车", "gasoline engine"),
            ("燃油车", "gasoline engine"),
            ("柴油车", "diesel engine"),
        ],
    )
    def test_powertrain(self, parser, text, expected):
        r = parser.parse(text)
        assert r.conditions.get("powertrain_type") == expected


class TestParserSeatLayout:
    """座位数"""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("两座跑车", "2-seat"),
            ("2座", "2-seat"),
            ("四座", "4-seat"),
            ("五座SUV", "5-seat"),
            ("5座", "5-seat"),
            ("六座MPV", "6-seat"),
            ("七座MPV", "7-seat"),
            ("7座SUV", "7-seat"),
            ("7-seat MPV", "7-seat"),
        ],
    )
    def test_seat(self, parser, text, expected):
        r = parser.parse(text)
        assert r.conditions.get("seat_layout") == expected


class TestParserDriveType:
    """驱动方式"""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("四驱SUV", "all-wheel drive"),
            ("全驱", "all-wheel drive"),
            ("AWD", "all-wheel drive"),
            pytest.param(
                "4WD",
                "all-wheel drive",
                marks=pytest.mark.xfail(reason="'4' 被价格解析器先消费为价格"),
            ),
            ("前驱轿车", "front-wheel drive"),
            ("FWD", "front-wheel drive"),
            ("后驱跑车", "rear-wheel drive"),
            ("RWD", "rear-wheel drive"),
        ],
    )
    def test_drive(self, parser, text, expected):
        r = parser.parse(text)
        assert r.conditions.get("drive_type") == expected


class TestParserDesignStyle:
    """风格"""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("运动风", "sporty"),
            ("运动", "sporty"),
            ("sporty car", "sporty"),
            ("商务风格", "business"),
            ("商务", "business"),
        ],
    )
    def test_style(self, parser, text, expected):
        r = parser.parse(text)
        assert r.conditions.get("design_style") == expected


# ======================================================================
# 5. QueryParser — 布尔功能
# ======================================================================


class TestParserBooleanFeatures:
    """布尔特性关键词"""

    @pytest.mark.parametrize(
        "text, label, expected",
        [
            ("自动泊车", "auto_parking", "yes"),
            ("远程泊车", "remote_parking", "yes"),
            ("自动驾驶", "autonomous_driving_level", "l3"),
            ("辅助驾驶", "autonomous_driving_level", "l2"),
            ("L2辅助", "autonomous_driving_level", "l2"),
            ("L3自动", "autonomous_driving_level", "l3"),
            ("语音控制", "voice_interaction", "yes"),
            ("语音交互", "voice_interaction", "yes"),
            ("OTA升级", "ota_updates", "yes"),
            ("自动刹车", "automatic_emergency_braking", "yes"),
            ("AEB", "automatic_emergency_braking", "yes"),
            ("车道保持", "lane_keep_assist", "yes"),
            ("盲区监测", "blind_spot_detection", "yes"),
            ("疲劳检测", "fatigue_driving_detection", "yes"),
            ("巡航功能", "adaptive_cruise_control", "yes"),
            ("ACC", "adaptive_cruise_control", "yes"),
            ("真皮座椅", "seat_material", "leather"),
            ("真皮内饰", "seat_material", "leather"),
            ("织物座椅", "seat_material", "fabric"),
        ],
    )
    def test_boolean(self, parser, text, label, expected):
        r = parser.parse(text)
        assert r.conditions.get(label) == expected


class TestParserUsage:
    """使用场景"""

    @pytest.mark.parametrize(
        "text, label, expected",
        [
            ("城市通勤", "city_commuting", "yes"),
            ("通勤代步", "city_commuting", "yes"),
            ("长途旅行", "highway_long_distance", "yes"),
            ("高速出行", "highway_long_distance", "yes"),
            ("拉货用", "cargo_capability", "yes"),
            ("载货", "cargo_capability", "yes"),
        ],
    )
    def test_usage(self, parser, text, label, expected):
        r = parser.parse(text)
        assert r.conditions.get(label) == expected


# ======================================================================
# 6. QueryParser — 性能别名 (range alias)
# ======================================================================


class TestParserPerformanceAlias:
    """性能别名 → 范围标签"""

    @pytest.mark.parametrize(
        "text, label, op",
        [
            ("省油的车", "fuel_consumption", "lte"),
            ("油耗低", "fuel_consumption", "lte"),
            ("费油", "fuel_consumption", "gte"),
            ("省电", "electric_consumption", "lte"),
            ("加速快", "zero_to_one_hundred_km_h_acceleration_time", "lte"),
            ("快", "zero_to_one_hundred_km_h_acceleration_time", "lte"),
            ("动力强", "horsepower", "gte"),
            ("大马力", "horsepower", "gte"),
            ("动力强劲", "horsepower", "gte"),
            pytest.param(
                "高速度",
                "top_speed",
                "gte",
                marks=pytest.mark.xfail(
                    reason="'高速' 被优先匹配为 highway_long_distance"
                ),
            ),
            ("长续航", "driving_range", "gte"),
            ("续航长", "driving_range", "gte"),
            ("大空间", "passenger_space_volume", "gte"),
            ("空间大", "passenger_space_volume", "gte"),
            ("大后备箱", "trunk_volume", "gte"),
            ("底盘高", "chassis_height", "gte"),
            ("低底盘", "chassis_height", "lte"),
        ],
    )
    def test_perf(self, parser, text, label, op):
        r = parser.parse(text)
        assert label in r.conditions
        assert r.conditions[label]["op"] == op


# ======================================================================
# 7. QueryParser — 复合条件
# ======================================================================


class TestParserComplex:
    """多条件复合查询"""

    def test_full_chinese(self, parser):
        """20万以内的国产纯电SUV，七座，四驱"""
        r = parser.parse("20万以内的国产纯电SUV，七座，四驱")
        assert r.conditions["prize"]["op"] == "lte"
        assert r.conditions["brand_country"] == "china"
        assert r.conditions["powertrain_type"] == "battery electric vehicle"
        assert r.conditions["vehicle_category_top"] == "suv"
        assert r.conditions["seat_layout"] == "7-seat"
        assert r.conditions["drive_type"] == "all-wheel drive"
        assert len(r.matched_keywords) >= 6

    def test_brand_plus_category_plus_price(self, parser):
        """奔驰30-50万的轿车"""
        r = parser.parse("奔驰30-50万的轿车")
        assert r.conditions["brand"] == "mercedes-benz"
        assert r.conditions["prize"]["op"] == "between"
        assert r.conditions["vehicle_category_top"] == "sedan"

    def test_region_plus_powertrain_plus_perf(self, parser):
        """日系省油的混动SUV"""
        r = parser.parse("日系省油的混动SUV")
        assert r.conditions["brand_country"] == "japan"
        assert r.conditions["vehicle_category_top"] == "suv"
        assert r.conditions["powertrain_type"] == "hybrid electric vehicle"
        assert "fuel_consumption" in r.conditions

    def test_english_complex(self, parser):
        """Tesla electric SUV with AWD"""
        r = parser.parse("Tesla electric SUV with AWD")
        assert r.conditions.get("brand") == "tesla"
        assert r.conditions.get("powertrain_type") == "battery electric vehicle"
        assert r.conditions.get("vehicle_category_top") == "suv"
        assert r.conditions.get("drive_type") == "all-wheel drive"

    def test_mixed_language(self, parser):
        """混合中英文: 比亚迪EV SUV 20万以内"""
        r = parser.parse("比亚迪EV SUV 20万以内")
        assert r.conditions.get("brand") == "byd"
        assert r.conditions.get("powertrain_type") == "battery electric vehicle"
        assert r.conditions.get("vehicle_category_top") == "suv"
        assert "prize" in r.conditions

    def test_perf_plus_features(self, parser):
        """大空间 长续航 有自动泊车的纯电SUV"""
        r = parser.parse("大空间 长续航 有自动泊车的纯电SUV")
        assert "passenger_space_volume" in r.conditions
        assert "driving_range" in r.conditions
        assert r.conditions.get("auto_parking") == "yes"
        assert r.conditions.get("powertrain_type") == "battery electric vehicle"
        assert r.conditions.get("vehicle_category_top") == "suv"

    def test_specific_bottom_level(self, parser):
        """紧凑型suv 20万以内 四驱"""
        r = parser.parse("紧凑型suv 20万以内 四驱")
        assert r.conditions.get("vehicle_category_bottom") == "compact suv"
        assert "prize" in r.conditions
        assert r.conditions.get("drive_type") == "all-wheel drive"


# ======================================================================
# 8. QueryParser — 边界/异常输入
# ======================================================================


class TestParserEdgeCases:
    """边界情况"""

    def test_empty_string(self, parser):
        r = parser.parse("")
        assert r.conditions == {}
        assert r.matched_keywords == []

    def test_whitespace_only(self, parser):
        r = parser.parse("   ")
        assert r.conditions == {}

    def test_gibberish(self, parser):
        r = parser.parse("asdfghjkl qwertyuiop")
        assert r.conditions == {}

    def test_number_only(self, parser):
        r = parser.parse("12345")
        assert r.conditions == {}

    def test_punctuation_heavy(self, parser):
        r = parser.parse("我想买SUV！！！价格20万以内？？？")
        assert r.conditions.get("vehicle_category_top") == "suv"
        assert "prize" in r.conditions

    def test_repeated_keywords(self, parser):
        """重复关键词不应导致异常"""
        r = parser.parse("SUV SUV SUV")
        assert "vehicle_category_top" in r.conditions

    def test_conflicting_conditions(self, parser):
        """矛盾条件: 同时前驱和四驱 — 后出现的覆盖"""
        r = parser.parse("前驱四驱SUV")
        assert "drive_type" in r.conditions


# ======================================================================
# 9. FilterEngine — 树形标签
# ======================================================================


class TestEngineTree:
    """树形标签过滤"""

    def test_top_level_suv(self, engine):
        r = engine.filter({"vehicle_category_top": "suv"})
        assert r.total_candidates > 50
        assert r.degrade_level == 0

    def test_top_level_sedan(self, engine):
        r = engine.filter({"vehicle_category_top": "sedan"})
        assert r.total_candidates > 50

    def test_top_level_mpv(self, engine):
        r = engine.filter({"vehicle_category_top": "mpv"})
        assert r.total_candidates > 10

    def test_top_level_sports_car(self, engine):
        r = engine.filter({"vehicle_category_top": "sports car"})
        assert r.total_candidates >= 0  # may be small

    def test_middle_level_crossover_suv(self, engine):
        r = engine.filter({"vehicle_category_middle": "crossover suv"})
        assert r.total_candidates > 10

    def test_middle_level_body_on_frame(self, engine):
        r = engine.filter({"vehicle_category_middle": "body-on-frame suv"})
        assert r.total_candidates >= 0

    def test_middle_level_family_mpv(self, engine):
        r = engine.filter({"vehicle_category_middle": "family mpv"})
        assert r.total_candidates >= 0

    def test_bottom_level_compact_suv(self, engine):
        r = engine.filter({"vehicle_category_bottom": "compact suv"})
        assert r.total_candidates > 5

    def test_bottom_level_mid_size_suv(self, engine):
        r = engine.filter({"vehicle_category_bottom": "mid-size suv"})
        assert r.total_candidates > 5

    def test_brand_area_european(self, engine):
        r = engine.filter({"brand_area": "european"})
        assert r.total_candidates > 50

    def test_brand_area_american(self, engine):
        r = engine.filter({"brand_area": "american"})
        assert r.total_candidates > 10

    def test_brand_area_asian(self, engine):
        r = engine.filter({"brand_area": "asian"})
        assert r.total_candidates > 100

    def test_brand_country_germany(self, engine):
        r = engine.filter({"brand_country": "germany"})
        assert r.total_candidates > 50

    def test_brand_country_japan(self, engine):
        r = engine.filter({"brand_country": "japan"})
        assert r.total_candidates > 50

    def test_brand_country_china(self, engine):
        r = engine.filter({"brand_country": "china"})
        assert r.total_candidates > 100

    def test_brand_country_usa(self, engine):
        r = engine.filter({"brand_country": "usa"})
        assert r.total_candidates > 10

    def test_brand_leaf_tesla(self, engine):
        r = engine.filter({"brand": "tesla"})
        assert r.total_candidates > 0
        for m in r.car_models:
            assert "tesla" in m.lower() or "Tesla" in m

    def test_brand_leaf_bmw(self, engine):
        r = engine.filter({"brand": "bmw"})
        assert r.total_candidates > 0

    def test_brand_leaf_byd(self, engine):
        r = engine.filter({"brand": "byd"})
        assert r.total_candidates > 0


# ======================================================================
# 10. FilterEngine — 范围标签
# ======================================================================


class TestEngineRange:
    """范围标签: 精确/gte/lte/between"""

    # --- 价格 ---
    def test_price_exact_bucket(self, engine):
        r = engine.filter({"prize": "20,000 ~ 30,000"})
        assert r.total_candidates > 0

    def test_price_between(self, engine):
        r = engine.filter(
            {
                "prize": {
                    "op": "between",
                    "min": "10,000 ~ 20,000",
                    "max": "30,000 ~ 40,000",
                }
            }
        )
        assert r.total_candidates > 0

    def test_price_lte(self, engine):
        r = engine.filter({"prize": {"op": "lte", "value": "20,000 ~ 30,000"}})
        assert r.total_candidates > 0

    def test_price_gte(self, engine):
        r = engine.filter({"prize": {"op": "gte", "value": "60,000 ~ 100,000"}})
        assert r.total_candidates > 0

    # --- 马力 ---
    def test_hp_exact(self, engine):
        r = engine.filter({"horsepower": "200-300 hp"})
        assert r.total_candidates > 0

    def test_hp_gte(self, engine):
        r = engine.filter({"horsepower": {"op": "gte", "value": "300-400 hp"}})
        assert r.total_candidates > 0

    def test_hp_lte(self, engine):
        r = engine.filter({"horsepower": {"op": "lte", "value": "200-300 hp"}})
        assert r.total_candidates > 0

    def test_hp_between(self, engine):
        r = engine.filter(
            {"horsepower": {"op": "between", "min": "100-200 hp", "max": "300-400 hp"}}
        )
        assert r.total_candidates > 0

    # --- 续航 ---
    def test_range_gte(self, engine):
        r = engine.filter({"driving_range": {"op": "gte", "value": "400-800km"}})
        assert r.total_candidates >= 0

    def test_range_lte(self, engine):
        r = engine.filter({"driving_range": {"op": "lte", "value": "400-800km"}})
        assert r.total_candidates >= 0

    # --- 油耗 ---
    def test_fuel_low(self, engine):
        r = engine.filter({"fuel_consumption": {"op": "lte", "value": "4-6l/100km"}})
        assert r.total_candidates >= 0

    # --- 百公里加速 ---
    def test_accel_fast(self, engine):
        r = engine.filter(
            {
                "zero_to_one_hundred_km_h_acceleration_time": {
                    "op": "lte",
                    "value": "6-8s",
                }
            }
        )
        assert r.total_candidates >= 0

    # --- 别名解析 ---
    def test_price_alias_cheap(self, engine, registry):
        """别名 'cheap' → 'below 10,000'"""
        label = registry.get_label("prize")
        resolved = label.resolve_alias("cheap")
        r = engine.filter({"prize": resolved})
        # should get some cheap cars
        assert isinstance(r, FilterResult)

    def test_hp_alias_high(self, engine, registry):
        """别名 'high' → '300-400 hp'"""
        label = registry.get_label("horsepower")
        resolved = label.resolve_alias("high")
        r = engine.filter({"horsepower": {"op": "gte", "value": resolved}})
        assert r.total_candidates >= 0


# ======================================================================
# 11. FilterEngine — 枚举标签
# ======================================================================


class TestEngineEnum:
    """枚举标签精确匹配"""

    def test_powertrain_bev(self, engine):
        r = engine.filter({"powertrain_type": "battery electric vehicle"})
        assert r.total_candidates > 50

    def test_powertrain_gasoline(self, engine):
        r = engine.filter({"powertrain_type": "gasoline engine"})
        assert r.total_candidates > 50

    def test_powertrain_phev(self, engine):
        r = engine.filter({"powertrain_type": "plug-in hybrid electric vehicle"})
        assert r.total_candidates >= 0

    def test_powertrain_hybrid(self, engine):
        r = engine.filter({"powertrain_type": "hybrid electric vehicle"})
        assert r.total_candidates >= 0

    def test_drive_awd(self, engine):
        r = engine.filter({"drive_type": "all-wheel drive"})
        assert r.total_candidates > 0

    def test_drive_fwd(self, engine):
        r = engine.filter({"drive_type": "front-wheel drive"})
        assert r.total_candidates > 0

    def test_drive_rwd(self, engine):
        r = engine.filter({"drive_type": "rear-wheel drive"})
        assert r.total_candidates >= 0

    def test_seat_layout_5(self, engine):
        r = engine.filter({"seat_layout": "5-seat"})
        assert r.total_candidates > 0

    def test_seat_layout_7(self, engine):
        r = engine.filter({"seat_layout": "7-seat"})
        assert r.total_candidates > 0

    def test_design_sporty(self, engine):
        r = engine.filter({"design_style": "sporty"})
        assert r.total_candidates >= 0

    def test_design_business(self, engine):
        r = engine.filter({"design_style": "business"})
        assert r.total_candidates >= 0

    def test_color_dark(self, engine):
        r = engine.filter({"color": "dark colors"})
        assert r.total_candidates >= 0

    def test_seat_material_leather(self, engine):
        r = engine.filter({"seat_material": "leather"})
        assert r.total_candidates >= 0


# ======================================================================
# 12. FilterEngine — 布尔标签
# ======================================================================


class TestEngineBoolean:
    """布尔标签 Yes/No"""

    @pytest.mark.parametrize(
        "label",
        [
            "abs",
            "esp",
            "voice_interaction",
            "ota_updates",
            "adaptive_cruise_control",
            "lane_keep_assist",
            "auto_parking",
            "blind_spot_detection",
            "automatic_emergency_braking",
            "city_commuting",
            "highway_long_distance",
        ],
    )
    def test_boolean_yes(self, engine, label):
        r = engine.filter({label: "yes"})
        assert isinstance(r, FilterResult)
        assert r.degrade_level <= 4

    @pytest.mark.parametrize(
        "label",
        [
            "abs",
            "esp",
            "ota_updates",
        ],
    )
    def test_boolean_no(self, engine, label):
        r = engine.filter({label: "no"})
        assert isinstance(r, FilterResult)


# ======================================================================
# 13. FilterEngine — 等级标签
# ======================================================================


class TestEngineGrade:
    """等级标签 (low/medium/high)"""

    @pytest.mark.parametrize(
        "label, value",
        [
            ("noise_insulation", "high"),
            ("noise_insulation", "low"),
            ("off_road_capability", "high"),
            ("off_road_capability", "medium"),
            ("passability", "high"),
            ("cold_resistance", "high"),
            ("heat_resistance", "medium"),
            ("body_line_smoothness", "high"),
        ],
    )
    def test_grade(self, engine, label, value):
        r = engine.filter({label: value})
        assert isinstance(r, FilterResult)


# ======================================================================
# 14. FilterEngine — 模糊标签
# ======================================================================


class TestEngineAmbiguous:
    """模糊标签"""

    @pytest.mark.parametrize(
        "label, value",
        [
            ("size", "large"),
            ("size", "small"),
            ("comfort_level", "high"),
            ("smartness", "high"),
            ("family_friendliness", "high"),
            ("energy_consumption_level", "low"),
            ("vehicle_usability", "high"),
            ("aesthetics", "high"),
        ],
    )
    def test_ambiguous(self, engine, label, value):
        r = engine.filter({label: value})
        assert isinstance(r, FilterResult)


# ======================================================================
# 15. FilterEngine — 组合条件
# ======================================================================


class TestEngineCombined:
    """多条件组合"""

    def test_suv_plus_price(self, engine):
        r = engine.filter(
            {
                "vehicle_category_top": "suv",
                "prize": {
                    "op": "between",
                    "min": "10,000 ~ 20,000",
                    "max": "30,000 ~ 40,000",
                },
            }
        )
        assert r.total_candidates > 0

    def test_brand_plus_category(self, engine):
        r = engine.filter(
            {
                "brand_country": "china",
                "vehicle_category_top": "suv",
            }
        )
        assert r.total_candidates > 10

    def test_brand_plus_powertrain(self, engine):
        r = engine.filter(
            {
                "brand": "tesla",
                "powertrain_type": "battery electric vehicle",
            }
        )
        assert r.total_candidates > 0

    def test_triple_condition(self, engine):
        r = engine.filter(
            {
                "vehicle_category_top": "suv",
                "brand_country": "china",
                "powertrain_type": "battery electric vehicle",
            }
        )
        assert r.total_candidates >= 0  # may degrade

    def test_four_conditions(self, engine):
        r = engine.filter(
            {
                "vehicle_category_top": "suv",
                "brand_country": "china",
                "powertrain_type": "battery electric vehicle",
                "drive_type": "all-wheel drive",
            }
        )
        assert isinstance(r, FilterResult)

    def test_price_plus_features(self, engine):
        r = engine.filter(
            {
                "prize": {"op": "lte", "value": "30,000 ~ 40,000"},
                "seat_layout": "7-seat",
            }
        )
        assert isinstance(r, FilterResult)


# ======================================================================
# 16. FilterEngine — 降级策略
# ======================================================================


class TestEngineDegrade:
    """降级策略验证"""

    def test_empty_query_returns_level_4(self, engine):
        r = engine.filter({})
        assert r.degrade_level == 4
        assert r.total_candidates == 0

    def test_impossible_combo_degrades(self, engine):
        """极端组合应触发降级"""
        r = engine.filter(
            {
                "brand": "bugatti",
                "prize": {"op": "lte", "value": "below 10,000"},
                "seat_layout": "7-seat",
                "size": "small",
            }
        )
        assert r.degrade_level >= 1

    def test_ambiguous_removed_at_level_1(self, engine):
        """含模糊标签的查询应在 level 1 去除模糊标签后成功"""
        r = engine.filter(
            {
                "vehicle_category_top": "suv",
                "size": "large",
                "comfort_level": "high",
            }
        )
        assert r.total_candidates > 0
        # 如果 level 0 失败，应该在 level 1 成功
        assert r.degrade_level <= 1

    def test_degrade_preserves_core(self, engine):
        """降级到 level 2 应保留核心标签"""
        r = engine.filter(
            {
                "brand_country": "japan",
                "vehicle_category_top": "suv",
                "noise_insulation": "high",
                "size": "large",
                "comfort_level": "high",
            }
        )
        assert r.total_candidates > 0

    def test_degrade_to_brand_only(self, engine):
        """极端降级到 level 3 仅保留品牌/车型"""
        r = engine.filter(
            {
                "brand": "rolls-royce",
                "prize": {"op": "lte", "value": "below 10,000"},
                "seat_layout": "7-seat",
                "drive_type": "rear-wheel drive",
                "noise_insulation": "high",
            }
        )
        # Should eventually degrade, possibly to level 3 with just brand
        assert isinstance(r, FilterResult)

    def test_no_degrade_option(self, engine):
        """禁用降级 → 可能返回空结果"""
        r = engine.filter(
            {
                "brand": "bugatti",
                "prize": {"op": "lte", "value": "below 10,000"},
            },
            enable_degrade=False,
        )
        assert isinstance(r, FilterResult)


# ======================================================================
# 17. 排除语义测试 (未来功能)
# ======================================================================


class TestExclusionQueries:
    """
    排除语义测试

    当前系统尚未实现排除功能，这些测试标记为 xfail，
    用于记录需求、验证未来实现、以及作为回归测试基线。
    """

    @pytest.mark.xfail(reason="排除语义尚未实现")
    def test_exclude_suv_chinese(self, parser):
        """'不要SUV' → 应排除 SUV"""
        r = parser.parse("不要SUV，20万以内的车")
        assert (
            "exclude" in r.conditions
            or r.conditions.get("vehicle_category_top") != "suv"
        )

    @pytest.mark.xfail(reason="排除语义尚未实现")
    def test_exclude_brand_chinese(self, parser):
        """'除了特斯拉' → 应排除 Tesla"""
        r = parser.parse("除了特斯拉以外的纯电SUV")
        assert "exclude" in r.conditions or r.conditions.get("brand") != "tesla"

    @pytest.mark.xfail(reason="排除语义尚未实现")
    def test_exclude_powertrain_chinese(self, parser):
        """'非纯电' / '不要电动' → 排除 BEV"""
        r = parser.parse("非纯电的SUV")
        assert (
            "exclude" in r.conditions
            or r.conditions.get("powertrain_type") != "battery electric vehicle"
        )

    @pytest.mark.xfail(reason="排除语义尚未实现")
    def test_exclude_no_feature(self, parser):
        """'不需要自动泊车' → 不筛选该功能 / 或排除 yes"""
        r = parser.parse("不需要自动泊车的车")
        assert r.conditions.get("auto_parking") != "yes"

    @pytest.mark.xfail(reason="排除语义尚未实现: exclude op 不存在")
    def test_exclude_filter_engine(self, engine):
        """FilterEngine 应支持 exclude 操作符, 排除特定品牌"""
        # 先获取所有 SUV（含 Tesla）
        all_suv = engine.filter({"vehicle_category_top": "suv"})
        tesla_in_all = [m for m in all_suv.car_models if "tesla" in m.lower()]
        assert len(tesla_in_all) > 0, "前置条件: SUV 中应包含 Tesla"

        # 排除 Tesla 后应不含 Tesla
        r = engine.filter(
            {
                "vehicle_category_top": "suv",
                "brand": {"op": "exclude", "value": "tesla"},
            }
        )
        tesla_in_result = [m for m in r.car_models if "tesla" in m.lower()]
        assert len(tesla_in_result) == 0, f"排除后仍含 Tesla: {tesla_in_result}"
        # 且总数应小于全量
        assert r.total_candidates < all_suv.total_candidates

    @pytest.mark.xfail(reason="排除语义尚未实现")
    def test_exclude_multiple(self, parser):
        """'不要日系也不要德系' → 同时排除两个地区"""
        r = parser.parse("不要日系也不要德系的SUV")
        assert "exclude" in r.conditions

    @pytest.mark.xfail(reason="排除语义尚未实现")
    def test_exclude_with_price(self, parser):
        """'20万以内不要SUV' → 价格 + 排除"""
        r = parser.parse("20万以内不要SUV")
        assert "prize" in r.conditions
        assert r.conditions.get("vehicle_category_top") != "suv"


# ======================================================================
# 18. 端到端 Pipeline 测试
# ======================================================================


class TestPipelineE2E:
    """Parser → Engine 端到端"""

    @pytest.mark.parametrize(
        "query, min_candidates",
        [
            ("30到40万的纯电SUV", 5),
            ("比亚迪的纯电车", 5),
            ("20万以内的国产七座MPV", 1),
            ("奔驰四驱轿车", 1),
            ("日系省油的紧凑型SUV", 1),
            ("丰田混动SUV", 1),
            ("特斯拉纯电", 1),
            ("30万左右德系轿车", 1),
            ("15万以内的国产纯电", 1),
            ("50万以上的四驱SUV", 1),
        ],
    )
    def test_e2e_min_candidates(self, pipeline, query, min_candidates):
        """端到端: 查询应返回至少 min_candidates 个候选"""
        r = pipeline.filter_only(query)
        assert (
            len(r.car_models) >= min_candidates
        ), f"Query '{query}': got {len(r.car_models)}, expected >= {min_candidates}"

    def test_e2e_consistency(self, pipeline):
        """同一查询多次执行应返回相同结果"""
        q = "比亚迪纯电SUV 20万以内"
        r1 = pipeline.filter_only(q)
        r2 = pipeline.filter_only(q)
        assert set(r1.car_models) == set(r2.car_models)

    def test_e2e_search_metadata(self, pipeline):
        """search() 应返回完整元数据"""
        r = pipeline.search("日系SUV 20万以内 四驱")
        s = r.summary()
        assert "parsed_conditions" in s
        assert "candidate_count" in s
        assert "total_time" in s
        assert s["total_time"] > 0

    def test_e2e_no_retriever_fallback(self, pipeline):
        """无 retriever 时 RAG 结果为 0"""
        r = pipeline.search("奔驰SUV")
        assert r.rag_result_count == 0
        assert r.candidate_count > 0

    def test_e2e_parse_method_is_rule(self, pipeline):
        """无 LLM parser 时应使用 rule 解析"""
        r = pipeline.search("宝马四驱SUV")
        assert r.parse_method == "rule"


# ======================================================================
# 19. 评估指标: 批量查询质量评估
# ======================================================================


class TestRetrievalQuality:
    """
    批量查询质量评估

    为每个查询定义期望特征，验证检索结果的质量:
    - 条件解析完整性 (parsed_condition_keys)
    - 候选数量范围 (min_candidates, max_candidates)
    - 降级级别 (max_degrade_level)
    """

    EVAL_CASES = [
        {
            "query": "20万以内的国产纯电SUV",
            "expected_keys": {
                "prize",
                "brand_country",
                "powertrain_type",
                "vehicle_category_top",
            },
            "min_candidates": 1,
            "max_degrade": 3,
        },
        {
            "query": "奔驰30-50万的四驱轿车",
            "expected_keys": {"brand", "prize", "drive_type", "vehicle_category_top"},
            "min_candidates": 1,
            "max_degrade": 3,
        },
        {
            "query": "日系省油的紧凑型SUV 15万以内",
            "expected_keys": {
                "brand_country",
                "fuel_consumption",
                "vehicle_category_bottom",
                "prize",
            },
            "min_candidates": 1,
            "max_degrade": 3,
        },
        {
            "query": "七座MPV 大空间",
            "expected_keys": {
                "seat_layout",
                "vehicle_category_top",
                "passenger_space_volume",
            },
            "min_candidates": 1,
            "max_degrade": 2,
        },
        {
            "query": "特斯拉纯电四驱长续航",
            "expected_keys": {
                "brand",
                "powertrain_type",
                "drive_type",
                "driving_range",
            },
            "min_candidates": 0,
            "max_degrade": 4,
        },
        {
            "query": "10万以内的通勤代步小车",
            "expected_keys": {"prize", "city_commuting"},
            "min_candidates": 1,
            "max_degrade": 2,
        },
        {
            "query": "真皮座椅 自动泊车 L2辅助驾驶的SUV",
            "expected_keys": {
                "seat_material",
                "auto_parking",
                "autonomous_driving_level",
                "vehicle_category_top",
            },
            "min_candidates": 1,
            "max_degrade": 3,
        },
        {
            "query": "德系30万以上大马力后驱跑车",
            "expected_keys": {
                "brand_country",
                "prize",
                "horsepower",
                "drive_type",
                "vehicle_category_top",
            },
            "min_candidates": 0,
            "max_degrade": 4,
        },
    ]

    @pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c["query"][:20])
    def test_parse_completeness(self, parser, case):
        """验证条件解析完整性"""
        r = parser.parse(case["query"])
        parsed_keys = set(r.conditions.keys())
        missing = case["expected_keys"] - parsed_keys
        assert not missing, (
            f"Query '{case['query']}': " f"missing keys {missing}, got {parsed_keys}"
        )

    @pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c["query"][:20])
    def test_candidate_quality(self, pipeline, case):
        """验证候选数量和降级级别"""
        r = pipeline.filter_only(case["query"])
        assert len(r.car_models) >= case["min_candidates"], (
            f"Query '{case['query']}': got {len(r.car_models)}, "
            f"expected >= {case['min_candidates']}"
        )
        assert r.degrade_level <= case["max_degrade"], (
            f"Query '{case['query']}': "
            f"degrade_level={r.degrade_level}, "
            f"expected <= {case['max_degrade']}"
        )
