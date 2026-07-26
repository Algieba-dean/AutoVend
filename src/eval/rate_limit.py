"""
Client-side rate limiting for LLM-judged evaluation.

Three mechanisms, each covering a limit the others cannot:

- **Semaphore** caps in-flight requests. Providers throttle on concurrency
  independently of throughput, and an unbounded `asyncio.gather` over 500
  evaluation tasks opens 500 sockets at once — which fails as connection errors
  rather than clean 429s, so retries do not help.
- **Request bucket (RPM)** caps requests per minute.
- **Token bucket (TPM)** caps tokens per minute. This is the binding limit for
  judge workloads: a judge prompt carrying retrieved context runs to thousands
  of tokens, so the token ceiling is reached long before the request ceiling.

Both buckets refill continuously rather than resetting on a minute boundary. A
window-reset limiter lets a burst drain the whole allowance in the first second
of each window, which providers see as a spike and reject.

**On the numbers.** The limits are configuration, not constants — a paid tier
allows an order of magnitude more than a free one, and a limiter tuned for the
wrong tier either wastes capacity or gets throttled anyway. `RateLimits.free`
and `.paid` are starting points; read the actual values from the provider
dashboard.

429 still happens even with correct client-side limits: the ceiling is shared
across every client using the key. Retries use exponential backoff with jitter,
and honour `Retry-After` when the provider sends it, because the provider knows
when it will let you back in and guessing is strictly worse.
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RateLimits:
    """Provider limits. Read these off the dashboard, do not guess."""

    rpm: int
    tpm: int
    concurrency: int
    name: str = "custom"

    @classmethod
    def free_tier(cls) -> "RateLimits":
        """
        Conservative defaults for a free tier.

        Deliberately below the published ceiling: free tiers also enforce a
        daily token budget, and saturating the per-minute limit is the fastest
        way to exhaust it mid-run — which is exactly how one RAGAS run was lost
        (see docs/record.md #15).
        """
        return cls(rpm=30, tpm=6_000, concurrency=3, name="free")

    @classmethod
    def paid_tier(cls) -> "RateLimits":
        """Typical paid-tier headroom."""
        return cls(rpm=2_550, tpm=212_500, concurrency=7, name="paid")


class TokenBucket:
    """
    Continuously-refilling token bucket.

    `capacity` is the burst allowance and `rate` the steady-state refill per
    second. A caller asking for more than `capacity` would block forever, so
    that request is clamped and logged rather than deadlocking the run.
    """

    def __init__(self, rate: float, capacity: Optional[float] = None, name: str = ""):
        self.rate = rate
        self.capacity = capacity if capacity is not None else rate
        self.name = name
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
        self._updated = now

    async def acquire(self, amount: float = 1.0) -> float:
        """Wait until `amount` tokens are available. Returns seconds waited."""
        if amount > self.capacity:
            logger.warning(
                f"[{self.name}] request of {amount:.0f} exceeds bucket capacity "
                f"{self.capacity:.0f}; clamping"
            )
            amount = self.capacity

        waited = 0.0
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= amount:
                    self._tokens -= amount
                    return waited
                deficit = amount - self._tokens
                delay = deficit / self.rate if self.rate > 0 else 0.05
            delay = min(max(delay, 0.01), 5.0)
            await asyncio.sleep(delay)
            waited += delay

    @property
    def available(self) -> float:
        self._refill()
        return self._tokens


@dataclass
class LimiterStats:
    """What the limiter did, for reporting the cost of throttling."""

    requests: int = 0
    tokens: int = 0
    retries: int = 0
    rate_limited: int = 0
    wait_seconds: float = 0.0
    failures: int = 0

    def as_dict(self) -> dict:
        return {
            "requests": self.requests,
            "tokens": self.tokens,
            "retries": self.retries,
            "rate_limited": self.rate_limited,
            "wait_seconds": round(self.wait_seconds, 2),
            "failures": self.failures,
        }


class RateLimiter:
    """
    Semaphore + RPM bucket + TPM bucket, plus retry with backoff.

    Wrap any awaitable that performs one provider call:

        async with limiter.slot(estimated_tokens=1200):
            ...

    or let `call()` handle the retry loop as well.
    """

    def __init__(self, limits: Optional[RateLimits] = None, max_retries: int = 5):
        self.limits = limits or RateLimits.free_tier()
        self.max_retries = max_retries
        self.stats = LimiterStats()

        self._semaphore = asyncio.Semaphore(self.limits.concurrency)
        # Capacity equals the per-minute allowance: a full minute's worth may
        # burst, then throughput settles to the refill rate.
        self._requests = TokenBucket(
            rate=self.limits.rpm / 60.0, capacity=self.limits.rpm, name="rpm"
        )
        self._tokens = TokenBucket(
            rate=self.limits.tpm / 60.0, capacity=self.limits.tpm, name="tpm"
        )

    async def acquire(self, estimated_tokens: int = 0) -> None:
        """Block until this call fits under both ceilings."""
        waited = await self._requests.acquire(1)
        if estimated_tokens:
            waited += await self._tokens.acquire(estimated_tokens)
        self.stats.wait_seconds += waited
        self.stats.requests += 1
        self.stats.tokens += estimated_tokens

    async def call(self, fn, *args, estimated_tokens: int = 0, **kwargs):
        """
        Run `fn` under the limits, retrying rate-limit and transient errors.

        `fn` may be sync or async; a sync callable runs in a worker thread so a
        blocking HTTP client cannot stall the event loop — which would silently
        serialise the whole queue and make the concurrency setting a lie.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            await self.acquire(estimated_tokens)
            async with self._semaphore:
                try:
                    if asyncio.iscoroutinefunction(fn):
                        return await fn(*args, **kwargs)
                    return await asyncio.to_thread(fn, *args, **kwargs)
                except Exception as exc:
                    # Bind to `last_error`, not `exc`: Python unbinds the
                    # `as` name when the except block exits, so reading `exc`
                    # below is a NameError on the first retry.
                    last_error = exc
                    if not _is_retryable(exc) or attempt == self.max_retries:
                        self.stats.failures += 1
                        raise
                    if _is_rate_limit(exc):
                        self.stats.rate_limited += 1
                    self.stats.retries += 1

            delay = _backoff_delay(attempt, last_error)
            logger.info(
                f"retry {attempt + 1}/{self.max_retries} after {delay:.1f}s: "
                f"{str(last_error)[:120]}"
            )
            await asyncio.sleep(delay)

        raise last_error  # unreachable; keeps the type checker honest


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "rate_limit" in text


def _is_retryable(exc: Exception) -> bool:
    """
    Retry throttling and transient transport faults only.

    A 400 from a bad request will fail identically every time; retrying it
    burns quota to reproduce a bug.
    """
    if _is_rate_limit(exc):
        return True
    text = str(exc).lower()
    return any(
        marker in text
        for marker in ("500", "502", "503", "504", "timeout", "timed out", "connection")
    )


def _retry_after(exc: Exception) -> Optional[float]:
    """
    Seconds the provider asked us to wait, if it said.

    Groq puts it in the message body ("Please try again in 7m31.008s"), which
    is worth parsing: the provider knows when the window reopens and guessing
    is strictly worse.
    """
    import re

    text = str(exc)
    match = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", text)
    if match:
        minutes = float(match.group(1) or 0)
        seconds = float(match.group(2))
        return minutes * 60 + seconds
    match = re.search(r"retry[- ]after[\"':\s]+([\d.]+)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


#: Cap on a single backoff sleep. Beyond this a run is better failed than
#: parked — a CI job blocked for ten minutes on a quota that resets tomorrow
#: has already failed, it just has not said so.
MAX_BACKOFF_SECONDS = 60.0


def _backoff_delay(attempt: int, exc: Exception) -> float:
    """Exponential backoff with full jitter, honouring Retry-After."""
    hinted = _retry_after(exc)
    if hinted is not None:
        return min(hinted, MAX_BACKOFF_SECONDS)
    # Full jitter (AWS): sleep = random(0, base * 2^attempt). Reduces the
    # thundering herd that fixed backoff creates when a whole queue retries in
    # lockstep.
    ceiling = min(MAX_BACKOFF_SECONDS, 1.0 * (2**attempt))
    return random.uniform(0, ceiling)


def estimate_tokens(text: str) -> int:
    """
    Rough token count for budgeting, without a tokenizer round trip.

    ~1 token per 4 ASCII chars, ~1 per CJK char. Deliberately an over-estimate:
    reserving too many tokens costs throughput, reserving too few costs a 429,
    and the second is more expensive.
    """
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    other = len(text) - cjk
    return int(cjk + other / 3.5) + 16
