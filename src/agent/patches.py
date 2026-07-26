"""
Incremental state patches.

The conversation has two kinds of memory and they age differently. The
transcript is *process* — it scrolls out of the sliding window and is gone. The
extracted profile, needs and reservation are *result* — they must survive
indefinitely, because a budget stated on turn 2 still constrains the
recommendation on turn 20, long after the sentence that carried it has been
evicted.

Patches are how the second kind stays auditable. Each turn emits the set of
changes it made, so the structured state is not just a blob that mysteriously
differs from last turn — it has a history saying which turn set which field,
and to what.

That history buys three things the flat state alone cannot give:

1. **Auditing.** "Where did `prize=40到60万` come from?" is answerable.
2. **Precise rollback.** A stage rollback can revert exactly the fields that
   stage introduced, rather than clearing whole sub-objects and losing facts
   the customer gave earlier.
3. **Compact prompt injection.** The most recent patches summarise what just
   changed in a few lines, without re-serialising every field on every turn.

The format is deliberately close to RFC 6902 (op / path / value) but not
literally it: paths are dotted rather than JSON Pointer because the state is a
fixed Pydantic tree, not arbitrary JSON, and the extra escaping would buy
nothing.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

#: Sub-models of SessionState that carry extracted facts. Order fixes the
#: order patches appear in, which keeps diffs of the patch log readable.
PATCHABLE_PATHS = (
    ("profile", "profile"),
    ("needs.explicit", "needs.explicit"),
    ("needs.implicit", "needs.implicit"),
    ("reservation", "reservation"),
)

#: Values that mean "not set". A field going from absent to absent is not a
#: change, and an extractor returning "" for a field it did not find must not
#: look like the customer retracting it.
_EMPTY = ("", None, [], {})


class PatchOp(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"


@dataclass(frozen=True)
class StatePatch:
    """One field-level change."""

    op: PatchOp
    path: str
    value: Any = None
    previous: Any = None
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"op": self.op.value, "path": self.path}
        if self.op is not PatchOp.REMOVE:
            payload["value"] = self.value
        if self.previous not in _EMPTY:
            payload["previous"] = self.previous
        if self.source:
            payload["source"] = self.source
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatePatch":
        return cls(
            op=PatchOp(data["op"]),
            path=data["path"],
            value=data.get("value"),
            previous=data.get("previous"),
            source=data.get("source", ""),
        )

    def describe(self) -> str:
        if self.op is PatchOp.REMOVE:
            return f"{self.path} 已清除"
        if self.op is PatchOp.UPDATE:
            return f"{self.path}: {self.previous!r} → {self.value!r}"
        return f"{self.path} = {self.value!r}"


@dataclass
class PatchLog:
    """Ordered patches for one session, newest last."""

    entries: List[StatePatch] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def extend(self, patches: Iterable[StatePatch]) -> None:
        self.entries.extend(patches)

    def recent(self, n: int = 5) -> List[StatePatch]:
        return self.entries[-n:]

    def for_path(self, prefix: str) -> List[StatePatch]:
        """Every patch touching a path, e.g. all of `needs.explicit`."""
        return [p for p in self.entries if p.path == prefix or p.path.startswith(prefix + ".")]

    def to_json(self) -> str:
        return json.dumps([p.to_dict() for p in self.entries], ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "PatchLog":
        return cls(entries=[StatePatch.from_dict(d) for d in json.loads(raw)])


# ── Snapshot and diff ─────────────────────────────────────────────────


def snapshot(state) -> Dict[str, Any]:
    """Flatten the structured state to {dotted_path: value}, skipping empties."""
    flat: Dict[str, Any] = {}
    for prefix, attribute in PATCHABLE_PATHS:
        model = _resolve(state, attribute)
        if model is None:
            continue
        for name, value in model.model_dump().items():
            if value not in _EMPTY:
                flat[f"{prefix}.{name}"] = value
    return flat


def diff(
    before: Dict[str, Any],
    after: Dict[str, Any],
    source: str = "",
) -> List[StatePatch]:
    """
    Patches turning `before` into `after`.

    Fields present in `before` but absent in `after` produce **no** patch. The
    extractors merge rather than replace, so a field disappearing means this
    turn's extraction had nothing to say about it — not that the customer
    retracted it. Emitting a remove there would erase facts every time a turn
    happened not to mention them.

    Genuine removals go through `removal_patches`, which the rollback path uses
    when it deliberately discards a stage's output.
    """
    patches: List[StatePatch] = []
    for path, value in after.items():
        old = before.get(path)
        if old == value:
            continue
        patches.append(
            StatePatch(
                op=PatchOp.UPDATE if path in before else PatchOp.ADD,
                path=path,
                value=value,
                previous=old,
                source=source,
            )
        )
    return patches


def removal_patches(
    paths: Iterable[str], before: Dict[str, Any], source: str = ""
) -> List[StatePatch]:
    """Explicit removals, for state a rollback deliberately drops."""
    return [
        StatePatch(op=PatchOp.REMOVE, path=path, previous=before.get(path), source=source)
        for path in paths
        if path in before
    ]


def apply_patches(state, patches: Iterable[StatePatch]) -> List[str]:
    """
    Apply patches to a SessionState in place. Returns the paths applied.

    Unknown paths are skipped rather than raising: a patch log written by an
    older schema must not make a session unloadable.
    """
    applied: List[str] = []
    for patch in patches:
        prefix, _, name = patch.path.rpartition(".")
        model = _resolve(state, prefix)
        if model is None or not hasattr(model, name):
            continue
        setattr(model, name, "" if patch.op is PatchOp.REMOVE else patch.value)
        applied.append(patch.path)
    return applied


def invert(patches: Iterable[StatePatch]) -> List[StatePatch]:
    """
    Patches undoing the given ones, newest first.

    Lets a rollback revert exactly what a stage contributed instead of clearing
    whole sub-objects — the difference between "forget the budget you just
    changed" and "forget everything about your requirements".
    """
    inverted: List[StatePatch] = []
    for patch in reversed(list(patches)):
        if patch.op is PatchOp.ADD:
            inverted.append(
                StatePatch(PatchOp.REMOVE, patch.path, previous=patch.value, source="revert")
            )
        elif patch.op is PatchOp.UPDATE:
            inverted.append(
                StatePatch(
                    PatchOp.UPDATE,
                    patch.path,
                    value=patch.previous,
                    previous=patch.value,
                    source="revert",
                )
            )
        else:  # REMOVE
            inverted.append(
                StatePatch(PatchOp.ADD, patch.path, value=patch.previous, source="revert")
            )
    return inverted


def format_for_prompt(patches: Iterable[StatePatch], limit: int = 6) -> str:
    """Render recent changes for injection into a generation prompt."""
    entries = list(patches)[-limit:]
    if not entries:
        return ""
    lines = "\n".join(f"- {p.describe()}" for p in entries)
    return f"本轮/近期状态更新：\n{lines}"


def _resolve(state, path: str) -> Optional[Any]:
    """Walk a dotted attribute path, returning None if any hop is missing."""
    current = state
    if not path:
        return current
    for part in path.split("."):
        current = getattr(current, part, None)
        if current is None:
            return None
    return current
