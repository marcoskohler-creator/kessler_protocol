---
name: kessler-protocol
description: Applies Kessler engineering safety workflows for risky changes, KES-* policy interventions, verification evidence, residual risk, and blocked operations in Gemini CLI.
---

# Kessler Protocol

The deterministic hook engine enforces most policy without spending model context. When context is injected, act on the specific policy only.

- Inspect relevant dependencies before elevated-risk changes.
- Use detected executable verification after source/config writes.
- Never label incomplete or placeholder integration as production-complete.
- If verification is unavailable, disclose it and use a documented waiver rather than fabricating success.
- Use `kessler explain <POLICY_ID>` for the full rule only when needed.
