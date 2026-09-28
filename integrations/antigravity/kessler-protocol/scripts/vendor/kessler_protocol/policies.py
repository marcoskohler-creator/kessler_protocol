from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files

@lru_cache(maxsize=1)
def load_policies() -> list[dict]:
    raw = files("kessler_protocol.data").joinpath("policies.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    out=[]
    for p in data.get("policies", []):
        q=dict(p)
        q["compiled"]=[re.compile(x, re.I) for x in p.get("patterns", [])]
        out.append(q)
    return out


def get_policy(policy_id: str) -> dict | None:
    for p in load_policies():
        if p["id"] == policy_id:
            return {k:v for k,v in p.items() if k != "compiled"}
    return None


def match_policy(kind: str, value: str) -> list[dict]:
    matches=[]
    for p in load_policies():
        if p.get("kind") != kind:
            continue
        if any(rx.search(value or "") for rx in p.get("compiled", [])):
            matches.append(p)
    return matches
