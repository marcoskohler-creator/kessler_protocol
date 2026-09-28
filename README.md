# The Kessler Protocol

**A deterministic, risk-proportional safety and evidence layer for agentic coding assistants.**

> A coding agent should not need thousands of prompt tokens to remember that destructive commands are destructive, failed tests are failures, or unverified work is not verified work.

Kessler moves those decisions **out of the prompt** and into a local policy runtime. The model only receives context when an intervention is relevant.

## What Kessler changes

Kessler uses a small always-on invariant layer plus executable engines instead of injecting a large rulebook into every turn:

- **Project Profiler** — detects stack, architecture signals, verification commands and risk automatically.
- **Risk Engine** — classifies the project and selects proportional strictness.
- **Policy Engine** — evaluates policies locally and lazily.
- **Evidence Engine** — records reads, searches, writes and interventions.
- **Verification Engine** — distinguishes test/build/typecheck/lint execution, success and relevance.
- **State Engine** — keeps session evidence atomically with lock protection.
- **Decision Engine** — maps a policy to the capabilities of each agent harness.
- **Audit Report** — reports residual risk and verification confidence.

### Token budget

`kessler budget` measures the static context footprint. In this release, the repository's current approximate budget is:

- always-on Kessler core: **~159 tokens**;
- skill discovery description: **~50 tokens**;
- full skill: lazy, loaded only when relevant;
- full policy catalog: **0 prompt tokens** until a policy fires.

The approximation uses characters/4 for regression budgeting; it is not a billing tokenizer.

## Supported adapters

| Harness | Status | Enforcement |
|---|---|---|
| Google Antigravity 2.0 / IDE | Implemented | native plugin hooks |
| Antigravity CLI | Implemented | plugin hooks; separate global path |
| Gemini CLI | Implemented | `settings.json` hooks |
| Claude Code | Planned | not claimed as supported |
| Codex | Planned | not claimed as supported |
| Cursor | Planned | not claimed as supported |

Implementation has automated synthetic coverage. A release can still require live smoke certification against the exact installed harness versions before being labeled operationally certified.

## Install

Python 3.11+ is required.

```bash
python -m pip install .
```

Initialize a project:

```bash
kessler init
kessler profile
kessler budget
```

Install for Antigravity IDE/2.0 globally:

```bash
kessler install --target antigravity --scope user --surface ide
```

Install for Antigravity CLI globally:

```bash
kessler install --target antigravity --scope user --surface cli
```

Install at workspace scope:

```bash
kessler install --target antigravity --scope workspace --workspace .
```

Gemini CLI:

```bash
kessler install --target gemini --scope user
```

Verify the installation by executing the installed runtime, not merely checking files:

```bash
kessler doctor --target antigravity --surface ide --deep
kessler doctor --target gemini --deep
```

## Automatic project configuration

The human-owned `.kessler.toml` is intentionally small:

```toml
version = 1
strictness = "auto"
context = "lean"
```

Kessler generates `.kessler/cache/project-profile.json` from deterministic project discovery. It can detect common languages/frameworks, database/auth/payment/migration/infrastructure signals and executable verification commands.

Manual project configuration always overrides detected values.

## Risk-proportional enforcement

Auto strictness maps project risk to behavior:

| Project risk | Default strictness |
|---|---|
| LOW | balanced |
| MODERATE | balanced |
| HIGH | strict |
| CRITICAL | paranoid |

A static landing page should not receive the same friction as a project containing authentication, payments, schema migrations and sensitive data signals.

## Zero-token enforcement

Kessler follows one architectural rule:

> **If a policy can be enforced deterministically, it must not consume LLM context.**

Examples handled locally:

- catastrophic shell patterns;
- destructive Git/filesystem/database commands;
- sensitive-path writes;
- successful vs failed verification;
- whether verification happened after the latest write;
- project fingerprint/cache invalidation;
- evidence state and installation rollback.

Only a compact KES policy message is surfaced when action is required.

## Verification is evidence, not command recognition

Kessler stores:

- command;
- verification kind;
- success/failure;
- relevance against detected project commands;
- execution time relative to the last write.

A failed `pytest`, `npm test`, build, lint or typecheck **does not** satisfy the completion gate.

## Explainable policies

```bash
kessler explain KES-VER-001
```

Every policy has an ID, severity, trigger type, deterministic action, explanation and remediation.

## Session report

```bash
kessler report
```

Reports project risk, files modified, sensitive writes, read/search evidence, interventions, verification completeness, residual risk and a bounded completion-confidence score.

If executable verification is genuinely unavailable, the human can document that decision:

```bash
kessler waive --reason "Vendor sandbox unavailable; change limited to generated fixture and reviewed manually."
```

A subsequent source write clears the waiver.

## Safe install, uninstall and rollback

Kessler does not overwrite `GEMINI.md` or arbitrary global rules. Installation manifests record Kessler-owned mutations and backups. Uninstall removes Kessler hooks selectively and can restore a previous Kessler installation without replacing unrelated changes made later by the user.

```bash
kessler uninstall --target gemini
kessler rollback --target antigravity --surface ide
```

## KesslerBench

`benchmarks/` defines the reproducibility contract for comparing the same coding tasks **with and without** Kessler. The benchmark is designed to measure both benefit and cost: task success, security regressions, fake-success behavior, verification quality, false interventions, tool calls, latency and token overhead.

No benchmark result is claimed until the fixtures, run counts, harness/model versions and raw scoring evidence are published.

## Open-source maintenance

Kessler is MIT licensed and welcomes scoped, evidence-backed contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development and review rules, [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance, and [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for the current support boundary. The CI matrix and KesslerBench methodology are public so maintainers and users can reproduce claims. Adoption, benchmark outcomes, and live harness certification are reported only when there is evidence.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
kessler doctor --target package --deep
python tools/build_integrations.py
```

CI runs on Linux, macOS and Windows with Python 3.11 and 3.13 and verifies that the vendored Antigravity runtime remains generated from the canonical source tree.

## Documentation

- `KESSLER_FINAL_IMPLEMENTATION_SPEC.md` — complete implementation architecture and decision record.
- `docs/ARCHITECTURE.md` — compact architecture reference.
- `docs/POLICY_REFERENCE.md` — policy model and IDs.
- `docs/COMPATIBILITY.md` — supported harnesses and limitations.
- `benchmarks/README.md` — KesslerBench methodology.

## License

MIT.
