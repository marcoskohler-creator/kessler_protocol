from __future__ import annotations

RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "CRITICAL")

WEIGHTS = {
    "database": 1,
    # migrations/authentication/authorization/payments/secrets are exactly the
    # boundaries KES-SEC-001 watches (its path regex: .env/secrets/credentials/
    # auth*/iam/payments/billing/migrations). Recalibrated so any ONE of these
    # signals alone reaches HIGH (score > 5) and auto-escalates strictness to
    # "strict" — previously a lone "secrets" signal only scored 3 (MODERATE),
    # so a real repo with just a .env file never actually saw KES-SEC-001 fire.
    "migrations": 6,
    "authentication": 6,
    "authorization": 6,
    "payments": 6,
    "secrets": 6,
    "medical": 4,
    "pii": 3,
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
