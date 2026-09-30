# Context / Token Budget

Run:

```bash
kessler budget --json
```

The budget is a regression guard, not a tokenizer-accurate billing estimate. Approximate tokens are calculated as `ceil(chars / 4)`.

Targets:

- always-on core <= 260 approximate tokens (includes the planning invariant);
- normal policy intervention <= 160 approximate tokens;
- policy catalog = 0 prompt tokens while inactive;
- full skill = lazy.

CI fails if the static always-on budget crosses its target.
