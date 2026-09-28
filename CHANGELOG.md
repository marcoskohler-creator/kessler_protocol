# Changelog

## 2.1.0 — Implementation freeze

- Replaced prompt-heavy rule architecture with local Policy/Risk/Evidence/Verification/State/Decision engines.
- Added automatic project profiling and cached fingerprints.
- Added risk-derived `auto` strictness.
- Added minimal `.kessler.toml` with manual overrides.
- Added Lazy Policy Loading and Zero-Token Enforcement architecture.
- Added executable verification success and relevance tracking; failed checks no longer satisfy completion.
- Added session reports and documented waivers cleared by subsequent writes.
- Added transactional installation manifests, selective Gemini hook mutation, previous-version restoration and rollback.
- Added Antigravity IDE/2.0 and CLI surface-aware installation paths.
- Added self-contained vendored Antigravity runtime generated from canonical source.
- Added `doctor --deep`, `profile`, `explain`, `report`, `waive`, and `budget` commands.
- Added context-budget CI guard.
- Expanded CI to Linux/macOS/Windows on Python 3.11/3.13.
- Preserved V1 under `legacy/v1` for historical comparison only.
