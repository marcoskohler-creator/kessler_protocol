# KESSLER PROTOCOL — FINAL IMPLEMENTATION SPECIFICATION

**Status:** implementation freeze / release candidate architecture complete  
**Date:** 2026-09-28  
**Scope:** deterministic safety, evidence, verification and risk control for agentic coding assistants  
**Primary implemented adapters:** Google Antigravity 2.0 / IDE / CLI and Gemini CLI

---

## 1. Executive summary

Kessler Protocol replaces the original prompt-heavy “constitutional rules” concept with a **local executable control plane**.

The central architectural decision is:

> **If a policy can be enforced deterministically, it MUST NOT consume LLM context.**

Instead of injecting hundreds of rules into every conversation, Kessler:

1. fingerprints the project;
2. automatically detects stack and risk signals;
3. selects proportional strictness;
4. evaluates policies locally;
5. records evidence of reads, searches, writes and verification;
6. distinguishes successful verification from merely running a command;
7. emits only a compact policy message when the agent actually needs context;
8. preserves an auditable session state and residual-risk report.

The human-controlled `.kessler.toml` therefore becomes intentionally small. Project configuration is primarily discovered automatically, cached, invalidated when relevant project structure changes, and overridden manually only when necessary.

This directly addresses the two main design requirements:

- **automatic configuration by project**, without forcing the user to maintain a large policy file;
- **bounded token overhead**, even as the number of policies grows.

---

# 2. Problem statement

Agentic coding systems can fail in ways that compound:

- editing before understanding dependencies;
- presenting mocks/placeholders as real completion;
- weakening auth/security boundaries to satisfy a task;
- performing destructive repository or filesystem actions under auto-approval;
- claiming success after a test command that actually failed;
- verifying the wrong subsystem after a change;
- adding large persistent rule sets that consume context before any work begins;
- losing user configuration during installation or upgrades.

An earlier Kessler design correctly identified many of these failure classes, but its implementation had structural problems:

- global `GEMINI.md` overwrite;
- hooks that emitted messages but did not perform validation;
- no reliable hook registration contract;
- broad claims of multi-agent support without implemented adapters;
- absolute doctrines such as “Zero Mocks” and “Backend First” that were too coarse;
- no evidence engine;
- no project-sensitive risk model;
- no verification relevance;
- no rollback manifest;
- no explicit token budget.

This is the replacement architecture.

---

# 3. Goals

Kessler MUST:

- prevent narrowly-defined catastrophic operations deterministically;
- elevate destructive actions in a harness-appropriate way;
- identify sensitive project boundaries automatically;
- maintain low static prompt/context cost;
- recognize whether executable verification happened after the latest relevant write;
- recognize whether that verification succeeded;
- estimate whether the verification is relevant to the detected project;
- preserve a local audit trail;
- support project-specific overrides without requiring configuration for normal use;
- support clean installation, uninstall, rollback and previous-Kessler restoration;
- separate core logic from harness adapters;
- never claim adapter support without implemented installation + contract tests;
- support reproducible benchmarking of benefits and costs.

Kessler MUST NOT:

- try to replace a full static analyzer;
- claim that a regex proves a security flaw or fake implementation;
- silently alter unrelated user configuration;
- make every project behave like a regulated/critical system;
- preload the policy catalog into the LLM context;
- claim that a command succeeded solely because its name looks like a test command;
- claim live-harness certification based only on unit tests.

---

# 4. Core architecture

```text
                         PROJECT
                            |
                    Project Profiler
                            |
                     Project Profile
                            |
                    +-------+-------+
                    |               |
               Risk Engine     Config Overrides
                    |               |
                    +-------+-------+
                            |
                       Policy Engine
                            |
               +------------+-------------+
               |            |             |
          Evidence      Verification     Decision
           Engine          Engine         Engine
               |            |             |
               +------------+-------------+
                            |
                        State Engine
                            |
                +-----------+-----------+
                |                       |
        Antigravity Adapter       Gemini Adapter
                |                       |
             Harness                  Harness
```

The canonical implementation is under:

```text
src/kessler_protocol/
```

Harness packages are adapters, not the source of truth.

---

# 5. Source tree

```text
kessler_protocol_final/
├── pyproject.toml
├── README.md
├── README.pt-BR.md
├── KESSLER_FINAL_IMPLEMENTATION_SPEC.md
├── src/
│   └── kessler_protocol/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── context_budget.py
│       ├── profiler.py
│       ├── risk.py
│       ├── policies.py
│       ├── decision.py
│       ├── evidence.py
│       ├── verification.py
│       ├── state.py
│       ├── reports.py
│       ├── hook_runtime.py
│       ├── installers.py
│       ├── doctor.py
│       ├── adapters/
│       │   ├── antigravity.py
│       │   └── gemini.py
│       └── data/
│           └── policies.json
├── integrations/
│   ├── antigravity/
│   │   └── kessler-protocol/
│   │       ├── plugin.json
│   │       ├── hooks.json
│   │       ├── rules/kessler-core.md
│   │       ├── skills/kessler-protocol/SKILL.md
│   │       └── scripts/
│   │           ├── entry.py
│   │           └── vendor/kessler_protocol/...
│   └── gemini-cli/
│       └── skill/kessler-protocol/SKILL.md
├── benchmarks/
├── docs/
├── examples/
├── tests/
└── tools/build_integrations.py
```

---

# 6. Canonical-source rule

There is one authoritative implementation:

```text
src/kessler_protocol
```

Antigravity requires a self-contained plugin runtime. That runtime is generated from canonical source by:

```bash
python tools/build_integrations.py
```

CI rebuilds the vendored runtime and fails if a diff appears. This prevents silent divergence between “package code” and “plugin code”.

---

# 7. Project auto-profiler

## 7.1 Purpose

The profiler lets Kessler behave differently for different projects without requiring a hand-written policy profile.

Examples:

```text
static marketing page
→ LOW/MODERATE project risk
→ balanced enforcement
```

```text
Next.js + PostgreSQL + auth + Stripe + migrations
→ HIGH/CRITICAL project risk
→ strict/paranoid enforcement
```

## 7.2 Deterministic discovery

The profiler inspects bounded, deterministic signals including:

- `package.json`;
- `pyproject.toml`;
- `requirements.txt`;
- `Cargo.toml`;
- `go.mod`;
- Maven/Gradle markers;
- Docker markers;
- Prisma schema/migrations;
- monorepo files;
- CI directories;
- shallow project path names associated with auth, payments, migrations, users, medical records, infrastructure, etc.

It does not call an LLM.

## 7.3 Stack detection

Current built-in examples include:

- JavaScript / TypeScript;
- Python;
- Rust;
- Go;
- JVM markers;
- Next.js / React / Vue / Nuxt / Svelte / SvelteKit;
- Express / Fastify / Nest;
- Django / FastAPI / Flask;
- Prisma / common database clients;
- common authentication dependencies;
- Stripe / PayPal signals.

Detection is deliberately conservative. Unknown frameworks do not fail profiling.

## 7.4 Profile cache

Generated profile:

```text
.kessler/cache/project-profile.json
```

The cache includes:

- schema version;
- generation time;
- workspace;
- project fingerprint;
- languages;
- frameworks;
- feature flags;
- risk score/level;
- effective strictness;
- detected verification commands;
- sensitive paths;
- CI signal.

## 7.5 Fingerprint invalidation

A SHA-256 fingerprint is built from relevant project metadata and shallow architecture signals.

When the fingerprint changes, Kessler regenerates the profile.

This avoids rescanning the whole project on every prompt/tool event.

---

# 8. Project configuration

## 8.1 Human config

The default `.kessler.toml` is intentionally minimal:

```toml
version = 1
strictness = "auto"
context = "lean"
```

Additional blocks exist only for overrides:

```toml
[profile]
auto = true
cache = true

[verification]
auto_detect = true
required = []

[policy]
lazy_loading = true

[paths]
sensitive = ["src/payments/**"]
ignore = ["node_modules", ".next", "dist"]

[commands]
allow = []
deny = ["terraform\\s+destroy"]
```

## 8.2 Precedence

Manual configuration wins over automatic detection where an explicit override exists.

The generated profile is machine-owned; `.kessler.toml` is human-owned.

## 8.3 No mandatory config

Kessler can operate without `.kessler.toml` using built-in defaults.

`kessler init` creates it for reproducibility and creates `.kessler/.gitignore` so profile cache is not committed by default.

---

# 9. Risk engine

## 9.1 Project signals

Current baseline weights:

| Signal | Weight |
|---|---:|
| database | +1 |
| migrations | +2 |
| authentication | +2 |
| authorization | +2 |
| payments | +3 |
| medical/clinical path signal | +4 |
| PII-oriented path signal | +3 |
| secrets/credentials | +3 |
| infrastructure | +2 |
| external API | +1 |
| monorepo | +1 |

These are **Kessler policy weights**, not claims about legal or security compliance.

## 9.2 Risk levels

```text
0–2   LOW
3–5   MODERATE
6–9   HIGH
10+   CRITICAL
```

## 9.3 Auto strictness

```text
LOW       -> balanced
MODERATE  -> balanced
HIGH      -> strict
CRITICAL  -> paranoid
```

Users can override strictness manually.

## 9.4 Important limitation

A file/folder named `patient` is evidence of a potentially sensitive domain, not proof of HIPAA scope. Kessler raises engineering caution; it does not infer legal applicability.

---

# 10. Strictness semantics

## balanced

Goal: catch destructive behavior and missing verification with low friction.

- catastrophic operations: deny;
- destructive operations: explicit confirmation where supported;
- source/config changes: require relevant executable verification when detectable;
- sensitive writes: tracked, not automatically blocked in ordinary cases;
- compact messages.

## strict

Goal: stronger protection for higher-risk projects.

- all balanced behavior;
- sensitive changes elevated;
- stronger discovery expectations;
- additional completion retries for missing evidence.

## paranoid

Goal: critical systems / manual-review-heavy workflow.

- all strict behavior;
- sensitive operations may hard-block on harnesses without force-confirm semantics;
- maximum completion evidence nudges;
- tighter requirement selection.

---

# 11. Policy engine

Policies live in:

```text
src/kessler_protocol/data/policies.json
```

The policy catalog is parsed by the local runtime, not placed in the prompt.

## 11.1 Policy schema

Each policy contains:

```json
{
  "id": "KES-OPS-001",
  "title": "...",
  "severity": "R4",
  "kind": "command",
  "action": "deny",
  "patterns": ["..."],
  "summary": "...",
  "remediation": "..."
}
```

## 11.2 Current policy set

### KES-OPS-001 — Catastrophic system operation

Examples:

- `rm -rf /` pattern;
- filesystem creation commands targeting devices;
- direct destructive `dd` device write;
- fork bomb pattern.

Action: hard deny.

### KES-OPS-002 — Destructive repository/data operation

Examples:

- `git reset --hard`;
- destructive `git clean`;
- generic `rm -rf`;
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE TABLE`.

Action:

- Antigravity: `force_ask`;
- Gemini CLI: deny and require explicit user authorization, because its current hook output contract does not offer Antigravity-equivalent `force_ask`.

### KES-SEC-001 — Sensitive boundary modification

Marks auth, secret, payment, migration and similar paths as elevated risk.

It is a context/risk signal, not proof of a vulnerability.

### KES-TRUTH-001 — Potential fake-success pattern

Examples include placeholder-like content such as TODO/NotImplemented/mock assignments or simulated timing.

Action: advisory only.

Important:

> Pattern match is not proof of fake behavior.

Mocks remain valid in tests, fixtures and explicit prototypes.

### KES-VER-001 — Executable verification required

Triggers when source/config writes exist after the last successful relevant verification.

### KES-READ-001 — Discovery evidence gap

Records whether elevated changes occurred with little/no read/search evidence.

This is used as an evidence quality signal, not a universal blocker.

---

# 12. Lazy Policy Loading

Policy count and prompt size are intentionally decoupled.

```text
Policy catalog
     |
 local matcher
     |
 relevant?
  /      \
 no      yes
 |        |
0 tokens  compact intervention only
```

Adding 500 policies does not mean adding 500 policies to every model call.

The runtime loads policies locally from JSON and outputs only the matched policy summary/remediation when necessary.

---

# 13. Zero-Token Enforcement

The following classes of logic currently require no LLM reasoning:

- command deny/confirm matching;
- user command deny patterns;
- project fingerprint generation;
- project stack/risk signal extraction;
- policy catalog matching;
- sensitive path classification;
- tool evidence recording;
- source-vs-doc write classification;
- test/build/lint/typecheck recognition;
- failed-vs-successful verification;
- verification timing relative to write;
- state persistence;
- installer rollback metadata.

No model context is emitted for ordinary allowed operations.

---

# 14. Context budget

Run:

```bash
kessler budget --json
```

Current implementation-freeze measurement:

```text
Always-on core         ~159 approximate tokens
Skill discovery         ~50 approximate tokens
Full skill              lazy (~257 approximate tokens)
Policy catalog           0 prompt tokens when inactive
```

Approximation:

```text
ceil(characters / 4)
```

This is a regression-budget approximation only. It is not a provider tokenizer and must not be presented as billing-exact.

## CI budget target

Always-on core:

```text
<= 180 approximate tokens
```

CI fails if this limit is exceeded.

This means policy growth is not allowed to silently grow the persistent system context.

---

# 15. Evidence engine

The evidence engine records bounded session evidence:

- file reads;
- repository/code searches;
- source/config writes;
- whether a write was sensitive;
- potential fake-success signals;
- verification executions;
- policy interventions;
- waivers.

Lists are bounded to prevent indefinite state growth.

Documentation-only edits do not automatically trigger executable verification.

---

# 16. Verification engine

Kessler does not merely ask:

> “Was `pytest` mentioned?”

It asks:

1. Was the command recognized as verification?
2. Did the tool execution succeed?
3. Did it happen after the latest source/config write?
4. How relevant is it to the automatically detected project verification commands?
5. Which verification classes are required by project/risk context?

## 16.1 Verification classes

- test;
- build;
- lint;
- typecheck;
- check.

## 16.2 Success determination

Failure is recorded when:

- the harness provides an error;
- response text indicates a non-zero exit or failed command/test pattern.

A failed recognized command does not satisfy completion.

## 16.3 Relevance

### High

Command matches or substantially corresponds to a detected project command.

Example:

```text
package.json: "test": "vitest"
agent executes: npm run test
=> HIGH
```

### Medium

Verification kind matches a detected project verification type but command is generic/different.

### Low

Recognized generic verification but no direct project signal supports it.

### None

Not recognized as executable verification.

## 16.4 Required verification

The engine selects requirements from detected available commands, project sensitivity and strictness.

Balanced mode usually requires at least one relevant successful executable check after source/config writes when such checks are detectable.

Sensitive/strict/paranoid flows can require test and additional available verification classes.

This mechanism is intentionally conservative rather than pretending to understand every project test topology.

---

# 17. Waivers

There are legitimate cases where executable verification is unavailable.

Human override:

```bash
kessler waive --reason "..."
```

Waivers are recorded in session state.

A subsequent source/config write clears the waiver automatically.

This gives a deliberate escape hatch without teaching the agent to fabricate verification.

---

# 18. State engine

State path:

```text
~/.kessler/state/<hashed-session>.json
```

Session key includes harness session ID and workspace.

## 18.1 Atomic writes

State is written to a temporary file and replaced atomically.

## 18.2 Cross-process lock

A lock file is acquired using exclusive file creation.

- bounded acquisition timeout;
- stale lock cleanup;
- atomic replace after update.

This reduces corruption when multiple hooks fire close together.

## 18.3 Session schema

Contains:

```text
schema_version
session_id
workspace
updated_at
reads[]
searches[]
writes[]
verifications[]
interventions[]
warnings[]
nudge_count
profile_fingerprint
waiver?
```

---

# 19. Decision engine

The decision engine translates a policy into harness capabilities.

This separation is required because the two implemented harnesses do not expose identical decisions.

## Antigravity

PreToolUse supports:

- allow;
- deny;
- ask;
- force_ask;
- deny_unless_prior_grant.

Kessler uses `force_ask` for destructive/elevated actions where human awareness must not be bypassed by cached permissions.

## Gemini CLI

BeforeTool supports allow/deny but does not provide Antigravity-equivalent `force_ask` in the documented contract used here.

Kessler therefore maps certain destructive operations to deny with a reason requiring explicit user authorization.

This is a deliberate adapter difference, not a hidden behavioral mismatch.

---

# 20. Antigravity adapter

## 20.1 Plugin structure

The integration follows Antigravity's current plugin shape:

```text
plugin.json
hooks.json
rules/
skills/
scripts/
```

## 20.2 Hook events

Used:

- `PreToolUse`;
- `PostToolUse`;
- `Stop`.

## 20.3 Tools tracked

Current matchers include:

- `run_command`;
- file writes/replacements;
- `view_file`;
- `grep_search`;
- `find_by_name`.

Read/search tools exist primarily to collect discovery evidence and emit no context on ordinary successful operations.

## 20.4 Stop behavior

If verification evidence is missing, Kessler can return:

```json
{
  "decision": "continue",
  "reason": "KES-VER-001 ..."
}
```

This re-enters the execution loop for a bounded number of nudges depending on strictness.

---

# 21. Gemini CLI adapter

Registered events:

- `BeforeTool`;
- `AfterTool`;
- `AfterAgent`.

Settings are mutated selectively by name:

```text
kessler-before-tool
kessler-after-tool
kessler-after-agent
```

Unrelated hook groups and settings remain untouched.

Gemini's stdin/stdout contract is respected:

- JSON input via stdin;
- only JSON on stdout;
- diagnostic logging belongs on stderr.

---

# 22. Harness contract sources validated for this implementation

External contracts were rechecked on **2026-09-28**.

## Google Antigravity

Plugins:

https://www.antigravity.google/docs/plugins?tab=cli

Relevant documented facts used by Kessler:

- plugin directory with `plugin.json`;
- optional `hooks.json`, `skills/`, `rules/`;
- workspace plugins under `.agents/plugins/`;
- global IDE/2.0 plugins under `~/.gemini/config/plugins/`;
- CLI staged plugin directory under `~/.gemini/antigravity-cli/plugins/`.

Hooks:

https://www.antigravity.google/docs/hooks

Relevant contracts used:

- `PreToolUse`;
- `PostToolUse`;
- `Stop`;
- JSON via stdin/stdout;
- `force_ask` support in `PreToolUse`;
- `Stop decision=continue` to re-enter the loop.

Rules:

https://www.antigravity.google/docs/rules

Kessler uses a very small `always_on` core and deliberately avoids placing the full policy catalog in rules.

Skills:

https://www.antigravity.google/docs/skills?tab=ide

Kessler relies on progressive disclosure: skill description is discoverable, full skill content loads only when relevant.

## Gemini CLI

Hooks overview:

https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/index.md

Hook reference:

https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md

Settings reference:

https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md

Relevant contracts used:

- hooks in `settings.json`;
- `BeforeTool`, `AfterTool`, `AfterAgent`;
- strict JSON stdout;
- stderr for logging;
- hook names and matchers;
- project settings overriding user settings.

---

# 23. Installation architecture

## 23.1 Transactional objective

An installer failure must not leave the previous Kessler installation destroyed.

## 23.2 Installation manifest

Stored under:

```text
~/.kessler/installations/
```

Records:

- target;
- scope;
- surface;
- workspace;
- installed paths;
- previous Kessler backups;
- previous named Kessler hook groups;
- creation timestamp.

## 23.3 Backups

Stored under:

```text
~/.kessler/backups/<installation-id>/
```

Only relevant previous Kessler-owned assets are restored.

## 23.4 Gemini preservation rule

The installer does not restore the entire old `settings.json` on ordinary uninstall because that could erase unrelated user changes made after installation.

Instead it:

1. removes current Kessler-named hook handlers;
2. retains unrelated settings/hooks;
3. restores previous Kessler hook groups if one existed.

Full settings bytes are held only for immediate transaction rollback if installation itself fails.

## 23.5 Antigravity self-contained runtime

The installed Antigravity plugin receives a vendored copy of canonical runtime code and an `entry.py` launcher.

The installer rewrites hook commands to use the exact Python interpreter that performed installation.

This avoids reliance on a `python3` binary name and avoids relying on the caller's current working directory.

---

# 24. Surface-aware Antigravity paths

User/global IDE / Antigravity 2.0:

```text
~/.gemini/config/plugins/kessler-protocol
```

User/global Antigravity CLI:

```text
~/.gemini/antigravity-cli/plugins/kessler-protocol
```

Workspace:

```text
.agents/plugins/kessler-protocol
```

CLI examples:

```bash
kessler install --target antigravity --scope user --surface ide
kessler install --target antigravity --scope user --surface cli
kessler install --target antigravity --scope workspace --workspace .
```

---

# 25. Doctor

## Standard doctor

Checks packaging/installation artifacts.

## Deep doctor

`--deep` executes synthetic runtime probes.

Example:

```bash
kessler doctor --target antigravity --surface ide --deep
```

The deep installed doctor invokes the **installed vendored runtime** with a synthetic catastrophic command and verifies that JSON output contains a deny decision.

This is stronger than merely checking that files exist.

It is still not equivalent to a full live GUI/CLI session certification.

---

# 26. Session report

Command:

```bash
kessler report
```

Current report fields:

- project risk;
- effective strictness;
- files modified;
- sensitive writes;
- read/search evidence count;
- interventions;
- required verification;
- verification completeness;
- residual risk;
- bounded completion confidence.

Example conceptual output:

```text
Project risk          HIGH
Strictness            strict
Files modified        8
Sensitive writes      2
Read/search evidence  12 / 4
Verification          PASS
Residual risk         MODERATE
Completion confidence 92%
```

The confidence value is a Kessler heuristic, not a formal probability of correctness.

---

# 27. Fail-open vs fail-closed strategy

Kessler intentionally does not fail closed for every ambiguous condition.

## Fail closed

Used for narrowly deterministic catastrophic/destructive operations where false negative cost is high and pattern confidence is high.

## Force confirmation

Used by Antigravity for elevated destructive operations.

## Advisory / track-only

Used when pattern matching is not evidence of an actual defect, e.g. placeholder-like code.

## Completion retry

Used for missing verification evidence after source/config writes.

The goal is to avoid turning Kessler into a brittle bureaucracy layer.

---

# 28. “No Fake Success” doctrine

The old absolute “Zero Mocks” rule is replaced.

Mocks are valid when they are explicitly used for:

- unit tests;
- fixtures;
- deterministic simulation;
- contract tests;
- explicit prototypes.

Mocks/placeholders are not acceptable when they are used to represent missing production integration while the task is presented as complete.

`KES-TRUTH-001` only raises a suspicion signal. It does not prove misuse.

---

# 29. Deep Read doctrine

The old instruction “use grep before writing” becomes evidence-oriented rather than ritualistic.

Kessler records:

- file reads;
- searches;
- writes;
- timing.

A future graph engine can extend this into callers/imports/tests/blast-radius analysis.

The current implementation intentionally does not pretend that “one grep call” guarantees adequate architectural discovery.

---

# 30. Context modes

## lean — default

- minimal policy summaries;
- no catalog preload;
- compact remediation;
- suitable for most work.

## standard

- policy title + summary + remediation.

## deep

- more explicit severity and remediation text.

Context mode affects emitted explanations, not the deterministic policy decision itself.

---

# 31. Security model

Kessler protects against a subset of agent-induced engineering hazards. It is not a host sandbox and not a replacement for OS permissions.

Security assumptions:

- the user account running the agent can modify its own Kessler files;
- malicious project code could attempt to alter project-local config;
- regex command filtering cannot model every shell semantic edge case;
- a truly hostile agent could attempt obfuscation unless the host enforces tool boundaries;
- Kessler should therefore be used as defense-in-depth, not as the only security boundary.

Important hardening properties implemented:

- catastrophic deny rules are independent of the LLM;
- hook state uses atomic writes and lock files;
- installer changes are scoped and recorded;
- global user instruction files are not overwritten;
- policy catalog is local data, not model-generated policy.

---

# 32. Privacy model

Kessler performs project discovery locally.

The core implementation does not require sending project files to an additional external model merely to calculate risk or select policies.

State contains paths/commands and should be considered local engineering telemetry. Users handling sensitive projects should protect their home directory accordingly.

---

# 33. KesslerBench

The benchmark layer exists to answer:

> Does Kessler improve engineering outcomes enough to justify its friction and cost?

## Required comparison

```text
same fixture
same task
same agent/model
same harness configuration
WITHOUT KESSLER
vs
WITH KESSLER
```

## Required metrics

Benefit:

- acceptance-test success;
- build/test/typecheck success;
- security regressions;
- fake-success incidents;
- unrelated edits;
- destructive operations;
- verification completeness;
- dependency-discovery evidence.

Cost:

- false-positive interventions;
- user confirmations;
- tool calls;
- elapsed time;
- token overhead when exposed by harness;
- completion rate.

## Statistical discipline

Published results should not rely on one run.

Every publication must report model/harness version, prompts, fixtures, run count, scoring code, exclusions and raw anonymized data.

---

# 34. Token-performance benchmark

KesslerBench should separately measure:

```text
baseline model input tokens
Kessler model input tokens
absolute delta
overhead percentage
```

The architecture target is that normal operations emit no Kessler policy text and therefore have near-zero dynamic context overhead beyond the small always-on/discovery baseline.

Do not substitute the local chars/4 regression estimate for real provider token telemetry when actual harness measurements are available.

---

# 35. CLI reference

```text
kessler init
kessler profile [--refresh]
kessler budget
kessler explain <POLICY_ID>
kessler install --target antigravity|gemini ...
kessler uninstall --target antigravity|gemini ...
kessler rollback --target antigravity|gemini ...
kessler doctor --target package|antigravity|gemini [--deep]
kessler report
kessler waive --reason "..."
```

Internal hook entry:

```text
kessler hook --harness ... --event ...
```

Installed adapters use a vendored runtime rather than depending on this command remaining in PATH.

---

# 36. Automated test coverage at implementation freeze

The current local test suite covers:

1. automatic profile/risk detection;
2. minimal config generation;
3. Antigravity catastrophic deny;
4. Antigravity force confirmation for destructive Git;
5. Gemini destructive operation deny;
6. failed test does not satisfy verification;
7. successful relevant test satisfies verification;
8. docs-only write does not trigger source verification gate;
9. policy explanation lookup;
10. Antigravity self-contained install + previous plugin restoration;
11. Gemini unrelated settings preservation + previous Kessler hook restoration;
12. deep package doctor;
12. deep package doctor;
13. always-on context budget guard.

Test suite result at packaging time is recorded in `IMPLEMENTATION_VALIDATION.md`.

---

# 37. CI matrix

GitHub Actions configuration covers:

```text
Ubuntu latest
macOS latest
Windows latest
```

against:

```text
Python 3.11
Python 3.13
```

CI runs:

- editable install;
- unit/integration tests;
- compileall;
- deep package doctor;
- context budget;
- generated Antigravity runtime drift check.

---

# 38. Compatibility claims

## Implemented

- Antigravity 2.0 / IDE plugin layout and hooks;
- Antigravity CLI global plugin path;
- Gemini CLI hook registration.

## Not yet claimed

- Claude Code;
- Codex;
- Cursor.

No README language should imply these adapters work until implemented and tested.

---

# 39. Live certification still required

Automated tests can verify contract shape and local behavior, but they do not replace actual agent runs.

Before declaring a published build “live certified”, execute the smoke matrix against installed current versions:

## Antigravity IDE / 2.0

- plugin visible;
- hooks visible/enabled;
- normal read/write allowed;
- catastrophic command denied;
- destructive command force-asks;
- write -> failed test -> Stop continues;
- write -> successful relevant test -> Stop allows;
- `doctor --deep` passes;
- uninstall restores previous state.

## Antigravity CLI

Same matrix using CLI-staged plugin path and `/hooks` visibility.

## Gemini CLI

- named hooks visible in settings;
- stdout JSON accepted;
- unrelated hook remains active;
- catastrophic/destructive path is blocked;
- failed verification does not clear gate;
- successful verification does;
- uninstall restores previous Kessler hook state without removing unrelated settings.

This is the remaining release-certification activity, not an architectural redesign.

---

# 40. Acceptance criteria

## Architecture

- [x] canonical core separated from harness adapters;
- [x] deterministic policy engine;
- [x] automatic project profiler;
- [x] risk engine;
- [x] verification engine;
- [x] evidence engine;
- [x] state engine;
- [x] decision engine;
- [x] session reporting;
- [x] context budget guard.

## Token control

- [x] full policy catalog outside prompt;
- [x] lazy full skill;
- [x] always-on core below target;
- [x] no policy output for ordinary allow path.

## Installation

- [x] no overwrite of global `GEMINI.md`;
- [x] installation manifest;
- [x] previous Kessler backup;
- [x] selective Gemini hook mutation;
- [x] rollback support;
- [x] exact interpreter path for installer-managed Antigravity hooks;
- [x] self-contained vendored runtime.

## Verification

- [x] command class recognition;
- [x] failure detection;
- [x] relevance scoring;
- [x] after-write timing;
- [x] bounded completion retry;
- [x] documented human waiver.

## Quality

- [x] automated tests pass locally;
- [x] deep package doctor passes;
- [x] source compiles;
- [x] generated runtime can be reproduced;
- [ ] live harness smoke certification executed on target machines.

---

# 41. Known limitations

1. Verification relevance is heuristic, not complete dependency-aware test selection.
2. Fake-success detection is advisory and pattern-based.
3. Project risk classification is engineering risk inference, not legal/compliance classification.
4. Deep Read currently records evidence; it does not yet build a semantic dependency graph.
5. Gemini does not expose the same force-confirm decision semantics as Antigravity in the contract used here.
6. Python 3.11+ is required.
7. Direct manual Antigravity plugin use relies on `python` being resolvable; installer-managed deployment rewrites to an exact interpreter and is preferred.
8. Live current-version harness certification must be repeated when upstream hook contracts materially change.

---

# 42. Next engineering phase

Do not add more generic rules first.

Priority order:

## Dependency and verification intelligence

- build lightweight import/caller graph;
- map changed paths to nearest tests;
- derive verification relevance from actual dependency graph;
- detect migration rollback coverage;
- strengthen monorepo package targeting.

## 2.3 — Benchmark release

- runnable fixtures;
- benchmark runner adapters;
- repeated experiment orchestration;
- machine-readable result schema;
- published baseline vs Kessler data.

## 2.4 — Additional harnesses

Implement one at a time:

1. Claude Code;
2. Codex;
3. Cursor.

Each adapter requires:

- exact contract research;
- installer;
- uninstall/rollback;
- hook behavior tests;
- live smoke tests;
- benchmark cohort.

---

# 43. Decision record: why not thousands of rules in the prompt?

Because a large persistent rule set creates four problems:

1. token cost;
2. instruction competition;
3. reduced salience of important rules;
4. coupling between framework growth and model context size.

Kessler instead treats policies as executable data.

The LLM only receives semantic guidance when deterministic enforcement cannot complete the task itself.

This is the architectural boundary that should be preserved in future versions.

---

# 44. Decision record: why automatic configuration?

Manual project profiles age quickly and create setup friction.

Project files already contain strong deterministic signals:

- framework dependencies;
- test/build scripts;
- database schema;
- auth libraries;
- migration directories;
- CI files;
- directory structure.

Kessler therefore treats auto-discovery as the default and manual configuration as an override layer.

---

# 45. Decision record: why bounded intervention retries?

Infinite “not verified, continue” loops can trap an agent when tests genuinely cannot run.

The implementation uses risk-dependent bounded nudges plus a human waiver path.

This preserves pressure toward evidence without making the tool impossible to escape.

---

# 46. Decision record: why not call an extra LLM for policy routing?

Using another model to decide whether a deterministic rule applies would:

- add tokens;
- add latency;
- introduce nondeterminism;
- create another failure mode;
- weaken auditability.

The current project profiler and policy router are local by design.

Semantic/model-assisted policy evaluation may be added later only for categories that genuinely cannot be expressed deterministically, and it should remain optional.

---

# 47. Release recommendation

The **implementation architecture is complete for the current release**.

No additional conceptual layer is required before testing.

The correct next action is:

1. install this exact package in controlled Antigravity and Gemini environments;
2. execute the live certification matrix;
3. fix only observed contract/runtime defects;
4. tag the tested commit;
5. start KesslerBench experiments from that immutable tag.

Do not expand scope with new agents or new large rule catalogs before live certification.

---

# 48. Final architectural invariant

> **Kessler must increase engineering evidence faster than it increases agent context.**

Any future feature that violates that invariant requires explicit architectural review.

---

# 49. Decision record: Planning Gate & Risk Proportionality (Abordagem 2)

## 49.1 Problem Statement
When the Planning Gate (`KES-PLAN-001`/`KES-PLAN-002`) required `future_risks` to unconditionally contain at least 2 items, trivial, cosmetic, or isolated changes (e.g. documentation updates, pure helper optimization, minor typo fixes) had no legitimate secondary risks. Coercing models to provide two risks unconditionally led to:
1. "Slop por coerção": models inventing hallucinated, absurd, or irrelevant risks just to satisfy the count validator;
2. Agent denial loops: models struggling to invent two valid risks while respecting the minimum 8-character and anti-placeholder filters;
3. Direct violation of Principle 3 of the Kessler Constitution (Risk Proportionality).

## 49.2 Solution (Abordagem 2)
Proportional risk gating dynamically evaluates both workspace profile risk and individual planned file targets:
- **Elevated / Sensitive Changes**: If `profile.risk.level` is `HIGH` or `CRITICAL`, strictness is `strict` or `paranoid`, or any target in `implementation` touches a sensitive boundary (detected via `sensitive_target`: auth, credentials, payments, database migrations, `.env`), `justification.future_risks` strictly requires at least 2 concrete risks (`minimum_count=2`).
- **Low / Moderate Non-Sensitive Changes**: `future_risks` remains a mandatory key and must be a JSON array, but is legitimately permitted to be empty (`minimum_count=0`).
- **Quality Floor**: If any risk item is declared, it must meet the standard 8+ character floor and pass anti-placeholder regex (`_PLACEHOLDER`), ensuring that any declared risk is substantive.

