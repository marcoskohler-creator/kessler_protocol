# Contributing

1. Keep changes evidence-driven and scoped.
2. Do not add a supported harness label without an executable adapter and tests.
3. Hook code must emit only valid JSON to stdout. Diagnostics go to stderr.
4. Installers must be additive or operate only inside Kessler-owned paths.
5. Every new hard-deny rule requires a regression test and a documented rationale.
6. Prefer `force_ask`/advisory behavior over hard denial when intent is ambiguous.

Run:

```bash
python -m unittest discover -s tests -v
```
