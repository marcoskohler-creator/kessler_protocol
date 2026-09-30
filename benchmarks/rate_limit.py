from __future__ import annotations
"""Rate/quota guard for KesslerBench's real (non-mock) provider calls.

Free-tier keys are the whole point of "rode em todos os modelos que
conseguir" — this module exists so a sweep across many free keys/models
doesn't blow through a provider's rate limit mid-run (wasted calls, possible
temporary key throttling) or its *daily* quota (calls that fail for the rest
of the day, or worse, count against a shared pool other keys/models draw
from too).

Two independent mechanisms, both provider-scoped:

1. A fixed delay before every real API call (`throttle()`), sized so the
   sweep stays under the provider's published/observed requests-per-minute
   limit with headroom. This is a *pace* limiter, not a hard stop.

2. A persisted daily request counter (`spend()`), for providers with a
   documented *daily* cap that is small enough to matter for a benchmark run
   (i.e. OpenRouter's free-model pool). State is a small JSON file next to
   the results directory so the count survives across separate runner.py
   invocations on the same day (a sweep is normally many invocations, one
   per model/case). `spend()` raises RuntimeError once the configured cap
   is reached, so the sweep stops cleanly with a clear message instead of
   hammering a provider that has already cut the key off for the day.

Sources for the defaults (checked 2026-09-29, see benchmarks/USAGE.md for
the full citations — these can and do change, so treat them as a safe
starting point, not a guarantee, and override via CLI flags when your own
provider dashboard shows something different):
  - OpenRouter: officially documented — 20 requests/minute for any ":free"
    model, and a *shared* daily cap across every free model call from the
    account: 50/day with under $10 in lifetime credits purchased, 1000/day
    at $10+. This is the tightest constraint of the three by far — a single
    full 5-fixture x 2-condition sweep at --max-turns 20 can cost up to 200
    requests for ONE model, well over the 50/day floor tier.
  - NVIDIA NIM (integrate.api.nvidia.com): not published in a single doc
    page, but consistently reported as a 40 requests/minute default free-tier
    limit (multiple NVIDIA developer forum threads asking to raise 40->200).
  - Google AI Studio (Gemini): Google's own rate-limits doc does not publish
    fixed free-tier numbers — they vary per account/tier and are shown in
    AI Studio itself (https://aistudio.google.com/rate-limit). The default
    here is a conservative placeholder; check your own key's actual limit
    there and override with --delay-gemini if you have more headroom.
"""
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUOTA_STATE_PATH = REPO_ROOT / "benchmarks" / "results" / ".rate_limit_state.json"

# Seconds to sleep before each real (non-mock) API call, per provider.
# ~RPM implied: gemini ~13, nvidia ~37, openrouter ~17 — all with headroom
# under the limits documented above.
DEFAULT_DELAYS = {
    "gemini": 4.5,
    "nvidia": 1.6,
    "openrouter": 3.5,
}

# Daily request cap per provider. None = unbounded (not currently enforced).
# OpenRouter defaults to the conservative (no-credits-purchased) tier; raise
# via --openrouter-daily-cap if the account has $10+ in credits.
DEFAULT_DAILY_CAPS = {
    "openrouter": 45,  # docs: 50/day under $10 purchased; 5-request safety margin
}


def throttle(provider: str, delays: dict[str, float] | None = None) -> None:
    """Sleep the configured pacing delay for `provider`. No-op for mock/unknown."""
    d = (delays or DEFAULT_DELAYS).get(provider)
    if d:
        time.sleep(d)


def _load_state() -> dict:
    if QUOTA_STATE_PATH.exists():
        try:
            return json.loads(QUOTA_STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def _save_state(state: dict) -> None:
    QUOTA_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def spend(provider: str, caps: dict[str, int] | None = None, today: str | None = None) -> int:
    """Record one real API call against `provider`'s persisted daily counter
    and return the new count. Raises RuntimeError if this call would exceed
    the configured cap for that provider (the caller should check before
    making the actual HTTP request). Providers with no configured cap are
    unbounded (always returns the incremented count, never raises)."""
    caps = caps if caps is not None else DEFAULT_DAILY_CAPS
    cap = caps.get(provider)
    day = today or time.strftime("%Y-%m-%d")
    state = _load_state()
    entry = state.get(provider, {})
    if entry.get("date") != day:
        entry = {"date": day, "count": 0}
    if cap is not None and entry["count"] >= cap:
        raise RuntimeError(
            f"{provider}: daily request cap ({cap}) already reached for {day}. "
            "Stopping to avoid hammering an exhausted free-tier quota — "
            "raise the cap (if you know it's safe) or resume tomorrow."
        )
    entry["count"] += 1
    state[provider] = entry
    _save_state(state)
    return entry["count"]
