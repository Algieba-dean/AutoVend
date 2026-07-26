"""
Golden set for retrieval evaluation.

**Independence is the whole point.** Ground truth for each query is a SQL
predicate over `vehicles.db`, written by hand from what the query *means* — it
never consults `QueryParser` or `FilterEngine`. If the parser mis-reads
"德系车" as a brand it doesn't know, relevance is unaffected and recall drops,
which is exactly the signal we want. Deriving ground truth from the system
under test would make every metric self-congratulatory.

Consequences of that choice, worth knowing before reading the numbers:

- A query whose ground truth is large (e.g. "SUV" -> 800 cars) will show high
  recall@3 trivially. Specs therefore skew toward narrow, discriminative
  predicates; the `broad` tag marks the deliberately wide ones.
- Some specs encode knowledge the current parser provably lacks (German brands,
  "affordable"). They are included on purpose — they are the headroom.

Values in the predicates are lowercase because `VehicleDB._normalize_value`
lowercases on import.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.config import PROJECT_ROOT

GOLDEN_SET_PATH = PROJECT_ROOT / "evaluation" / "golden_set.jsonl"


@dataclass(frozen=True)
class QuerySpec:
    """One evaluation query plus its hand-written ground-truth predicate."""

    id: str
    query: str
    where: str
    tags: List[str] = field(default_factory=list)
    note: str = ""


# ── Single-constraint: category ───────────────────────────────────────
_CATEGORY = [
    QuerySpec("cat01", "Compact SUV", "vehicle_category_bottom = 'compact suv'", ["category"]),
    QuerySpec("cat02", "Mid-Size SUV", "vehicle_category_bottom = 'mid-size suv'", ["category"]),
    QuerySpec(
        "cat03", "Mid-to-Large SUV", "vehicle_category_bottom = 'mid-to-large suv'", ["category"]
    ),
    QuerySpec("cat04", "Off-road SUV", "vehicle_category_bottom = 'off-road suv'", ["category"]),
    QuerySpec(
        "cat05", "D-Segment Sedan", "vehicle_category_bottom = 'd-segment sedan'", ["category"]
    ),
    QuerySpec("cat06", "Compact Sedan", "vehicle_category_bottom = 'compact sedan'", ["category"]),
    QuerySpec(
        "cat07", "B-Segment Sedan", "vehicle_category_bottom = 'b-segment sedan'", ["category"]
    ),
    QuerySpec("cat08", "Large MPV", "vehicle_category_bottom = 'large mpv'", ["category"]),
    QuerySpec("cat09", "Compact MPV", "vehicle_category_bottom = 'compact mpv'", ["category"]),
    QuerySpec("cat10", "Micro Sedan", "vehicle_category_bottom = 'micro sedan'", ["category"]),
    QuerySpec(
        "cat11",
        "Two-door Hardtop Sports Car",
        "vehicle_category_bottom = 'two-door hardtop sports car'",
        ["category"],
    ),
    QuerySpec(
        "cat12",
        "SUV",
        "vehicle_category_bottom LIKE '%suv%'",
        ["category", "broad"],
        "Tree-node query: every SUV sub-type should qualify.",
    ),
    QuerySpec(
        "cat13",
        "sedan",
        "vehicle_category_bottom LIKE '%sedan%'",
        ["category", "broad"],
    ),
    QuerySpec(
        "cat14",
        "MPV",
        "vehicle_category_bottom LIKE '%mpv%'",
        ["category", "broad"],
    ),
    QuerySpec(
        "cat15",
        "sports car",
        "vehicle_category_bottom LIKE '%sports car%' OR vehicle_category_bottom LIKE '%sprots car%'",
        ["category", "broad"],
        "Source data contains the typo 'sprots car'; ground truth accepts both.",
    ),
    QuerySpec(
        "cat16",
        "pickup truck",
        "vehicle_category_bottom LIKE '%pickup%'",
        ["category", "rare"],
    ),
]

# ── Single-constraint: brand ──────────────────────────────────────────
_BRAND = [
    QuerySpec("brd01", "Toyota", "brand = 'toyota'", ["brand"]),
    QuerySpec("brd02", "BMW", "brand = 'bmw'", ["brand"]),
    QuerySpec("brd03", "Mercedes-Benz", "brand = 'mercedes-benz'", ["brand"]),
    QuerySpec("brd04", "Audi", "brand = 'audi'", ["brand"]),
    QuerySpec("brd05", "Tesla", "brand = 'tesla'", ["brand"]),
    QuerySpec("brd06", "NIO", "brand = 'nio'", ["brand"]),
    QuerySpec("brd07", "BYD", "brand = 'byd'", ["brand"]),
    QuerySpec("brd08", "Porsche", "brand = 'porsche'", ["brand"]),
    QuerySpec("brd09", "Volvo", "brand = 'volvo'", ["brand"]),
    QuerySpec("brd10", "Land Rover", "brand = 'land rover'", ["brand"]),
    QuerySpec("brd11", "Rolls-Royce", "brand = 'rolls-royce'", ["brand", "rare"]),
    QuerySpec("brd12", "XPeng", "brand = 'xpeng'", ["brand"]),
    QuerySpec(
        "brd13",
        "German car",
        "brand IN ('audi', 'bmw', 'mercedes-benz', 'porsche', 'volkswagen', 'bentley', 'bugatti')",
        ["brand", "world-knowledge", "known-gap"],
        "Requires country-of-origin knowledge the label vocabulary does not encode.",
    ),
    QuerySpec(
        "brd14",
        "Japanese car",
        "brand IN ('toyota', 'honda', 'nissan', 'mazda', 'suzuki')",
        ["brand", "world-knowledge", "known-gap"],
    ),
    QuerySpec(
        "brd15",
        "Chinese brand",
        "brand IN ('byd', 'geely', 'nio', 'xpeng', 'changan', 'great wall motor', 'gwm')",
        ["brand", "world-knowledge", "known-gap"],
    ),
    QuerySpec(
        "brd16",
        "American car",
        "brand IN ('ford', 'chevrolet', 'buick', 'cadillac', 'tesla')",
        ["brand", "world-knowledge", "known-gap"],
    ),
]

# ── Single-constraint: powertrain ─────────────────────────────────────
_POWERTRAIN = [
    QuerySpec(
        "pwr01",
        "Battery Electric Vehicle",
        "powertrain_type = 'battery electric vehicle'",
        ["powertrain"],
    ),
    QuerySpec(
        "pwr02", "Gasoline Engine", "powertrain_type = 'gasoline engine'", ["powertrain", "broad"]
    ),
    QuerySpec(
        "pwr03",
        "Hybrid Electric Vehicle",
        "powertrain_type = 'hybrid electric vehicle'",
        ["powertrain"],
    ),
    QuerySpec(
        "pwr04",
        "Plug-in Hybrid Electric Vehicle",
        "powertrain_type = 'plug-in hybird electric vehicle'",
        ["powertrain"],
        "Source data misspells 'hybrid' as 'hybird'.",
    ),
    QuerySpec(
        "pwr05", "Diesel Engine", "powertrain_type = 'diesel engine'", ["powertrain", "rare"]
    ),
    QuerySpec(
        "pwr06",
        "electric car",
        "powertrain_type = 'battery electric vehicle'",
        ["powertrain", "paraphrase"],
        "Colloquial phrasing of the label value.",
    ),
    QuerySpec(
        "pwr07",
        "纯电动车",
        "powertrain_type = 'battery electric vehicle'",
        ["powertrain", "zh"],
    ),
    QuerySpec(
        "pwr08",
        "混动车",
        "powertrain_type IN ('hybrid electric vehicle', 'plug-in hybird electric vehicle')",
        ["powertrain", "zh"],
    ),
]

# ── Single-constraint: price ──────────────────────────────────────────
_PRICE = [
    QuerySpec("prc01", "below 10,000", "prize = 'below 10,000'", ["price", "rare"]),
    QuerySpec("prc02", "10,000~20,000", "prize = '10,000 ~ 20,000'", ["price"]),
    QuerySpec("prc03", "20,000~30,000", "prize = '20,000 ~ 30,000'", ["price"]),
    QuerySpec("prc04", "30,000~40,000", "prize = '30,000 ~ 40,000'", ["price"]),
    QuerySpec("prc05", "40,000~60,000", "prize = '40,000 ~ 60,000'", ["price", "broad"]),
    QuerySpec("prc06", "above 100,000", "prize = 'above 100,000'", ["price"]),
    QuerySpec(
        "prc07",
        "affordable car",
        "prize IN ('below 10,000', '10,000 ~ 20,000', '20,000 ~ 30,000')",
        ["price", "paraphrase", "known-gap"],
        "Subjective term with no direct label value.",
    ),
    QuerySpec(
        "prc08",
        "luxury car",
        "prize IN ('above 100,000', '60,000 ~ 100,000')",
        ["price", "paraphrase", "known-gap"],
    ),
    QuerySpec(
        "prc09",
        "budget under 30,000",
        "prize IN ('below 10,000', '10,000 ~ 20,000', '20,000 ~ 30,000')",
        ["price", "range"],
    ),
    QuerySpec(
        "prc10",
        "预算20万到30万",
        "prize = '20,000 ~ 30,000'",
        ["price", "zh"],
    ),
]

# ── Single-constraint: other structured labels ────────────────────────
_STRUCTURED = [
    QuerySpec("str01", "7-seat", "seat_layout = '7-seat'", ["seat_layout"]),
    QuerySpec("str02", "5-seat", "seat_layout = '5-seat'", ["seat_layout", "broad"]),
    QuerySpec("str03", "2-seat", "seat_layout = '2-seat'", ["seat_layout"]),
    QuerySpec("str04", "4-seat", "seat_layout = '4-seat'", ["seat_layout"]),
    QuerySpec(
        "str05", "All-Wheel Drive", "drive_type = 'all-wheel drive'", ["drive_type", "broad"]
    ),
    QuerySpec("str06", "Rear-Wheel Drive", "drive_type = 'rear-wheel drive'", ["drive_type"]),
    QuerySpec(
        "str07",
        "Front-Wheel Drive",
        "drive_type IN ('front-wheel drive', 'font-wheel drive')",
        ["drive_type"],
        "Source data misspells 'front' as 'font' for most rows.",
    ),
    QuerySpec("str08", "sporty design", "design_style = 'sporty'", ["design_style", "broad"]),
    QuerySpec("str09", "business style", "design_style = 'business'", ["design_style", "broad"]),
    QuerySpec(
        "str10", "L3 autonomous driving", "autonomous_driving_level = 'l3'", ["adas", "rare"]
    ),
    QuerySpec(
        "str11",
        "driving range above 800km",
        "driving_range IN ('above 800km', '800~1000km')",
        ["range"],
    ),
    QuerySpec("str12", "driving range 300-400km", "driving_range = '300-400km'", ["range"]),
]

# ── Single-constraint: ambiguous / derived labels ─────────────────────
_AMBIGUOUS = [
    QuerySpec("amb01", "large size vehicle", "size = 'large'", ["ambiguous", "broad"]),
    QuerySpec("amb02", "small car", "size = 'small'", ["ambiguous"]),
    QuerySpec(
        "amb03", "family friendly car", "family_friendliness = 'high'", ["ambiguous", "broad"]
    ),
    QuerySpec("amb04", "high comfort", "comfort_level = 'high'", ["ambiguous", "broad"]),
    QuerySpec("amb05", "smart car", "smartness = 'high'", ["ambiguous", "broad"]),
    QuerySpec(
        "amb06",
        "energy efficient",
        "energy_consumption_level = 'low'",
        ["ambiguous", "paraphrase"],
    ),
    QuerySpec(
        "amb07",
        "strong off-road capability",
        "off_road_capability = 'high'",
        ["ambiguous"],
    ),
    QuerySpec("amb08", "家用车", "family_friendliness = 'high'", ["ambiguous", "zh", "broad"]),
    QuerySpec("amb09", "省油的车", "energy_consumption_level = 'low'", ["ambiguous", "zh"]),
    QuerySpec("amb10", "舒适的车", "comfort_level = 'high'", ["ambiguous", "zh", "broad"]),
]

# ── Two-constraint combinations ───────────────────────────────────────
_COMBO2 = [
    QuerySpec(
        "cmb01",
        "Mid-Size SUV Battery Electric Vehicle",
        "vehicle_category_bottom = 'mid-size suv' AND powertrain_type = 'battery electric vehicle'",
        ["category", "powertrain", "combo"],
    ),
    QuerySpec(
        "cmb02",
        "Compact SUV Gasoline Engine",
        "vehicle_category_bottom = 'compact suv' AND powertrain_type = 'gasoline engine'",
        ["category", "powertrain", "combo"],
    ),
    QuerySpec(
        "cmb03",
        "BMW sedan",
        "brand = 'bmw' AND vehicle_category_bottom LIKE '%sedan%'",
        ["brand", "category", "combo"],
    ),
    QuerySpec(
        "cmb04",
        "Toyota SUV",
        "brand = 'toyota' AND vehicle_category_bottom LIKE '%suv%'",
        ["brand", "category", "combo"],
    ),
    QuerySpec(
        "cmb05",
        "Audi Battery Electric Vehicle",
        "brand = 'audi' AND powertrain_type = 'battery electric vehicle'",
        ["brand", "powertrain", "combo"],
    ),
    QuerySpec(
        "cmb06",
        "Tesla SUV",
        "brand = 'tesla' AND vehicle_category_bottom LIKE '%suv%'",
        ["brand", "category", "combo"],
    ),
    QuerySpec(
        "cmb07",
        "7-seat MPV",
        "seat_layout = '7-seat' AND vehicle_category_bottom LIKE '%mpv%'",
        ["seat_layout", "category", "combo"],
    ),
    QuerySpec(
        "cmb08",
        "Mid-Size SUV 40,000~60,000",
        "vehicle_category_bottom = 'mid-size suv' AND prize = '40,000 ~ 60,000'",
        ["category", "price", "combo"],
    ),
    QuerySpec(
        "cmb09",
        "Compact SUV 20,000~30,000",
        "vehicle_category_bottom = 'compact suv' AND prize = '20,000 ~ 30,000'",
        ["category", "price", "combo"],
    ),
    QuerySpec(
        "cmb10",
        "Battery Electric Vehicle above 100,000",
        "powertrain_type = 'battery electric vehicle' AND prize = 'above 100,000'",
        ["powertrain", "price", "combo"],
    ),
    QuerySpec(
        "cmb11",
        "NIO Battery Electric Vehicle",
        "brand = 'nio' AND powertrain_type = 'battery electric vehicle'",
        ["brand", "powertrain", "combo"],
    ),
    QuerySpec(
        "cmb12",
        "Off-road SUV All-Wheel Drive",
        "vehicle_category_bottom = 'off-road suv' AND drive_type = 'all-wheel drive'",
        ["category", "drive_type", "combo"],
    ),
    QuerySpec(
        "cmb13",
        "sporty Two-door Hardtop Sports Car",
        "design_style = 'sporty' AND vehicle_category_bottom = 'two-door hardtop sports car'",
        ["design_style", "category", "combo"],
    ),
    QuerySpec(
        "cmb14",
        "family friendly 7-seat",
        "family_friendliness = 'high' AND seat_layout = '7-seat'",
        ["ambiguous", "seat_layout", "combo"],
    ),
    QuerySpec(
        "cmb15",
        "Porsche sports car",
        "brand = 'porsche' AND (vehicle_category_bottom LIKE '%sports car%' "
        "OR vehicle_category_bottom LIKE '%sprots car%')",
        ["brand", "category", "combo"],
    ),
    QuerySpec(
        "cmb16",
        "BYD Battery Electric Vehicle",
        "brand = 'byd' AND powertrain_type = 'battery electric vehicle'",
        ["brand", "powertrain", "combo"],
    ),
    QuerySpec(
        "cmb17",
        "中型SUV 纯电",
        "vehicle_category_bottom = 'mid-size suv' AND powertrain_type = 'battery electric vehicle'",
        ["category", "powertrain", "combo", "zh"],
    ),
    QuerySpec(
        "cmb18",
        "宝马 轿车",
        "brand = 'bmw' AND vehicle_category_bottom LIKE '%sedan%'",
        ["brand", "category", "combo", "zh"],
    ),
    QuerySpec(
        "cmb19",
        "7座 家用车",
        "seat_layout = '7-seat' AND family_friendliness = 'high'",
        ["seat_layout", "ambiguous", "combo", "zh"],
    ),
    QuerySpec(
        "cmb20",
        "Volvo SUV",
        "brand = 'volvo' AND vehicle_category_bottom LIKE '%suv%'",
        ["brand", "category", "combo"],
    ),
]

# ── Three-constraint combinations ─────────────────────────────────────
_COMBO3 = [
    QuerySpec(
        "cmb21",
        "Mid-Size SUV Battery Electric Vehicle 40,000~60,000",
        "vehicle_category_bottom = 'mid-size suv' "
        "AND powertrain_type = 'battery electric vehicle' AND prize = '40,000 ~ 60,000'",
        ["category", "powertrain", "price", "combo3"],
    ),
    QuerySpec(
        "cmb22",
        "Toyota SUV Hybrid Electric Vehicle",
        "brand = 'toyota' AND vehicle_category_bottom LIKE '%suv%' "
        "AND powertrain_type = 'hybrid electric vehicle'",
        ["brand", "category", "powertrain", "combo3"],
    ),
    QuerySpec(
        "cmb23",
        "Compact SUV Gasoline Engine 20,000~30,000",
        "vehicle_category_bottom = 'compact suv' AND powertrain_type = 'gasoline engine' "
        "AND prize = '20,000 ~ 30,000'",
        ["category", "powertrain", "price", "combo3"],
    ),
    QuerySpec(
        "cmb24",
        "BMW SUV All-Wheel Drive",
        "brand = 'bmw' AND vehicle_category_bottom LIKE '%suv%' AND drive_type = 'all-wheel drive'",
        ["brand", "category", "drive_type", "combo3"],
    ),
    QuerySpec(
        "cmb25",
        "large MPV 7-seat family friendly",
        "vehicle_category_bottom = 'large mpv' AND seat_layout = '7-seat' "
        "AND family_friendliness = 'high'",
        ["category", "seat_layout", "ambiguous", "combo3"],
    ),
    QuerySpec(
        "cmb26",
        "Mercedes-Benz sedan above 100,000",
        "brand = 'mercedes-benz' AND vehicle_category_bottom LIKE '%sedan%' "
        "AND prize = 'above 100,000'",
        ["brand", "category", "price", "combo3"],
    ),
    QuerySpec(
        "cmb27",
        "Battery Electric Vehicle SUV driving range above 800km",
        "powertrain_type = 'battery electric vehicle' AND vehicle_category_bottom LIKE '%suv%' "
        "AND driving_range IN ('above 800km', '800~1000km')",
        ["powertrain", "category", "range", "combo3"],
    ),
    QuerySpec(
        "cmb28",
        "Audi sedan sporty",
        "brand = 'audi' AND vehicle_category_bottom LIKE '%sedan%' AND design_style = 'sporty'",
        ["brand", "category", "design_style", "combo3"],
    ),
    QuerySpec(
        "cmb29",
        "off-road SUV high off-road capability All-Wheel Drive",
        "vehicle_category_bottom = 'off-road suv' AND off_road_capability = 'high' "
        "AND drive_type = 'all-wheel drive'",
        ["category", "ambiguous", "drive_type", "combo3"],
    ),
    QuerySpec(
        "cmb30",
        "30万预算的中型纯电SUV",
        "vehicle_category_bottom = 'mid-size suv' "
        "AND powertrain_type = 'battery electric vehicle' AND prize = '30,000 ~ 40,000'",
        ["category", "powertrain", "price", "combo3", "zh"],
    ),
]

# ── Natural-language phrasings ────────────────────────────────────────
_NATURAL = [
    QuerySpec(
        "nat01",
        "I need a family car with three rows of seats",
        "seat_layout IN ('7-seat', '8-seat') AND family_friendliness = 'high'",
        ["natural", "seat_layout"],
    ),
    QuerySpec(
        "nat02",
        "Looking for an electric SUV for city commuting",
        "powertrain_type = 'battery electric vehicle' AND vehicle_category_bottom LIKE '%suv%' "
        "AND city_commuting = 'yes'",
        ["natural", "powertrain", "category"],
    ),
    QuerySpec(
        "nat03",
        "a cheap small car for a first-time driver",
        "size = 'small' AND prize IN ('below 10,000', '10,000 ~ 20,000', '20,000 ~ 30,000')",
        ["natural", "price", "ambiguous", "known-gap"],
    ),
    QuerySpec(
        "nat04",
        "something fast and sporty",
        "design_style = 'sporty' AND (vehicle_category_bottom LIKE '%sports car%' "
        "OR vehicle_category_bottom LIKE '%sprots car%')",
        ["natural", "design_style", "category"],
    ),
    QuerySpec(
        "nat05",
        "long range electric car for road trips",
        "powertrain_type = 'battery electric vehicle' "
        "AND driving_range IN ('above 800km', '800~1000km') AND highway_long_distance = 'yes'",
        ["natural", "powertrain", "range"],
    ),
    QuerySpec(
        "nat06",
        "我需要一台适合家庭的七座车",
        "seat_layout = '7-seat' AND family_friendliness = 'high'",
        ["natural", "zh", "seat_layout"],
    ),
    QuerySpec(
        "nat07",
        "想买一台城市代步的小型电动车",
        "powertrain_type = 'battery electric vehicle' AND size = 'small' "
        "AND city_commuting = 'yes'",
        ["natural", "zh", "powertrain"],
    ),
    QuerySpec(
        "nat08",
        "预算不多，找一台经济实惠的紧凑型SUV",
        "vehicle_category_bottom = 'compact suv' "
        "AND prize IN ('below 10,000', '10,000 ~ 20,000', '20,000 ~ 30,000')",
        ["natural", "zh", "price", "known-gap"],
    ),
    QuerySpec(
        "nat09",
        "喜欢越野，要四驱的硬派SUV",
        "vehicle_category_bottom IN ('off-road suv', 'all-terrain suv') "
        "AND drive_type = 'all-wheel drive'",
        ["natural", "zh", "category", "drive_type"],
    ),
    QuerySpec(
        "nat10",
        "高端豪华行政轿车",
        "vehicle_category_bottom LIKE '%sedan%' AND prize = 'above 100,000' "
        "AND comfort_level = 'high'",
        ["natural", "zh", "price", "known-gap"],
    ),
    QuerySpec(
        "nat11",
        "a luxury German SUV",
        "brand IN ('audi', 'bmw', 'mercedes-benz', 'porsche', 'volkswagen', 'bentley') "
        "AND vehicle_category_bottom LIKE '%suv%' AND prize IN ('above 100,000', '60,000 ~ 100,000')",
        ["natural", "world-knowledge", "known-gap"],
    ),
    QuerySpec(
        "nat12",
        "reliable Japanese hybrid sedan",
        "brand IN ('toyota', 'honda', 'nissan', 'mazda', 'suzuki') "
        "AND powertrain_type IN ('hybrid electric vehicle', 'plug-in hybird electric vehicle') "
        "AND vehicle_category_bottom LIKE '%sedan%'",
        ["natural", "world-knowledge", "known-gap"],
    ),
    QuerySpec(
        "nat13",
        "convertible for weekend drives",
        "vehicle_category_bottom LIKE '%convertible%'",
        ["natural", "category", "rare"],
    ),
    QuerySpec(
        "nat14",
        "spacious car with a big trunk for cargo",
        "cargo_capability = 'yes' AND trunk_volume = 'above 500l'",
        ["natural", "range"],
    ),
    QuerySpec(
        "nat15",
        "带L2辅助驾驶的智能电动车",
        "autonomous_driving_level = 'l2' AND powertrain_type = 'battery electric vehicle' "
        "AND smartness = 'high'",
        ["natural", "zh", "adas"],
    ),
]

ALL_SPECS: List[QuerySpec] = (
    _CATEGORY
    + _BRAND
    + _POWERTRAIN
    + _PRICE
    + _STRUCTURED
    + _AMBIGUOUS
    + _COMBO2
    + _COMBO3
    + _NATURAL
)


@dataclass
class GoldenQuery:
    """A resolved golden-set entry: query plus its relevant car models."""

    id: str
    query: str
    relevant_car_models: List[str]
    tags: List[str]
    note: str = ""

    @property
    def relevant_set(self) -> set:
        return set(self.relevant_car_models)

    def to_json(self) -> Dict:
        return {
            "id": self.id,
            "query": self.query,
            "relevant_car_models": self.relevant_car_models,
            "tags": self.tags,
            "note": self.note,
        }

    @classmethod
    def from_json(cls, data: Dict) -> "GoldenQuery":
        return cls(
            id=data["id"],
            query=data["query"],
            relevant_car_models=data["relevant_car_models"],
            tags=data.get("tags", []),
            note=data.get("note", ""),
        )


def resolve_specs(db_path: Optional[str] = None) -> List[GoldenQuery]:
    """
    Run every spec's ground-truth predicate against the catalogue.

    Specs that match nothing are dropped with a warning rather than silently
    kept — an empty relevant set makes recall undefined and would otherwise
    inflate or deflate the aggregate depending on the convention used.
    """
    import sqlite3

    from src.utils.config import config
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    conn = sqlite3.connect(db_path or config.vehicle_db_path)

    resolved: List[GoldenQuery] = []
    for spec in ALL_SPECS:
        rows = conn.execute(
            f"SELECT car_model FROM vehicles WHERE {spec.where}"  # noqa: S608 - specs are code, not input
        ).fetchall()
        models = sorted(r[0] for r in rows)
        if not models:
            logger.warning(f"[golden-set] {spec.id} '{spec.query}' matched 0 vehicles — dropped")
            continue
        resolved.append(
            GoldenQuery(
                id=spec.id,
                query=spec.query,
                relevant_car_models=models,
                tags=list(spec.tags),
                note=spec.note,
            )
        )

    conn.close()
    return resolved


def write_golden_set(path: Optional[Path] = None, db_path: Optional[str] = None) -> Path:
    """Materialize the resolved golden set to JSONL."""
    import json

    target = Path(path or GOLDEN_SET_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)

    queries = resolve_specs(db_path)
    with target.open("w", encoding="utf-8") as fh:
        for q in queries:
            fh.write(json.dumps(q.to_json(), ensure_ascii=False) + "\n")
    return target


def load_golden_set(path: Optional[Path] = None) -> List[GoldenQuery]:
    """
    Load the golden set, materializing it from the catalogue if absent.

    The JSONL is generated, not hand-maintained: the predicates in this module
    are the source of truth, so a stale file is always safe to regenerate.
    """
    import json

    target = Path(path or GOLDEN_SET_PATH)
    if not target.exists():
        write_golden_set(target)

    with target.open(encoding="utf-8") as fh:
        return [GoldenQuery.from_json(json.loads(line)) for line in fh if line.strip()]
