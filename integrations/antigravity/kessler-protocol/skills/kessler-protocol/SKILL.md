---
name: kessler-protocol
description: Applies Kessler engineering safety workflows when an agent must inspect risky changes, explain a KES-* intervention, verify modifications, assess residual risk, or recover from a blocked operation.
---

# Kessler Protocol

Use executable evidence rather than assumptions. The hook engine performs deterministic enforcement outside the model context; this skill is only for the reasoning that remains.

When a Kessler policy fires:
1. Read the policy ID and reason.
2. Inspect the affected code path and dependencies before retrying an elevated-risk edit.
3. Prefer the project's detected test/build/typecheck/lint commands.
4. If verification cannot be executed, say so explicitly and request a documented waiver rather than calling the result verified.
5. Never replace missing production integration with mock behavior while presenting the task as complete.

Useful CLI commands when available: `kessler profile`, `kessler explain KES-...`, `kessler report`, `kessler doctor --deep`.
