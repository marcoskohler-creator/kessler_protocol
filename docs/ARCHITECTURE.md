# Architecture

```text
Project -> Profiler -> Risk Engine -> Policy Engine -> Decision Engine -> Adapter
                      |               |                  |
                      |               +-> Evidence ------+
                      |               +-> Verification --+
                      +-----------------> State Engine
```

The canonical implementation lives in `src/kessler_protocol`. Antigravity's self-contained runtime is generated from that source with `tools/build_integrations.py`; CI rejects drift.

The LLM receives a minimal always-on invariant layer. Project discovery, policy matching, verification status, state and destructive-operation decisions happen locally.
