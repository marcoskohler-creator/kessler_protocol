# Policy Reference

Policies live in `src/kessler_protocol/data/policies.json` and are loaded locally.

| ID | Purpose | Default action |
|---|---|---|
| KES-OPS-001 | catastrophic host/filesystem commands | deny |
| KES-OPS-002 | destructive repository/filesystem/database commands | explicit confirmation / deny where force-confirm is unavailable |
| KES-PLAN-001 | direct edit or shell command without a registered plan | deny until a valid, evidence-based plan is registered |
| KES-PLAN-002 | direct file edit outside the registered plan | deny until the exact file and placement are added to the plan |
| KES-SEC-001 | sensitive boundary modification | risk-proportional elevation |
| KES-TRUTH-001 | possible placeholder/fake-success pattern | advisory only |
| KES-VER-001 | executable verification after source/config writes | completion gate |
| KES-READ-001 | elevated edit without discovery evidence | evidence warning |

`KES-TRUTH-001` is deliberately not proof that code is fake. It is a suspicion signal and must not be used as a deterministic accusation.
