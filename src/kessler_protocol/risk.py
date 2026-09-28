from __future__ import annotations

RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "CRITICAL")

WEIGHTS = {
    "database": 1,
    "migrations": 2,
    "authentication": 2,
    "authorization": 2,
    "payments": 3,
    "medical": 4,
    "pii": 3,
    "secrets": 3,
    "infrastructure": 2,
    "external_api": 1,
    "monorepo": 1,
}


def score_profile(features: dict[str, bool]) -> tuple[int, str, list[dict]]:
    score = 0
    reasons: list[dict] = []
    for name, weight in WEIGHTS.items():
        if features.get(name):
            score += weight
            reasons.append({"signal": name, "weight": weight})
    if score <= 2:
        level = "LOW"
    elif score <= 5:
        level = "MODERATE"
    elif score <= 9:
        level = "HIGH"
    else:
        level = "CRITICAL"
    return score, level, reasons


def effective_strictness(configured: str, risk_level: str) -> str:
    if configured != "auto":
        return configured
    return {
        "LOW": "balanced",
        "MODERATE": "balanced",
        "HIGH": "strict",
        "CRITICAL": "paranoid",
    }.get(risk_level, "balanced")
