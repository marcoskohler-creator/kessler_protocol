# KesslerBench — running it

This complements `README.md` (methodology/required-reporting spec) with the
concrete "how do I actually run this" instructions for the runner/scorer/
fixtures implementation.

It is **not** a simulation of Kessler. `runner.py` calls the exact same
`hook_runtime.run("gemini", event, payload)` entry point the installed Gemini
adapter calls, with the same payload shape. The only thing scripted is the
model-facing tool loop (read_file/write_file/search_files/list_dir/
run_shell_command/task_complete), standing in for a real harness UI.

## Two sources of truth (see `scorer.py`'s docstring)

1. Each fixture's own `check.py` — case-specific acceptance/security checks,
   run in a subprocess against the post-episode workspace.
2. Kessler's own session state (`kessler_protocol.state.load`) — the same
   reads/searches/writes/verifications/interventions audit trail
   `kessler report` prints, read straight from Kessler, not re-derived.

## Fixtures

| case | what it tests |
|---|---|
| `cross-module-refactor` | multi-file rename correctness |
| `authz-regression` | does the agent silently weaken an authorization check while adding a feature |
| `fake-api-integration` | does the agent claim an integration is done while leaving a stub (fake success) |
| `db-migration` | additive, backward-compatible schema change vs. a destructive one |
| `destructive-git` | fixing a broken commit while preserving uncommitted WIP, without an unapproved destructive git command |

Each fixture is a real small repo under `fixtures/<case>/repo/`, plus
`prompt.txt` (the task given to the model) and `check.py` (the acceptance
check: `check.py <workspace>` prints one JSON line —
`{"acceptance_success", "security_regressions", "details"}`).

## Running it for real

This project's own dev/CI sandbox cannot reach any LLM provider's API
(network egress there is locked to package registries only) — by design in
that environment, not a bug in the benchmark. Run it from a machine with
normal internet access, with your own API key:

```bash
python benchmarks/runner.py \
  --case authz-regression \
  --provider gemini --model gemini-2.5-flash-lite \
  --api-key "$YOUR_KEY" \
  --condition both --runs 1
```

`--case all` runs every fixture. `--condition both` runs `with_kessler`
(every tool call gated by Kessler) and `baseline` (no Kessler at all, raw
execution) back to back, for a direct before/after comparison per model.

Supported `--provider` values: `gemini` (Google Generative Language REST
API), `nvidia` and `openrouter` (both OpenAI-compatible `/chat/completions`).
Pass whichever model id your key has access to via `--model`.

**Never commit an API key.** Pass it as `--api-key` on the command line
(from your shell env, not a file in this repo) or export it as an env var
and reference that: `--api-key "$KB_GEMINI_KEY_1"`.

Results land under
`benchmarks/results/<timestamp>/<case>/<provider>-<model>/<condition>/run-N/`
— `result.json` (metrics + scoring), `transcript.json` (full tool-call
trace), and (for `with_kessler`) Kessler's own session state.

## Offline plumbing check (no network, no API key)

```bash
python benchmarks/runner.py --case all --provider mock --model mock \
  --api-key '[{"tool_calls":[{"name":"list_dir","args":{"directory_path":"."}}]},{"tool_calls":[{"name":"task_complete","args":{"summary":"smoke test"}}]}]' \
  --condition both --runs 1 --out /tmp/kb_smoke
```

`--provider mock` repurposes `--api-key` as an inline JSON script (a list of
`{"tool_calls": [{"name", "args"}]}` steps) consumed one per model turn by
`MockClient` — no network call, no real model. Useful to prove the hook
wiring and scoring pipeline still work after changing `runner.py`/
`scorer.py`, before spending a real API call. This has been run for all 5
fixtures, both conditions, with a solve-attempt script for
`cross-module-refactor` (Kessler's Planning Gate correctly denied unplanned
writes, proving real enforcement — see caveat below) and a plumbing-only
script for the rest (proves no crashes, valid JSON, real `check.py`
execution — not a claim of a real solve).

## Agents need to register a plan first (solved via priming, not a caveat anymore)

Kessler's Planning Gate (`KES-PLAN-001/002`) blocks mutating tool calls
(`write_file`, `run_shell_command`, and anything else whose tool name looks
like write/edit/replace/patch — see `kessler_protocol.planning.plan_decision`)
until a plan is registered for the session; read-only tools (`read_file`,
`list_dir`, `search_files`) are never gated by it. `runner.py`'s
`with_kessler` system prompt includes `KESSLER_PRIMING`, adapted from the
real `GEMINI_SKILL` text an actual Kessler-Gemini install injects, so a
scripted model knows the protocol going in — this was confirmed against real
transcripts to reliably produce a correct, well-formed plan write on the
first or second attempt, not endless denied shell retries.

`--max-turns` (default 20, was 12) exists because even with a fast plan
handshake, an "implement a feature + run tests + fix + retest" task needs
real room beyond just negotiating the gate — `authz-regression` in
particular was timing out mid-implementation, in *both* conditions, at the
old 12-turn budget.

## Rate limits and daily quotas — you're spending real free-tier request budget

Every real (non-mock) API call now goes through `benchmarks/rate_limit.py`:
a fixed per-provider delay before each call (`--delay-gemini/-nvidia/-openrouter`),
plus a persisted daily request counter for OpenRouter specifically
(`--openrouter-daily-cap`, state in `benchmarks/results/.rate_limit_state.json`).
**Read `rate_limit.py`'s module docstring for the full numbers and sources**
(checked 2026-09-29) — the short version:

- **OpenRouter free (`:free`) models: 20 requests/minute, and a daily cap
  SHARED across every free model your account calls — 50/day under $10 in
  lifetime credits purchased, 1000/day at $10+.** This is the tightest
  constraint by far: one full 5-fixture x 2-condition sweep at `--max-turns
  20` can cost up to 200 requests for a *single* model — well over the
  50/day floor tier. Budget accordingly: test 1-2 OpenRouter models, not a
  wide sweep, unless the account has $10+ in credits. `sweep.py` stops
  cleanly (skips remaining OpenRouter entries, keeps going on other
  providers) once the configured cap is hit mid-run, rather than continuing
  to fail against an exhausted key.
- **NVIDIA NIM: commonly reported 40 requests/minute default** (not in a
  single official doc page, but consistent across several NVIDIA developer
  forum threads asking for a 40→200 increase). No published daily cap found.
- **Gemini/AI Studio: no fixed free-tier number in Google's own docs** —
  it varies per account/tier and is shown at
  https://aistudio.google.com/rate-limit. `--delay-gemini` defaults to a
  conservative placeholder; check your own key there and loosen it if you
  have more headroom.

## Discovering which models are actually available: `discover_models.py`

Rather than hand-maintaining a manifest with placeholder model ids, ask each
provider what your keys can actually see, right now:

```bash
export KB_GEMINI_KEY_NOVA1="..."
export KB_NVIDIA_KEY="..."
export KB_OPENROUTER_KEY="..."
python benchmarks/discover_models.py \
  --gemini-keys KB_GEMINI_KEY_NOVA1,KB_GEMINI_KEY_NOVA2 \
  --nvidia-key KB_NVIDIA_KEY \
  --openrouter-key KB_OPENROUTER_KEY \
  --out benchmarks/models.discovered.json
```

This queries each provider's own list-models endpoint (Gemini's `ListModels`,
NVIDIA NIM's and OpenRouter's OpenAI-shaped `/v1/models`), filters to what's
actually callable (Gemini: `generateContent` support, flash/flash-lite
preferred; OpenRouter: **strictly zero-priced** models only — pricing is the
source of truth for "free", not just the `:free` suffix), round-robins
discovered Gemini models across every `--gemini-keys` entry given (spreads
request load across your keys instead of hammering one), and writes a
manifest in exactly the shape `sweep.py --manifest` expects. See
`discover_models.py`'s module docstring for the full per-provider rationale
and the `--max-per-provider`/`--max-openrouter` caps (OpenRouter defaults to
2, for the daily-quota reason above). Its three filter functions
(`gemini_model_ids`/`nvidia_model_ids`/`openrouter_free_model_ids`) are pure
and unit-tested offline against synthetic responses matching each API's real
shape — this sandbox cannot reach any of these APIs for a live check, so
that's the extent of verification possible from here; the actual HTTP calls
need to run on a machine with real network access, same as `runner.py`.

## Running across "all the models you can": `sweep.py`

```bash
python benchmarks/sweep.py --manifest benchmarks/models.discovered.json
```

Runs every fixture against every `(provider, model, api_key_env)` entry in
the manifest, both conditions, and writes one aggregate `summary.json`
alongside the per-run `result.json`/`transcript.json` files `runner.py`
already produces. Accepts the same `--max-turns`/`--delay-*`/
`--openrouter-daily-cap` flags as `runner.py`, applied uniformly across the
whole sweep. Any manifest entry whose `api_key_env` isn't set in the
environment is skipped with a warning, not a hard failure — one missing or
expired key doesn't kill the whole sweep, and neither does one provider's
daily quota running out partway through (the sweep just stops calling that
provider and keeps going on the others).
