"""
Rule-based PII interceptor.

Sits between the user's message and everything downstream — memory, extraction
prompts, retrieval queries, the cloud LLM. Real identifiers never leave the
process; the models see stable placeholders instead.

**Masking is reversible, and that is not a convenience.** An irreversible
redactor would break the product: the agent has to greet the customer by name
and put a real phone number on the test-drive booking. So each session keeps a
placeholder -> original mapping, and values extracted *out* of the models get
restored before they are stored or shown. The LLM reasons over
`<CN_PERSON_1>`; the reservation record holds 张伟.

Two properties the mapping must have, both load-bearing:

1. **Stable within a session.** The same name must map to the same placeholder
   on every turn, or the conversation history stops being coherent — turn 3
   would refer to a different token than turn 1 for the same person.
2. **Not decodable across sessions.** Placeholders carry a per-session tag, so
   one conversation's vault cannot resolve another's text. Without the tag every
   session numbers from 1 and a session_id mix-up would silently substitute a
   different customer's name — the wrong-person failure mode a privacy layer
   least wants.
"""

import hashlib
import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.privacy.recognizers import CN_ENTITIES, build_recognizers
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Presidio built-ins kept alongside the Chinese recognizers. Format-driven and
#: language-independent. EMAIL_ADDRESS is deliberately absent — the built-in
#: over-captures across CJK boundaries, so `AsciiEmailRecognizer` provides it.
BUILTIN_ENTITIES = ["CREDIT_CARD", "IP_ADDRESS", "IBAN_CODE"]

#: Minimum confidence for a detection to be masked. Below this the recognizers
#: produce more false positives (a model name read as a person) than genuine
#: hits, and a false positive corrupts the query the user actually asked.
DEFAULT_THRESHOLD = 0.5

# Entity type, optional session tag, index.
_PLACEHOLDER_RE = re.compile(r"<([A-Z_]+?)_(?:([0-9a-f]{4})_)?(\d+)>")


@dataclass(frozen=True)
class PIIMatch:
    """One detected entity."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float


@dataclass
class SessionVault:
    """Per-session placeholder <-> original mapping."""

    tag: str = ""
    to_original: Dict[str, str] = field(default_factory=dict)
    to_placeholder: Dict[str, str] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)

    def placeholder_for(self, entity_type: str, original: str) -> str:
        """Stable placeholder for a value within this session."""
        key = f"{entity_type}:{original}"
        if key in self.to_placeholder:
            return self.to_placeholder[key]

        index = self.counters.get(entity_type, 0) + 1
        self.counters[entity_type] = index
        placeholder = f"<{entity_type}_{self.tag}{index}>"
        self.to_placeholder[key] = placeholder
        self.to_original[placeholder] = original
        return placeholder


def _session_tag(session_id: str) -> str:
    """
    Short per-session token embedded in every placeholder.

    Without it every session numbers from 1, so `<CN_PERSON_1>` exists in all of
    them and one session's vault will happily decode another's text — silently
    substituting a different customer's name. A session_id mix-up should fail
    to resolve, not resolve to the wrong person.

    Derived from the session id rather than random so a placeholder stays
    reproducible for the same session; it is a namespace, not a secret.
    """
    return hashlib.blake2s(session_id.encode("utf-8"), digest_size=2).hexdigest() + "_"


class PIIInterceptor:
    """
    Detects and reversibly masks PII.

    Thread-safe: FastAPI serves concurrent sessions and the vaults are shared
    state. The Presidio analyzer itself is built lazily because loading spaCy
    costs seconds, and a deployment that never sees PII should not pay for it
    at import time.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        entities: Optional[List[str]] = None,
    ):
        self.threshold = threshold
        self.entities = entities if entities is not None else CN_ENTITIES + BUILTIN_ENTITIES
        self._analyzer = None
        self._vaults: Dict[str, SessionVault] = {}
        self._lock = threading.Lock()

    # ── analyzer ──────────────────────────────────────────────────────

    @property
    def analyzer(self):
        if self._analyzer is None:
            with self._lock:
                if self._analyzer is None:
                    self._analyzer = self._build_analyzer()
        return self._analyzer

    def _build_analyzer(self):
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        # Map zh onto the English spaCy pipeline: the Chinese recognizers are
        # pure regex and never consult it, but Presidio requires *some* NLP
        # engine registered for the language it is asked to analyze.
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "en", "model_name": "en_core_web_lg"},
                    {"lang_code": "zh", "model_name": "en_core_web_lg"},
                ],
            }
        )
        engine = AnalyzerEngine(
            nlp_engine=provider.create_engine(),
            supported_languages=["en", "zh"],
        )

        # Drop the built-in EmailRecognizer before adding ours. Both claim
        # EMAIL_ADDRESS, and the built-in's `\w` local part swallows preceding
        # CJK ("邮箱zhang@example.com" matched whole), so it wins the overlap
        # resolution on length and masks the surrounding word.
        for recognizer in list(engine.registry.recognizers):
            if recognizer.name == "EmailRecognizer":
                engine.registry.remove_recognizer("EmailRecognizer")

        for recognizer in build_recognizers("zh"):
            engine.registry.add_recognizer(recognizer)
        logger.info(f"PII analyzer ready — entities: {', '.join(self.entities)}")
        return engine

    # ── detection ─────────────────────────────────────────────────────

    def detect(self, text: str) -> List[PIIMatch]:
        """Find PII in `text`, highest-confidence and longest spans first."""
        if not text or not text.strip():
            return []

        results = self.analyzer.analyze(
            text=text,
            language="zh",
            entities=self.entities,
            score_threshold=self.threshold,
        )
        matches = [
            PIIMatch(
                entity_type=r.entity_type,
                text=text[r.start : r.end],
                start=r.start,
                end=r.end,
                score=r.score,
            )
            for r in results
        ]
        return _drop_overlaps(matches)

    # ── masking ───────────────────────────────────────────────────────

    def mask(self, text: str, session_id: str) -> Tuple[str, List[PIIMatch]]:
        """
        Replace PII with per-session placeholders.

        Returns the masked text and what was found, so callers can log the
        entity *types* that were intercepted without logging the values.
        """
        matches = self.detect(text)
        if not matches:
            return text, []

        vault = self._vault(session_id)
        # Replace back-to-front so earlier offsets stay valid.
        masked = text
        for match in sorted(matches, key=lambda m: m.start, reverse=True):
            placeholder = vault.placeholder_for(match.entity_type, match.text)
            masked = masked[: match.start] + placeholder + masked[match.end :]

        logger.info(
            f"[{session_id}] masked {len(matches)} PII span(s): "
            f"{', '.join(sorted({m.entity_type for m in matches}))}"
        )
        return masked, matches

    def unmask(self, text: str, session_id: str) -> str:
        """Restore original values in text that came back from a model."""
        if not text:
            return text
        vault = self._vaults.get(session_id)
        if vault is None or not vault.to_original:
            return text

        def replace(match: re.Match) -> str:
            return vault.to_original.get(match.group(0), match.group(0))

        return _PLACEHOLDER_RE.sub(replace, text)

    def unmask_mapping(self, data: Dict, session_id: str) -> Dict:
        """
        Restore placeholders throughout a nested dict.

        Extractors return Pydantic models dumped to dicts; a name that was
        masked on the way in comes back as `<CN_PERSON_1>` and has to be
        restored before it is stored or shown to the user.
        """
        vault = self._vaults.get(session_id)
        if vault is None or not vault.to_original:
            return data
        return _walk(data, lambda value: self.unmask(value, session_id))

    # ── vault lifecycle ───────────────────────────────────────────────

    def _vault(self, session_id: str) -> SessionVault:
        with self._lock:
            if session_id not in self._vaults:
                self._vaults[session_id] = SessionVault(tag=_session_tag(session_id))
            return self._vaults[session_id]

    def clear_session(self, session_id: str) -> None:
        """Drop a session's mapping. Call when the conversation ends."""
        with self._lock:
            self._vaults.pop(session_id, None)

    def vault_summary(self, session_id: str) -> Dict[str, int]:
        """Counts by entity type — for /health and tests, never the values."""
        vault = self._vaults.get(session_id)
        if vault is None:
            return {}
        counts: Dict[str, int] = {}
        for placeholder in vault.to_original:
            match = _PLACEHOLDER_RE.match(placeholder)
            if match:
                counts[match.group(1)] = counts.get(match.group(1), 0) + 1
        return counts


def _drop_overlaps(matches: List[PIIMatch]) -> List[PIIMatch]:
    """
    Keep the strongest match per overlapping span.

    An ID card matches the bank-card pattern too; masking both would nest
    placeholders and corrupt the text. Longer spans win ties so the more
    specific entity survives.
    """
    ordered = sorted(matches, key=lambda m: (-m.score, -(m.end - m.start), m.start))
    kept: List[PIIMatch] = []
    for match in ordered:
        if any(match.start < k.end and k.start < match.end for k in kept):
            continue
        kept.append(match)
    return sorted(kept, key=lambda m: m.start)


def _walk(value, fn):
    """Apply `fn` to every string in a nested structure."""
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, dict):
        return {k: _walk(v, fn) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(v, fn) for v in value]
    return value


_default_interceptor: Optional[PIIInterceptor] = None
_default_lock = threading.Lock()


def get_interceptor() -> PIIInterceptor:
    """Process-wide interceptor. One spaCy pipeline is enough."""
    global _default_interceptor
    if _default_interceptor is None:
        with _default_lock:
            if _default_interceptor is None:
                _default_interceptor = PIIInterceptor()
    return _default_interceptor
