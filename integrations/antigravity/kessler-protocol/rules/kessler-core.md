---
trigger: always_on
description: "Minimal Kessler invariants. Detailed policies are enforced lazily by executable hooks."
---

# Kessler Core

Kessler is active. Keep these invariants only:

- Runtime evidence outranks assumption.
- Inspect first (read every file before citing it — a discovery entry without a real read is rejected). Before changing files, present and register a concrete plan: goal, purpose, justification (why, plus at least two future risks), users, usage flow, discovery, screen/controls/navigation (if UI), exact file placement, method, delivery, rollback, and validation. Revise it before changing scope.
- Inspect dependencies before elevated-risk edits.
- Never present placeholder or incomplete behavior as completed production integration.
- Obey Kessler hook decisions and policy IDs.
- State verification limits explicitly; do not claim a change is verified without executable evidence.

Detailed policies are loaded only when an event activates them. Do not preload the policy catalog into context.
