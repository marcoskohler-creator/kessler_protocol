# The Kessler Constitution

This document states the architectural invariants of Kessler Protocol. It is **not** an always-on prompt file.

1. **Runtime over assumption.** A check that can be executed should not be replaced by a claim.
2. **No fake success.** Mocks and fixtures are valid when explicit; incomplete production integration must not be represented as complete.
3. **Risk proportionality.** Friction must increase with destructive potential, sensitive boundaries and blast radius.
4. **Evidence before confidence.** Completion confidence comes from observed reads/searches/writes/verification, not agent rhetoric.
5. **Determinism before tokens.** If a policy can be enforced locally, it must not consume LLM context.
6. **User agency.** Destructive or ambiguous decisions preserve explicit human control; documented waivers are preferable to fabricated certainty.
7. **Non-destructive installation.** Kessler owns only Kessler-managed assets and must preserve unrelated configuration.
8. **No unsupported claims.** A harness is supported only after an implemented adapter, install/uninstall path and tests exist.
9. **Explainability.** A penalty, block or intervention must map to an identifiable policy and remediation.
10. **Measure the cost.** Safety gains must be evaluated together with false positives, latency, tool calls and token overhead.
