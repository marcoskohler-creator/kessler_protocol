# Kessler Protocol

**Deterministic, risk-proportional safety and evidence layer for agentic coding assistants.**

> A coding agent should not need thousands of prompt tokens to remember that destructive commands are destructive, failed tests are failures, or unverified work is not verified work.

Kessler moves safety, planning, and verification decisions **out of the prompt** and into a local, deterministic policy runtime. The model only receives context when an intervention is relevant.

---

## What Kessler solves

Coding assistants frequently suffer from failure modes that compound during autonomous execution:
- Modifying files before understanding dependencies;
- Presenting mock data or placeholder code as production integration;
- Executing destructive repository or filesystem operations;
- Fabricating risks or claims under prompt coercion;
- Declaring victory after test commands that actually failed;
- Consuming enormous system prompt token budgets with redundant rule sets.

Kessler solves this with a **zero-token local control plane**:

- **Project Profiler** — automatically scans the project structure, stack, signals (auth, payments, migrations, secrets), and verification commands.
- **Risk Engine** — scores project and change risk to apply proportional strictness (`balanced`, `strict`, `paranoid`).
- **Planning Gate (`KES-PLAN-001` / `KES-PLAN-002`)** — blocks tool execution until a concrete, evidence-backed implementation plan is registered.
- **Future Risks Engine** — requires at least two substantive future risks to force agents to evaluate secondary failure modes before modifying code.
- **UI Platform Design Standards** — enforces deterministic standards (`touch_target_pt >= 44`, `contrast_ratio >= 4.5`, `supports_dynamic_type: true`, `respects_reduced_motion: true`, 2+ responsive breakpoints) on every UI plan.
- **Anti-Gaming Shield** — blocks plans labeled `non_ui` from secretly editing UI-surface files (`.tsx`, `.jsx`, `.vue`, `.html`, `.css`, etc.) without an explicit, documented `non_ui_override_reason`.
- **Evidence Engine (`KES-READ-001`)** — rejects discovery claims without real file read evidence recorded in the session.
- **Verification Engine (`KES-VER-001`)** — inspects exit codes, test failures, and mandates automated accessibility/design tooling (`axe`, `pa11y`, `lighthouse`, `test:a11y`) for UI changes when available.
- **Policy Engine** — evaluates local policies lazily with zero static prompt consumption until triggered.
- **State Engine** — preserves session evidence and history atomically with cross-process locking.
- **Audit & Session Reports** — outputs residual risk, verification confidence scores, and auditable evidence logs.

---

## Token budget: Zero-token enforcement

Kessler follows a core architectural invariant:

> **If a policy can be enforced deterministically, it must not consume LLM context.**

`kessler budget` measures the static context footprint:

- **Always-on Kessler core:** ~214 approximate tokens;
- **Skill discovery description:** ~50 tokens;
- **Full skill:** lazy, loaded only when relevant;
- **Policy catalog:** **0 prompt tokens** when inactive.

---

## Supported agent harnesses

| Harness | Status | Integration mechanism |
|---|---|---|
| Google Antigravity (IDE & Agent) | Fully Certified | Native plugin hooks (`PreToolUse`, `PostToolUse`, `Stop`) |
| Google Antigravity CLI | Fully Certified | Plugin hooks with dedicated CLI global path |
| Gemini CLI | Fully Certified | Hook integration via `settings.json` |
| Anthropic Claude Code | Fully Certified | Native hook handlers (`PreToolUse`, `Stop`, `UserPromptSubmit`) |

---

## Installation & Setup

Python 3.11+ is required.

```bash
python -m pip install .
```

Initialize and profile a repository:

```bash
kessler init
kessler profile
kessler budget
```

### Install into Agent Environments

**Google Antigravity IDE:**
```bash
kessler install --target antigravity --scope user --surface ide
```

**Google Antigravity CLI:**
```bash
kessler install --target antigravity --scope user --surface cli
```

**Anthropic Claude Code:**
```bash
kessler install --target claude_code --scope user
```

**Gemini CLI:**
```bash
kessler install --target gemini --scope user
```

### Verify Installation Health

Verify the live executable runtime across environments:

```bash
kessler doctor --target antigravity --surface ide --deep
kessler doctor --target claude_code --deep
kessler doctor --target gemini --deep
```

---

## Automatic project profiling & configuration

The human-maintained `.kessler.toml` is intentionally minimal:

```toml
version = 1
strictness = "auto"
context = "lean"
```

Kessler automatically generates `.kessler/cache/project-profile.json` by inspecting dependencies, frameworks, databases, authentication, payments, and CI workflows. Manual configuration always overrides automatic detection.

### Proportional Strictness

| Project risk level | Default strictness | Behavior |
|---|---|---|
| LOW | balanced | Frictionless for simple utility or documentation tasks |
| MODERATE | balanced | Standard discovery and verification requirements |
| HIGH | strict | Escalated verification and mandatory multi-risk planning |
| CRITICAL | paranoid | Strict confirmation on sensitive boundaries and operations |

---

## Methodical Planning Gate

Before modifying project files, Kessler requires an evidence-based implementation plan written to `.kessler/cache/implementation-plan.json`:

1. **Goal & Purpose:** Specific rationale and target outcome.
2. **Justification & Future Risks:** Requires **at least 2 concrete future risks** (8+ characters, no placeholders) forcing the agent to reason through secondary effects and trade-offs.
3. **Usage Flow & Interface:**
   - **UI Mode:** Explicit sequence of actions, navigation, controls (with `evidence_path`), 3+ states, accessibility statement, and mandatory **Platform Design Standards** (`touch_target_pt >= 44`, `contrast_ratio >= 4.5`, `supports_dynamic_type: true`, `respects_reduced_motion: true`, 2+ responsive breakpoints).
   - **Non-UI Mode:** Entry point, reason, data contracts, failure behavior, side effects list, and **Anti-Gaming Shield** (rejects non-UI plans modifying `.tsx/.jsx/.vue/.html/.css` unless an explicit `non_ui_override_reason` justifies why).
4. **Discovery with Read Evidence (`KES-READ-001`):** Every cited file must have been read with a read/view tool during the session.
5. **Exact Scope (`KES-PLAN-002`):** Direct file writes outside the registered plan are blocked.
6. **Executable Verification:** Specific test commands required to confirm functionality.

See [docs/PLANNING.md](docs/PLANNING.md) for full schema details and examples.

---

## Verification is Evidence, Not Keyword Matching

Kessler tracks:
- Exact verification command executed;
- Category (test, build, lint, typecheck, design/accessibility);
- Real execution success (exit code and output inspection);
- Automated Accessibility Tooling: for UI changes, `KES-VER-001` requires real accessibility/design QA checks (`axe`, `pa11y`, `lighthouse`, or `test:a11y`) to pass whenever available in the project;
- Relevance against detected project test commands;
- Timing relative to the latest source modification.

A failed command or a command executed before the latest code edit **does not** satisfy completion.

---

## CLI Reference

```bash
kessler explain KES-SEC-001   # Detailed policy explanation and remediation
kessler report                 # Comprehensive session evidence and confidence score
kessler waive --reason "..."   # Documented human waiver for untestable environments
kessler doctor --deep          # End-to-end integration and hook diagnostic
kessler budget                 # Static token overhead measurement
```

---

## KesslerBench: Post-Test Validation

Kessler is verified through multi-cloud, multi-model automated benchmarks across real-world fixtures (`authz-regression`, `destructive-git`, `db-migration`, `fake-api-integration`, `cross-module-refactor`):

- **Destructive Command Interception:** 100% prevention of catastrophic Git/filesystem operations (`KES-OPS-001`, `KES-OPS-002`).
- **Pre-Implementation Gating:** 100% enforcement of evidence-based planning before code mutation.
- **Model Compatibility:** Validated against Google Gemini (3.7 Flash, 3.5 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite), NVIDIA NIM (Nemotron 3.5 30B, Llama 3.2 11B, Laguna XS), and OpenRouter models.
- **Zero Token Overhead:** Zero prompt token expansion during ordinary execution turns.

See [benchmarks/REAL_BENCHMARK_REPORT.md](benchmarks/REAL_BENCHMARK_REPORT.md) for full telemetry and benchmark results.

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Architectural overview.
- [docs/PLANNING.md](docs/PLANNING.md) — Implementation plan schema and proportional risk validation.
- [docs/POLICY_REFERENCE.md](docs/POLICY_REFERENCE.md) — Policy catalog and IDs.
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) — Agent harness support boundaries.
- [KESSLER_FINAL_IMPLEMENTATION_SPEC.md](KESSLER_FINAL_IMPLEMENTATION_SPEC.md) — Complete implementation specification.

---

## Author & License

Developed by **Marcos Kohler** (`marcoskohlerfotografia@gmail.com`).

Licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
