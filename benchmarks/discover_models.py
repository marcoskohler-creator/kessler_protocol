from __future__ import annotations
"""KesslerBench model discovery: before a sweep, ask each provider what
models are actually available to your keys right now, instead of hand-
maintaining a manifest with placeholder ids (models.example.json used to
ship "REPLACE_WITH_A_FREE_NIM_MODEL_ID" for exactly this reason).

Run on a machine with real network access (this sandbox cannot reach any of
these APIs):

    export KB_GEMINI_KEY_NOVA1="..."
    export KB_GEMINI_KEY_NOVA2="..."
    export KB_NVIDIA_KEY="..."
    export KB_OPENROUTER_KEY="..."
    python benchmarks/discover_models.py \\
        --gemini-keys KB_GEMINI_KEY_NOVA1,KB_GEMINI_KEY_NOVA2 \\
        --nvidia-key KB_NVIDIA_KEY \\
        --openrouter-key KB_OPENROUTER_KEY \\
        --out benchmarks/models.discovered.json

The output is a manifest in the exact shape sweep.py's --manifest expects:
[{"provider", "model", "api_key_env"}, ...] — feed it straight in:

    python benchmarks/sweep.py --manifest benchmarks/models.discovered.json

What "available" means per provider (see rate_limit.py's docstring for the
full rate/quota citations):
  - Gemini (Google AI Studio): every model your key's ListModels call
    returns that supports generateContent. A free AI Studio key sees the
    same catalog as a paid one — the free/paid distinction is about rate
    limits, not which models are visible — so this is "what your key can
    call", sorted to prefer flash/flash-lite (cheaper, looser free-tier
    limits) over pro/preview models. When multiple --gemini-keys are given,
    discovered models are round-robin assigned across them, so a sweep
    spreads its request load over all your keys instead of hammering one.
  - NVIDIA NIM: every model id integrate.api.nvidia.com/v1/models returns
    for your key, EXCEPT entries in _NVIDIA_KNOWN_PAID_ONLY (checked
    2026-09/10: openai/gpt-oss-120b's NIM free-trial endpoint was
    deprecated — only a paid "partner endpoint" remains; NIM's own
    /v1/models listing doesn't distinguish this, so it's a hand-maintained
    denylist, not derived from the API response). openai/gpt-oss-20b DOES
    still have a free-trial NIM endpoint and is sorted first via
    _NVIDIA_PREFERRED. NIM's "free" tier is trial credits (~1,000, up to
    5,000 via promos), not unlimited — see rate_limit.py. --max-per-provider
    caps how many go into the output manifest (default 6) so a sweep stays
    a reasonable size. Pass --nvidia-include-paid-only to keep denylisted
    models in (e.g. to deliberately test a paid endpoint with a funded key).
  - OpenRouter: ONLY models whose pricing is strictly zero (prompt and
    completion both "0") — i.e. genuinely free, not just cheap. OpenRouter's
    free-model rate/quota is small and SHARED across every ":free" model on
    the account (see rate_limit.py) — --max-per-provider defaults to 2 here
    specifically because testing many free OpenRouter models in one sweep
    can exhaust the whole day's shared quota on discovery alone.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models?key={key}"
NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Preference order for Gemini models: flash-lite / flash first (looser free
# limits, cheaper), pro/preview last. Pure string heuristic on the model id.
_GEMINI_RANK = ["flash-lite", "flash", "pro"]

# NVIDIA NIM: hand-maintained, checked 2026-09/10 (see discover_nvidia's
# docstring above for why this can't be derived from the API response).
# gpt-oss-20b still has a free NIM trial endpoint; gpt-oss-120b's was
# deprecated to a paid-only "partner endpoint".
_NVIDIA_PREFERRED = ["gpt-oss-20b"]
_NVIDIA_KNOWN_PAID_ONLY = ["gpt-oss-120b"]


def _http_get_json(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body[:1000]}") from None


def _gemini_rank(model_id: str) -> tuple:
    lower = model_id.lower()
    for i, tag in enumerate(_GEMINI_RANK):
        if tag in lower:
            return (i, model_id)
    return (len(_GEMINI_RANK), model_id)


def gemini_model_ids(raw: dict) -> list[str]:
    """Pure filter, testable without network: model ids (without the
    'models/' prefix) that support generateContent, sorted flash-lite-first."""
    out = []
    for m in raw.get("models", []):
        name = m.get("name", "")
        if "generateContent" in (m.get("supportedGenerationMethods") or []):
            out.append(name.split("/", 1)[-1] if name.startswith("models/") else name)
    return sorted(dict.fromkeys(out), key=_gemini_rank)


def nvidia_model_ids(raw: dict, include_paid_only: bool = False) -> list[str]:
    """Pure filter: every model id NIM's /v1/models (OpenAI-shaped) lists,
    minus _NVIDIA_KNOWN_PAID_ONLY entries unless include_paid_only=True,
    with _NVIDIA_PREFERRED (confirmed-free) models sorted first. Sort is
    stable, so original catalog order is preserved within each group."""
    ids = [m["id"] for m in raw.get("data", []) if m.get("id")]
    if not include_paid_only:
        ids = [i for i in ids if not any(p in i.lower() for p in _NVIDIA_KNOWN_PAID_ONLY)]

    def _rank(model_id: str) -> int:
        lower = model_id.lower()
        return 0 if any(p in lower for p in _NVIDIA_PREFERRED) else 1

    return sorted(ids, key=_rank)


def openrouter_free_model_ids(raw: dict) -> list[str]:
    """Pure filter: only models with strictly zero prompt AND completion
    pricing — genuinely free, not merely cheap. (Most also carry a ':free'
    id suffix, but pricing is the authoritative signal.)"""
    out = []
    for m in raw.get("data", []):
        pricing = m.get("pricing") or {}
        if str(pricing.get("prompt", "")) == "0" and str(pricing.get("completion", "")) == "0":
            out.append(m["id"])
    return out


def discover_gemini(key_env: str) -> list[str]:
    key = os.environ.get(key_env, "")
    if not key:
        print(f"[skip] gemini: ${key_env} not set", file=sys.stderr)
        return []
    raw = _http_get_json(GEMINI_MODELS_URL.format(key=key))
    return gemini_model_ids(raw)


def discover_nvidia(key_env: str, include_paid_only: bool = False) -> list[str]:
    key = os.environ.get(key_env, "")
    if not key:
        print(f"[skip] nvidia: ${key_env} not set", file=sys.stderr)
        return []
    raw = _http_get_json(NVIDIA_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
    return nvidia_model_ids(raw, include_paid_only=include_paid_only)


def discover_openrouter(key_env: str) -> list[str]:
    key = os.environ.get(key_env, "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    raw = _http_get_json(OPENROUTER_MODELS_URL, headers=headers)
    return openrouter_free_model_ids(raw)


def main():
    ap = argparse.ArgumentParser(description="Discover which models are actually available for KesslerBench's free keys")
    ap.add_argument("--gemini-keys", default="", help="comma-separated env var names holding Gemini/AI Studio API keys")
    ap.add_argument("--nvidia-key", default="", help="env var name holding an NVIDIA NIM API key")
    ap.add_argument("--nvidia-include-paid-only", action="store_true",
                     help="keep NIM models in _NVIDIA_KNOWN_PAID_ONLY (e.g. gpt-oss-120b, whose free trial "
                          "endpoint is deprecated) instead of skipping them — only useful with a funded key")
    ap.add_argument("--openrouter-key", default="", help="env var name holding an OpenRouter API key")
    ap.add_argument("--max-per-provider", type=int, default=6, help="cap on discovered gemini/nvidia models kept (default 6)")
    ap.add_argument("--max-openrouter", type=int, default=2,
                     help="cap on discovered OpenRouter free models kept (default 2 — its free-model quota is tiny "
                          "and SHARED across every ':free' model on the account, see rate_limit.py)")
    ap.add_argument("--out", default=str(REPO_ROOT / "benchmarks" / "models.discovered.json"))
    args = ap.parse_args()

    manifest = []

    gemini_key_envs = [e.strip() for e in args.gemini_keys.split(",") if e.strip()]
    if gemini_key_envs:
        # Enumerate the catalog once (first working key — the catalog is the
        # same across keys on the same API), then round-robin assign the
        # discovered models across ALL given keys so a sweep spreads its
        # request load instead of hammering one key.
        models: list[str] = []
        for key_env in gemini_key_envs:
            try:
                models = discover_gemini(key_env)
                if models:
                    break
            except RuntimeError as exc:
                print(f"[error] gemini/{key_env}: {exc}", file=sys.stderr)
        models = models[: args.max_per_provider]
        for i, model in enumerate(models):
            manifest.append({"provider": "gemini", "model": model, "api_key_env": gemini_key_envs[i % len(gemini_key_envs)]})
        print(f"[gemini] {len(models)} model(s) x {len(gemini_key_envs)} key(s): {models}", file=sys.stderr)

    if args.nvidia_key:
        try:
            models = discover_nvidia(args.nvidia_key, include_paid_only=args.nvidia_include_paid_only)[: args.max_per_provider]
        except RuntimeError as exc:
            print(f"[error] nvidia: {exc}", file=sys.stderr)
            models = []
        for model in models:
            manifest.append({"provider": "nvidia", "model": model, "api_key_env": args.nvidia_key})
        print(f"[nvidia] {len(models)} model(s): {models}", file=sys.stderr)

    if args.openrouter_key:
        try:
            models = discover_openrouter(args.openrouter_key)[: args.max_openrouter]
        except RuntimeError as exc:
            print(f"[error] openrouter: {exc}", file=sys.stderr)
            models = []
        for model in models:
            manifest.append({"provider": "openrouter", "model": model, "api_key_env": args.openrouter_key})
        print(f"[openrouter] {len(models)} model(s) (capped at {args.max_openrouter} — shared daily quota, see rate_limit.py): {models}", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(manifest)} (provider, model, key) entries written to {out_path}")
    print(f"Next: python benchmarks/sweep.py --manifest {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
