# Migration from V1 to V2

## V1 issues corrected

- `cp KESSLER_CONSTITUTION.md ~/.gemini/GEMINI.md` overwrote the user's global instructions. Removed.
- Hook files only printed messages and returned success. Replaced with executable JSON-contract hooks.
- Hook files were copied without registration. V2 packages Antigravity hooks in a native plugin and explicitly merges Gemini hooks into settings.
- “Zero Mocks” was absolute. V2 bans fake success, not legitimate test doubles.
- “Backend first” was absolute. V2 uses truthful boundaries and task-appropriate sequencing.
- Execution Lock was universal for “complex” work. V2 uses R0–R4 risk proportionality.
- Persona could conflict with audit duties. Persona is no longer part of enforcement.

## Existing V1 users

If V1 replaced your `~/.gemini/GEMINI.md`, V2 cannot reconstruct what existed before that overwrite unless you have a backup/version-control copy. Install V2 only after reviewing your current configuration.
