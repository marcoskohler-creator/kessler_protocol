from __future__ import annotations
"""KesslerBench sweep: run every fixture against every model in a manifest,
both conditions, and print/write one aggregate table.

This is the "rode em todos os modelos que conseguir me dando o resultado em
cada um deles" entry point: one command, many (provider, model) combos, one
summary at the end instead of one runner.py invocation per model.

Usage (run on a machine with real network access to the providers, never in
this project's own dev/CI sandbox):

    python benchmarks/sweep.py --manifest benchmarks/models.example.json \\
        --out benchmarks/results/sweep-$(date +%Y%m%d-%H%M%S)

Manifest format (JSON, a list): each entry is
    {"provider": "gemini", "model": "gemini-2.5-flash-lite", "api_key_env": "KB_GEMINI_KEY_NOVA1"}
`api_key_env` names an environment variable already exported in your shell —
sweep.py reads the key from the environment, never from the manifest file
itself, so the manifest (and this repo) never has to contain a real key.

    export KB_GEMINI_KEY_NOVA1="..."   # from your own key catalog, not committed anywhere
    python benchmarks/sweep.py --manifest my_models.json

Any entry whose api_key_env isn't set in the environment is skipped with a
warning, not a hard failure, so one missing/expired key doesn't kill the
whole sweep.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner  # noqa: E402
from runner import run_case  # noqa: E402
import rate_limit  # noqa: E402

CASES_FILE = REPO_ROOT / "benchmarks" / "cases.json"


def load_case_ids() -> list[str]:
    return [c["id"] for c in json.loads(CASES_FILE.read_text())["cases"]]


def main():
    ap = argparse.ArgumentParser(description="KesslerBench sweep across a manifest of models")
    ap.add_argument("--manifest", required=True, help="JSON file: list of {provider, model, api_key_env}")
    ap.add_argument("--case", default="all", help="single case id, or 'all' (default)")
    ap.add_argument("--condition", default="both", choices=["both", "with_kessler", "baseline"])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out", default=str(REPO_ROOT / "benchmarks" / "results" / f"sweep-{time.strftime('%Y%m%d-%H%M%S')}"))
    ap.add_argument("--max-turns", type=int, default=runner.DEFAULT_MAX_TURNS)
    ap.add_argument("--delay-gemini", type=float, default=rate_limit.DEFAULT_DELAYS["gemini"])
    ap.add_argument("--delay-nvidia", type=float, default=rate_limit.DEFAULT_DELAYS["nvidia"])
    ap.add_argument("--delay-openrouter", type=float, default=rate_limit.DEFAULT_DELAYS["openrouter"])
    ap.add_argument("--openrouter-daily-cap", type=int, default=rate_limit.DEFAULT_DAILY_CAPS["openrouter"],
                     help="shared across ALL ':free' OpenRouter models on the account, not per-model — see rate_limit.py")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    case_ids = load_case_ids() if args.case == "all" else [c.strip() for c in args.case.split(",") if c.strip()]
    results_root = Path(args.out).resolve()
    results_root.mkdir(parents=True, exist_ok=True)
    delays = {"gemini": args.delay_gemini, "nvidia": args.delay_nvidia, "openrouter": args.delay_openrouter}
    daily_caps = {"openrouter": args.openrouter_daily_cap}
    exhausted_providers: set[str] = set()

    summary_rows = []
    for entry in manifest:
        provider, model, key_env = entry["provider"], entry["model"], entry["api_key_env"]
        api_key = os.environ.get(key_env, "")
        if not api_key:
            print(f"[skip] {provider}/{model}: ${key_env} is not set in the environment", file=sys.stderr)
            continue
        if provider in exhausted_providers:
            print(f"[skip] {provider}/{model}: daily quota already exhausted earlier in this sweep", file=sys.stderr)
            continue
        for cid in case_ids:
            try:
                records = run_case(cid, provider, model, api_key, args.condition, args.runs, results_root,
                                    max_turns=args.max_turns, delays=delays, daily_caps=daily_caps)
            except RuntimeError as exc:
                if "daily request cap" in str(exc):
                    print(f"[quota] {provider}: {exc} — skipping remaining {provider} entries for the rest of this sweep.", file=sys.stderr)
                    exhausted_providers.add(provider)
                    summary_rows.append({"provider": provider, "model": model, "case": cid, "condition": "QUOTA_EXHAUSTED", "acceptance_success": False, "error": str(exc)})
                    break
                print(f"[error] {provider}/{model} case={cid}: {exc!r}", file=sys.stderr)
                summary_rows.append({"provider": provider, "model": model, "case": cid, "condition": "ERROR", "acceptance_success": False, "error": str(exc)})
                continue
            except Exception as exc:
                print(f"[error] {provider}/{model} case={cid}: {exc!r}", file=sys.stderr)
                summary_rows.append({"provider": provider, "model": model, "case": cid, "condition": "ERROR", "acceptance_success": False, "error": str(exc)})
                continue
            for r in records:
                summary_rows.append({
                    "provider": provider, "model": model, "case": cid, "condition": r["condition"],
                    "acceptance_success": r["scoring"]["acceptance_success"],
                    "security_regressions": r["scoring"]["security_regressions"],
                    "fake_success_incidents": r["scoring"]["fake_success_incidents"],
                    "kessler_denials": r["scoring"]["kessler_denials"],
                })

    summary_path = results_root / "summary.json"
    summary_path.write_text(json.dumps(summary_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== KesslerBench sweep summary ===")
    header = f"{'provider/model':<32} {'case':<24} {'cond':<13} {'pass':<5} {'sec_reg':<8} {'fake_ok':<8} {'denials'}"
    print(header)
    for row in summary_rows:
        pm = f"{row['provider']}/{row['model']}"
        print(f"{pm:<32} {row['case']:<24} {row['condition']:<13} "
              f"{'YES' if row.get('acceptance_success') else 'no':<5} "
              f"{row.get('security_regressions', '-'):<8} {row.get('fake_success_incidents', '-'):<8} {row.get('kessler_denials', '-')}")
    print(f"\nFull results + per-run transcripts under: {results_root}")
    print(f"Machine-readable summary: {summary_path}")


if __name__ == "__main__":
    main()
