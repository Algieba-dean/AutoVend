"""
Dynamic Competitor Battlecards & Comparative Pitching Module (`src/agent/battlecards.py`).

Detects competitor vehicle mentions in customer input and generates grounded
tactical battlecards backed by:
1. Dynamic CMS / JSON knowledge store (`storage/knowledge/battlecards.json` if present)
   supporting runtime CRUD updates.
2. Live `TruthEngineFacade` synthesis (MIIT specs, real-world range gap, owner
   reliability/safety cases) and `ServiceContainer.get_rag_service()` retrieval
   for any known vehicle model — avoiding static hardcoded model dictionaries.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.container import ServiceContainer
from src.core.interfaces import RAGQueryRequest
from src.core.truth_engine import TruthEngineFacade

logger = logging.getLogger(__name__)

DEFAULT_BATTLECARD_CMS_PATH = Path("storage/knowledge/battlecards.json")


class Battlecard(BaseModel):
    """Battlecard data structure for a competitor model or brand."""

    name: str
    category: str = "竞品车型"
    target_competitors: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    counter_points: List[str] = Field(default_factory=list)
    source: str = "dynamic_truth_engine"

    def to_system_note(self) -> str:
        """Format battlecard into a concise system note for response generator."""
        strengths_str = "、".join(self.strengths) if self.strengths else "市场关注度较高"
        counter_str = "；".join(
            [f"({i + 1}) {cp}" for i, cp in enumerate(self.counter_points)]
        )
        return (
            f"[系统竞品战术卡提示] ({self.source}): 检测到客户提及/关注竞品【{self.name}】"
            f"（竞品卖点: {strengths_str}）。"
            f"请在回复中予以客观尊重，同时从以下实测与配置维度展开对比：{counter_str}。"
        )


class BattlecardStore:
    """
    Dynamic CMS + TruthEngine + RAG-backed battlecard repository.
    """

    _instance: Optional["BattlecardStore"] = None

    def __init__(self, cms_path: Optional[Path] = None):
        self.cms_path = Path(cms_path) if cms_path else DEFAULT_BATTLECARD_CMS_PATH
        self._cms_cards: Dict[str, Battlecard] = {}
        self.reload()

    @classmethod
    def get_instance(cls) -> "BattlecardStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self) -> None:
        """Load battlecards from CMS JSON file if it exists."""
        self._cms_cards.clear()
        if not self.cms_path.exists():
            return
        try:
            raw = json.loads(self.cms_path.read_text(encoding="utf-8"))
            items = raw if isinstance(raw, list) else raw.get("battlecards", [])
            for item in items:
                card = Battlecard.model_validate({**item, "source": item.get("source", "cms")})
                self._cms_cards[card.name.lower()] = card
        except Exception as exc:
            logger.warning(f"Failed to load battlecards CMS from {self.cms_path}: {exc}")

    def upsert_battlecard(self, card: Battlecard, persist: bool = False) -> None:
        """Register or update a battlecard dynamically at runtime."""
        self._cms_cards[card.name.lower()] = card
        if persist:
            self.cms_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [c.model_dump() for c in self._cms_cards.values()]
            self.cms_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def _synthesize_from_truth_and_rag(
        self,
        model_name: str,
        matched_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Battlecard]:
        """Synthesize a grounded battlecard from TruthEngineFacade + RAGService."""
        strengths: List[str] = []
        counter_points: List[str] = []
        category = "智能新能源汽车"

        # 1. Query TruthEngineFacade for MIIT specs, real-world range gap & owner cases
        try:
            truth = TruthEngineFacade.get_instance()
            specs = truth.deconstruct_vehicle_specs(model_name)
            if isinstance(specs, dict) and specs.get("found_in_miit"):
                details = specs.get("details") if isinstance(specs.get("details"), dict) else specs
                if details.get("battery_chemistry"):
                    strengths.append(f"电池体系 {details['battery_chemistry']}")
                if details.get("motor_peak_power_kw"):
                    strengths.append(f"峰值功率 {details['motor_peak_power_kw']}kW")
                if details.get("cltc_energy_consumption"):
                    strengths.append(f"申报电耗 {details['cltc_energy_consumption']}kWh/100km")
                for pt in (details.get("analysis_points") or [])[:2]:
                    counter_points.append(str(pt)[:100])

            cases = truth.get_real_owner_feedback_and_safety_cases(model_name)
            if isinstance(cases, dict):
                case_list = cases.get("cases") or cases.get("feedback") or []
                for c in case_list[:2]:
                    summary = c.get("summary") or c.get("title") or str(c)
                    if summary:
                        counter_points.append(f"提醒关注真实车主反馈维度：{summary[:80]}")
        except Exception as exc:
            logger.debug(f"TruthEngine battlecard synthesis skipped for {model_name}: {exc}")

        # 2. Enrich with live RAG retrieval if available
        try:
            rag = ServiceContainer.get_rag_service()
            if rag is not None:
                resp = rag.search_vehicles(
                    RAGQueryRequest(query_text=model_name, top_k=2)
                )
                for car in getattr(resp, "results", []) or []:
                    if not isinstance(car, dict):
                        continue
                    price = car.get("price_wan") or car.get("price")
                    rng = car.get("electric_range")
                    if price or rng:
                        strengths.append(
                            " ".join(
                                p
                                for p in (
                                    f"参考价 {price}" if price else "",
                                    f"续航 {rng}" if rng else "",
                                )
                                if p
                            )
                        )
                    snippet = str(car.get("text_snippet") or "").strip()
                    if snippet and len(counter_points) < 3:
                        counter_points.append(f"核对配置清单：{snippet[:90]}")
                    break
        except Exception as exc:
            logger.debug(f"RAG battlecard enrichment skipped for {model_name}: {exc}")

        # 3. Grounded comparison against our currently matched_cars
        if matched_cars:
            top_car = matched_cars[0] if isinstance(matched_cars[0], dict) else {}
            our_model = top_car.get("car_model") or top_car.get("model")
            our_price = top_car.get("price_wan") or top_car.get("price")
            our_range = top_car.get("electric_range")
            if our_model and our_model.lower() != model_name.lower():
                facts = [
                    p
                    for p in (
                        f"参考价 {our_price}" if our_price else "",
                        f"续航 {our_range}" if our_range else "",
                    )
                    if p
                ]
                fact_str = f"（{'，'.join(facts)}）" if facts else ""
                counter_points.append(
                    f"结合客户预算与用车场景，横向对比我方候选车型【{our_model}】{fact_str}的落地性价比与配置达成度"
                )

        if not strengths and not counter_points:
            return None

        if not strengths:
            strengths = ["市场知名度与关注度较高"]
        if not counter_points:
            counter_points = [
                f"从真实落地价、实测续航达成率及售后质保政策维度与【{model_name}】做客观横向对比"
            ]

        return Battlecard(
            name=model_name,
            category=category,
            target_competitors=[model_name.lower()],
            strengths=strengths[:3],
            counter_points=counter_points[:3],
            source="dynamic_truth_rag",
        )

    def match(
        self,
        conversation_text: str,
        matched_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Battlecard]:
        """Match CMS battlecards or dynamically synthesize grounded cards for mentioned models."""
        if not conversation_text:
            return []

        text_lower = conversation_text.lower()
        text_norm = re.sub(r"\s+", "", text_lower)
        results: List[Battlecard] = []
        matched_norms: set[str] = set()

        # 1. Check dynamic CMS registry first
        for card in self._cms_cards.values():
            if any(
                kw.lower() in text_lower or re.sub(r"\s+", "", kw.lower()) in text_norm
                for kw in card.target_competitors
            ):
                results.append(card)
                matched_norms.add(re.sub(r"\s+", "", card.name.lower()))
                for kw in card.target_competitors:
                    matched_norms.add(re.sub(r"\s+", "", kw.lower()))

        # 2. Detect any known vehicle model from TruthEngineFacade not already matched
        try:
            truth = TruthEngineFacade.get_instance()
            known_models = truth.get_known_models()
            for model in sorted(known_models, key=len, reverse=True):
                model_lower = model.lower()
                model_norm = re.sub(r"\s+", "", model_lower)
                base_norm = re.sub(r"(?:ev|dm-i|pro|max|ultra|标准版|增程版)$", "", model_norm)
                exact_hit = model_lower in text_lower or model_norm in text_norm
                base_hit = not exact_hit and len(base_norm) >= 4 and base_norm in text_norm
                if not (exact_hit or base_hit):
                    continue
                if model_norm in matched_norms or (base_hit and base_norm in matched_norms):
                    continue
                # Skip if it's already the primary recommended car
                if matched_cars and any(
                    str(c.get("car_model") or "").lower() == model_lower
                    for c in matched_cars[:1]
                    if isinstance(c, dict)
                ):
                    continue
                synthesized = self._synthesize_from_truth_and_rag(
                    model, matched_cars=matched_cars
                )
                if synthesized is not None:
                    results.append(synthesized)
                    matched_norms.add(model_norm)
                    if base_hit:
                        matched_norms.add(base_norm)
        except Exception as exc:
            logger.debug(f"Dynamic battlecard model discovery skipped: {exc}")

        return results


def match_battlecards(
    conversation_text: str,
    matched_cars: Optional[List[Dict[str, Any]]] = None,
    store: Optional[BattlecardStore] = None,
) -> List[Battlecard]:
    """
    Search conversation history or latest text for competitor mentions and return
    dynamically grounded Battlecards from CMS + TruthEngine + RAGService.
    """
    active_store = store or BattlecardStore.get_instance()
    return active_store.match(conversation_text, matched_cars=matched_cars)
