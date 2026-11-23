"""
Weighted Tri-Partite Preference Modeling for AutoVend Agent (src/agent/preference_model.py).

Separates customer preferences into:
1. Hard Constraints (with optional tolerance bounds and temporal provenance)
2. Soft Preferences (ranked by weight in (0, 1])
3. Negative Exclusions (explicitly rejected powertrains/brands/models/categories that MUST NEVER reappear)

Also provides deterministic Chinese NLU helpers for negative exclusions and soft preferences,
vehicle filtering, soft-preference re-ranking, and prompt formatting.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.agent.schemas import (
    PreferenceModel,
    SessionState,
    WeightedConstraint,
)

# Negative exclusion patterns in Chinese automotive dialogue
_NEG_POWERTRAIN_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不要买|拒绝|不想买)\s*(?:纯电|电动车|BEV|EV)", re.IGNORECASE), "纯电"),
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不要买|拒绝|不想买)\s*(?:增程|增程式|REEV)", re.IGNORECASE), "增程"),
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不要买|拒绝|不想买)\s*(?:插混|插电混动|混动|PHEV)", re.IGNORECASE), "插混"),
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不要买|拒绝|不想买)\s*(?:燃油|油车|汽油车|ICE)", re.IGNORECASE), "燃油"),
]

_NEG_CATEGORY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不想买)\s*(?:SUV|越野车)", re.IGNORECASE), "SUV"),
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不想买)\s*(?:轿车|三厢车)", re.IGNORECASE), "轿车"),
    (re.compile(r"(?:不要|别推荐|不考虑|排除|不想买)\s*(?:MPV|商务车)", re.IGNORECASE), "MPV"),
]

# Generic "不考虑/不要/排除 + Brand/Model" pattern
_NEG_ENTITY_RE = re.compile(
    r"(?:不要|别推荐|不考虑|排除|算了不要|Pass掉|pass掉|不喜欢)\s*([A-Za-z0-9\u4e00-\u9fa5\-]{2,16})"
)

# Common brands for entity classification
_KNOWN_BRANDS = {
    "特斯拉", "tesla", "比亚迪", "byd", "理想", "蔚来", "nio", "小鹏", "xpeng",
    "小米", "问界", "极氪", "zeekr", "吉利", "长安", "奇瑞", "长城", "哈弗",
    "宝马", "bmw", "奔驰", "奥迪", "audi", "大众", "丰田", "本田", "领克",
    "腾势", "阿维塔", "智己", "极狐", "零跑", "哪吒", "埃安", "广汽",
}

_SOFT_PREF_PATTERNS: List[Tuple[re.Pattern, str, str, float]] = [
    (re.compile(r"空间(?:大|宽敞|充裕|大点|大一点)"), "space", "空间大", 0.8),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:舒适|舒服|座椅软|隔音好|静谧)"), "comfort_level", "舒适性高", 0.75),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:智驾|智能驾驶|辅助驾驶|车机好|智能化)"), "smartness", "智能化高", 0.75),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:省油|能耗低|电耗低|经济性|省钱)"), "energy_consumption_level", "低能耗", 0.7),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:颜值|外观好看|帅气|运动感)"), "aesthetics", "外观颜值高", 0.65),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:动力强|加速快|操控好|性能)"), "power_performance", "动力操控强", 0.7),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:安全|气囊多|车身硬)"), "safety", "高安全性", 0.85),
    (re.compile(r"(?:最好|希望|偏向)?.*?(?:家用|带娃|老人|一家人)"), "family_friendliness", "家庭友好", 0.75),
]


def _normalize_powertrain(pt: str) -> str:
    low = pt.strip().lower()
    if any(k in low for k in ("纯电", "bev", "ev")):
        return "纯电"
    if any(k in low for k in ("增程", "reev")):
        return "增程"
    if any(k in low for k in ("插混", "phev", "混动", "dm-i")):
        return "插混"
    if any(k in low for k in ("燃油", "汽油", "油车", "ice")):
        return "燃油"
    return pt.strip()


class PreferenceEngine:
    """Deterministic operations over `PreferenceModel` and `SessionState`."""

    @staticmethod
    def add_hard_constraint(
        prefs: PreferenceModel,
        key: str,
        value: Any,
        turn_index: int = 0,
        tolerance_pct: Optional[float] = None,
        confirmed: bool = True,
    ) -> None:
        if value is None or value == "":
            return
        prefs.hard_constraints[key] = WeightedConstraint(
            key=key,
            value=value,
            weight=1.0,
            tolerance_pct=tolerance_pct,
            turn_index=turn_index,
            confirmed=confirmed,
        )

    @staticmethod
    def add_soft_preference(
        prefs: PreferenceModel,
        key: str,
        value: Any,
        weight: float = 0.7,
        turn_index: int = 0,
    ) -> None:
        if value is None or value == "":
            return
        clamped_w = max(0.05, min(0.99, float(weight)))
        existing = prefs.soft_preferences.get(key)
        # Temporal override: newer turn wins or boosts weight
        if existing and existing.turn_index > turn_index:
            return
        prefs.soft_preferences[key] = WeightedConstraint(
            key=key,
            value=value,
            weight=clamped_w,
            turn_index=turn_index,
            confirmed=True,
        )

    @staticmethod
    def add_negative_exclusion(
        prefs: PreferenceModel,
        kind: str,
        value: str,
        turn_index: int = 0,
    ) -> None:
        val = value.strip()
        if not val:
            return
        neg = prefs.negative_exclusions
        if kind == "powertrain":
            norm = _normalize_powertrain(val)
            if norm not in neg.powertrains:
                neg.powertrains.append(norm)
            neg.exclusion_turns[f"powertrain:{norm}"] = turn_index
            # If user previously had this powertrain as hard constraint, clear it
            hc = prefs.hard_constraints.get("powertrain_type")
            if hc and _normalize_powertrain(str(hc.value)) == norm and turn_index >= hc.turn_index:
                prefs.hard_constraints.pop("powertrain_type", None)
        elif kind == "brand":
            if val not in neg.brands:
                neg.brands.append(val)
            neg.exclusion_turns[f"brand:{val.lower()}"] = turn_index
            hc = prefs.hard_constraints.get("brand")
            if hc and str(hc.value).lower() == val.lower() and turn_index >= hc.turn_index:
                prefs.hard_constraints.pop("brand", None)
        elif kind == "model":
            if val not in neg.models:
                neg.models.append(val)
            neg.exclusion_turns[f"model:{val.lower()}"] = turn_index
        elif kind == "category":
            if val not in neg.categories:
                neg.categories.append(val)
            neg.exclusion_turns[f"category:{val.lower()}"] = turn_index
            hc = prefs.hard_constraints.get("vehicle_category_bottom")
            if hc and str(hc.value).lower() == val.lower() and turn_index >= hc.turn_index:
                prefs.hard_constraints.pop("vehicle_category_bottom", None)
        elif kind == "feature":
            if val not in neg.features:
                neg.features.append(val)
            neg.exclusion_turns[f"feature:{val.lower()}"] = turn_index

    @classmethod
    def parse_user_message_into_preferences(
        cls,
        user_message: str,
        sess: SessionState,
        turn_index: Optional[int] = None,
    ) -> None:
        """
        Deterministically extract negative exclusions, budget tolerance, and soft preferences
        from `user_message` into `sess.preferences`, and sync with `sess.needs`.
        """
        if not user_message:
            return
        t_idx = turn_index if turn_index is not None else int(getattr(sess, "turn_count", 0))
        prefs = sess.preferences

        # 1. Negative powertrain exclusions
        for pat, pt_name in _NEG_POWERTRAIN_PATTERNS:
            if pat.search(user_message):
                cls.add_negative_exclusion(prefs, "powertrain", pt_name, turn_index=t_idx)
                if sess.needs.explicit.powertrain_type and _normalize_powertrain(sess.needs.explicit.powertrain_type) == pt_name:
                    sess.needs.explicit.powertrain_type = ""

        # 2. Negative category exclusions
        for pat, cat_name in _NEG_CATEGORY_PATTERNS:
            if pat.search(user_message):
                cls.add_negative_exclusion(prefs, "category", cat_name, turn_index=t_idx)
                if sess.needs.explicit.vehicle_category_bottom and cat_name.lower() in sess.needs.explicit.vehicle_category_bottom.lower():
                    sess.needs.explicit.vehicle_category_bottom = ""

        # 3. Negative brand / model entity exclusions
        for m in _NEG_ENTITY_RE.finditer(user_message):
            entity = m.group(1).strip("，。！？,.!? ")
            if not entity or len(entity) < 2:
                continue
            # Skip already handled powertrain/category words
            if entity in ("纯电", "电动车", "增程", "插混", "混动", "燃油", "油车", "SUV", "轿车", "MPV"):
                continue
            low_ent = entity.lower()
            if any(b in low_ent for b in _KNOWN_BRANDS) and len(entity) <= 5:
                # Could be a brand alone (e.g. "特斯拉") or brand+model (e.g. "小米SU7")
                if any(ch.isdigit() or ch.isascii() for ch in entity) and not low_ent.isascii():
                    cls.add_negative_exclusion(prefs, "model", entity, turn_index=t_idx)
                elif low_ent in _KNOWN_BRANDS:
                    cls.add_negative_exclusion(prefs, "brand", entity, turn_index=t_idx)
                else:
                    cls.add_negative_exclusion(prefs, "model", entity, turn_index=t_idx)
            else:
                cls.add_negative_exclusion(prefs, "model", entity, turn_index=t_idx)

        # 4. Budget tolerance ("左右", "上下", "大概", "差不多")
        has_approx_budget = any(k in user_message for k in ("左右", "上下", "大概", "大约", "差不多"))
        if sess.needs.explicit.budget_max is not None or sess.needs.explicit.price:
            tol = 0.15 if has_approx_budget else 0.10
            val = sess.needs.explicit.budget_max or sess.needs.explicit.price
            cls.add_hard_constraint(prefs, "budget", val, turn_index=t_idx, tolerance_pct=tol)

        # 5. Soft preferences
        for pat, key, label, weight in _SOFT_PREF_PATTERNS:
            if pat.search(user_message):
                cls.add_soft_preference(prefs, key, label, weight=weight, turn_index=t_idx)
                if hasattr(sess.needs.implicit, key) and not getattr(sess.needs.implicit, key):
                    setattr(sess.needs.implicit, key, label)

        # 6. Sync remaining explicit hard constraints
        cls.sync_from_needs(sess, turn_index=t_idx)

    @classmethod
    def sync_from_needs(cls, sess: SessionState, turn_index: int = 0) -> None:
        """Synchronize `sess.needs.explicit` and `sess.needs.implicit` into `sess.preferences`."""
        prefs = sess.preferences
        exp = sess.needs.explicit

        if exp.powertrain_type:
            norm_pt = _normalize_powertrain(exp.powertrain_type)
            if norm_pt not in prefs.negative_exclusions.powertrains:
                cls.add_hard_constraint(prefs, "powertrain_type", norm_pt, turn_index=turn_index)
            else:
                # Negative exclusion wins unless explicitly cleared
                exp.powertrain_type = ""

        if exp.brand:
            if exp.brand.lower() not in [b.lower() for b in prefs.negative_exclusions.brands]:
                cls.add_hard_constraint(prefs, "brand", exp.brand, turn_index=turn_index)
            else:
                exp.brand = ""

        if exp.vehicle_category_bottom:
            if exp.vehicle_category_bottom.lower() not in [c.lower() for c in prefs.negative_exclusions.categories]:
                cls.add_hard_constraint(prefs, "vehicle_category_bottom", exp.vehicle_category_bottom, turn_index=turn_index)
            else:
                exp.vehicle_category_bottom = ""

        if exp.seat_layout:
            cls.add_hard_constraint(prefs, "seat_layout", exp.seat_layout, turn_index=turn_index)

        if exp.budget_max is not None:
            existing = prefs.hard_constraints.get("budget")
            tol = existing.tolerance_pct if existing and existing.tolerance_pct is not None else 0.15
            cls.add_hard_constraint(prefs, "budget", exp.budget_max, turn_index=turn_index, tolerance_pct=tol)

    @staticmethod
    def is_vehicle_excluded(car: Dict[str, Any], prefs: PreferenceModel) -> Tuple[bool, str]:
        """Return `(True, reason)` if `car` violates any negative exclusion."""
        neg = prefs.negative_exclusions
        meta = car.get("metadata") if isinstance(car.get("metadata"), dict) else {}

        car_model = str(car.get("car_model") or meta.get("car_model") or "").strip()
        car_brand = str(car.get("brand") or meta.get("brand") or "").strip()
        car_power = str(
            car.get("powertrain_type") or car.get("power_type") or meta.get("powertrain_type") or ""
        ).strip()
        car_cat = str(
            car.get("vehicle_category_bottom") or car.get("category") or meta.get("vehicle_category_bottom") or ""
        ).strip()

        if car_power:
            norm_cp = _normalize_powertrain(car_power)
            for ex_pt in neg.powertrains:
                if _normalize_powertrain(ex_pt) == norm_cp:
                    return True, f"excluded_powertrain:{ex_pt}"

        for ex_brand in neg.brands:
            if ex_brand.lower() in car_brand.lower() or ex_brand.lower() in car_model.lower():
                return True, f"excluded_brand:{ex_brand}"

        for ex_model in neg.models:
            if ex_model.lower() in car_model.lower():
                return True, f"excluded_model:{ex_model}"

        if car_cat:
            for ex_cat in neg.categories:
                if ex_cat.lower() in car_cat.lower():
                    return True, f"excluded_category:{ex_cat}"

        return False, ""

    @classmethod
    def filter_excluded_vehicles(
        cls,
        cars: List[Dict[str, Any]],
        prefs: PreferenceModel,
    ) -> List[Dict[str, Any]]:
        """Filter out any vehicles violating `prefs.negative_exclusions` and sort by soft fit."""
        kept: List[Dict[str, Any]] = []
        for car in cars or []:
            excluded, _ = cls.is_vehicle_excluded(car, prefs)
            if not excluded:
                kept.append(car)
        if prefs.soft_preferences and len(kept) > 1:
            kept.sort(key=lambda c: cls.score_vehicle_soft_fit(c, prefs), reverse=True)
        return kept

    @staticmethod
    def score_vehicle_soft_fit(car: Dict[str, Any], prefs: PreferenceModel) -> float:
        """Compute soft-preference alignment score in [0.0, 1.0] for ranking."""
        if not prefs.soft_preferences:
            return float(car.get("score", 0.5) or 0.5)
        text_blob = (
            f"{car.get('car_model', '')} {car.get('text_snippet', '')} "
            f"{car.get('highlights', '')} {car.get('metadata', '')}"
        ).lower()
        total_w = sum(c.weight for c in prefs.soft_preferences.values()) or 1.0
        matched_w = 0.0
        keyword_map = {
            "space": ("空间", "轴距", "宽敞", "大五座", "6座", "7座", "后备箱"),
            "comfort_level": ("舒适", "空悬", "静谧", "按摩", "座椅", "nvh"),
            "smartness": ("智驾", "激光雷达", "鸿蒙", "车机", "城市noa", "辅助驾驶"),
            "energy_consumption_level": ("能耗", "油耗", "电耗", "省油", "低功耗"),
            "aesthetics": ("颜值", "猎装", "轿跑", "设计", "流线"),
            "power_performance": ("加速", "马力", "零百", "四驱", "操控"),
            "safety": ("安全", "气囊", "高强度钢", "防撞", "电池安全"),
            "family_friendliness": ("家用", "家庭", "亲子", "儿童", "奶爸"),
        }
        for key, constraint in prefs.soft_preferences.items():
            kws = keyword_map.get(key, (str(constraint.value).lower(),))
            if any(k in text_blob for k in kws):
                matched_w += constraint.weight
        base_score = float(car.get("score", 0.5) or 0.5)
        return round(0.5 * base_score + 0.5 * (matched_w / total_w), 4)

    @staticmethod
    def format_for_prompt(prefs: PreferenceModel) -> str:
        """Render tri-partite preferences for injection into LLM dynamic context."""
        lines: List[str] = []
        if prefs.hard_constraints:
            hard_items = []
            for k, c in prefs.hard_constraints.items():
                tol_str = f" (容差±{int(c.tolerance_pct * 100)}%)" if c.tolerance_pct else ""
                hard_items.append(f"{k}={c.value}{tol_str}")
            lines.append("硬约束: " + ", ".join(hard_items))
        if prefs.soft_preferences:
            soft_items = [
                f"{c.value}(权重{c.weight:.2f})"
                for c in sorted(prefs.soft_preferences.values(), key=lambda x: x.weight, reverse=True)
            ]
            lines.append("软偏好: " + ", ".join(soft_items))
        neg = prefs.negative_exclusions
        neg_parts = []
        if neg.powertrains:
            neg_parts.append("动力=" + "/".join(neg.powertrains))
        if neg.brands:
            neg_parts.append("品牌=" + "/".join(neg.brands))
        if neg.models:
            neg_parts.append("车型=" + "/".join(neg.models))
        if neg.categories:
            neg_parts.append("类别=" + "/".join(neg.categories))
        if neg_parts:
            lines.append("绝对负向排除(严禁推荐): " + "; ".join(neg_parts))
        return "\n".join(lines)
