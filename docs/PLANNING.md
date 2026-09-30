# Planning before implementation

Kessler requires a specific, evidence-based implementation plan before project-changing tools run. Read/search tools can inspect the project first so the plan is grounded in actual files (`KES-READ-001`). All shell commands and write tools wait until the plan is registered (`KES-PLAN-001`). The agent must present the plan, then write it with a file-write tool to `.kessler/cache/implementation-plan.json`. The hook registers that valid plan for the current agent turn. A later file write is allowed only when its exact workspace-relative path appears in `implementation` (`KES-PLAN-002`).

## Schema & Risk Proportionality

The implementation plan requires:
- `goal` (8+ chars)
- `purpose` (8+ chars)
- `justification`:
  - `why`: rationale for why the change is needed now.
  - `future_risks`: list of foreseeable risks or secondary failure modes.
- `users`: target audience or actors (at least 1 entry, 8+ chars each).
- `usage_flow`: sequence of steps (at least 2 entries, 8+ chars each).
- `discovery`: array of `{path, finding}` entries where each path exists and has recorded read evidence in the current session.
- `delivery`: delivery method or packaging (8+ chars).
- `rollback`: exact rollback strategy (8+ chars).
- `interface`: mode-specific declaration (`mode: "ui"` or `mode: "non_ui"`).
- `implementation`: array of `{path, placement, method, responsibility}` entries.
- `validation`: verification steps (list of strings or `{description, command}`).

### Justification & Future Risks (`future_risks`)

`justification.future_risks` requires **at least 2 substantive entries** (`minimum_count=2`). Each risk must be specific (8+ characters, no placeholder words such as `todo`, `unknown`, or `tbd`), forcing the agent to consider secondary failure modes and long-term implications before modifying code.

### UI Mode & Platform Design Standards (`design_standards`)

For user-facing changes (`mode: "ui"`), Kessler enforces deterministic floor requirements from platform interaction guidelines (Apple HIG / Material Design / WCAG 2.2 AA):

- `touch_target_pt`: must be a number `>= 44` (Apple HIG / Material minimum tap target in points/pixels).
- `contrast_ratio`: must be a number `>= 4.5` (WCAG 2.2 AA standard for normal text).
- `supports_dynamic_type`: must be `true` (accessible font scaling).
- `respects_reduced_motion`: must be `true` (respects `prefers-reduced-motion`).
- `responsive_breakpoints`: must list at least 2 named breakpoints (e.g. `["mobile", "desktop"]`).

> **Note:** The `design_standards` block states compliant target numbers in the plan contract. At runtime, `KES-VER-001` additionally requires an executable accessibility and design-QA check (`axe`, `pa11y`, `lighthouse`, or `npm run test:a11y`) to pass after file modification whenever such tooling is available in the project.

### Anti-Gaming Shield for Non-UI Work

A plan cannot dodge `design_standards` simply by declaring `mode: "non_ui"` while its implementation targets UI-surface files (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.html`, `.htm`, `.css`, `.scss`, `.sass`, `.less`). If a non-UI plan touches these extensions, Kessler rejects the plan unless `interface.non_ui_override_reason` explicitly explains why (8+ characters, no placeholders) — for example, a static compiled stylesheet bundle or server-rendered email template with no interactive controls.

## Example Plan (UI Mode)

```json
{
  "goal": "Add a report export action to the audit detail page",
  "purpose": "Let reviewers save the completed audit report for offline review",
  "justification": {
    "why": "Reviewers currently screenshot the page to share audits, losing data fidelity",
    "future_risks": [
      "Ad-hoc screenshot sharing could leak fields that a real export would redact",
      "Bolting on export later without a stable endpoint would force consumer migration"
    ]
  },
  "users": ["Reviewers who have access to a completed audit"],
  "usage_flow": [
    "Reviewer opens the audit list and selects a completed audit",
    "Reviewer sees Export report in the detail page action bar",
    "Reviewer clicks Export report and receives the generated PDF"
  ],
  "discovery": [
    {"path": "src/pages/audits/index.tsx", "finding": "The audit list links each completed row to the detail page"},
    {"path": "src/pages/audits/[id].tsx", "finding": "The detail page renders the existing action bar"}
  ],
  "delivery": "A PDF download triggered from the browser via the existing export endpoint",
  "rollback": "Revert the audit.tsx change; no server-side or data changes are involved",
  "interface": {
    "mode": "ui",
    "entry_point": "Audit list row opens the audit detail page",
    "final_screen": "Audit detail with Export report in the top action bar and feedback",
    "accessibility": "Export button is keyboard-reachable and has an accessible label",
    "states": [
      "Default: Export report button visible in the action bar",
      "Loading: button shows a spinner while PDF generates",
      "Error: inline message shown if export request fails"
    ],
    "controls": [
      {
        "label": "Export report",
        "location": "Top action bar beside Share",
        "action": "Request PDF export for the current audit",
        "destination": "Browser download for the generated PDF",
        "failure": "Show an error and keep the detail page open",
        "handler_path": "src/pages/audits/[id].tsx",
        "evidence_path": "src/pages/audits/[id].tsx"
      }
    ],
    "navigation": [
      {
        "from": "Audit list",
        "via": "Completed audit row",
        "to": "Audit detail page",
        "evidence": "Existing list link and detail route inspected in discovery",
        "evidence_path": "src/pages/audits/index.tsx"
      }
    ],
    "design_standards": {
      "touch_target_pt": 44,
      "contrast_ratio": 4.5,
      "supports_dynamic_type": true,
      "respects_reduced_motion": true,
      "responsive_breakpoints": ["mobile", "desktop"]
    }
  },
  "implementation": [
    {
      "path": "src/pages/audits/[id].tsx",
      "placement": "Top action bar beside Share",
      "method": "Render the button only for completed audits and handle loading/errors",
      "responsibility": "Expose the export action in the detail view"
    }
  ],
  "validation": [
    "Open completed audit from list and confirm button placement and keyboard focus",
    "Click Export report and verify downloaded PDF content against audit detail"
  ]
}
```

## Example Plan (Non-UI Mode, Low-Risk)

For backend, CLI, or maintenance changes touching no sensitive boundaries:

```json
{
  "goal": "Optimize math calculation caching in utility module",
  "purpose": "Avoid redundant floating point recalculations in loop",
  "justification": {
    "why": "Benchmarks show 15% CPU spent in un-memoized geometry computations",
    "future_risks": [
      "Unbounded cache growth could increase memory pressure on very large matrix batches",
      "Stale memoized results if caller modifies mutable matrix buffers in-place"
    ]
  },
  "users": ["Internal calculation pipeline callers"],
  "usage_flow": [
    "Caller invokes calculate_vector with identical coordinate inputs",
    "Cached memoized result is returned without recomputing"
  ],
  "discovery": [
    {"path": "src/calc.py", "finding": "calculate_vector performs unmemoized matrix multiplication"}
  ],
  "delivery": "Updated Python module with lru_cache decorator",
  "rollback": "Remove lru_cache import and decorator from calc.py",
  "interface": {
    "mode": "non_ui",
    "entry_point": "calc.calculate_vector",
    "reason": "Internal pure computation acceleration",
    "result": "Cached calculation return values",
    "data_contract": "calculate_vector(matrix: list[float]) -> float",
    "failure_behavior": "Raises ValueError on non-numeric matrix entries",
    "side_effects": []
  },
  "implementation": [
    {
      "path": "src/calc.py",
      "placement": "calculate_vector function definition",
      "method": "Decorate with functools.lru_cache(maxsize=1024)",
      "responsibility": "Cache pure calculation results"
    }
  ],
  "validation": [
    "Run python3 -m unittest tests/test_calc.py"
  ]
}
```
