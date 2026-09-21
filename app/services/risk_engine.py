"""
DBPTBS - Risk Engine
---------------------
Combines the anomaly detector's raw signals into a single normalized 0-100
risk score, broken into named, weighted components so every score can be
explained. This module also renders the human-readable "why" behind a
decision - the numbers shown to the user are the same numbers the engine
computed, never separately-authored UI text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np

from app.config import RISK_LOW_MAX, RISK_MEDIUM_MAX, RISK_WEIGHTS
from app.services.anomaly_detector import AnomalyDetector, AnomalyResult
from app.services.dna_engine import DigitalDNA


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def _z_to_unit(z: float, saturate_at: float = 6.0) -> float:
    """Map an absolute z-score to a 0-1 severity, saturating at
    `saturate_at` standard deviations (beyond that, "more anomalous"
    stops mattering for the purpose of the score)."""
    return _clip01(abs(z) / saturate_at)


@dataclass
class RiskComponent:
    name: str
    label: str
    unit_score: float     # 0-1 before weighting
    weight: float
    contribution: float   # 0-100 points contributed to the final score
    reason: str | None = None  # populated only if this component is notable


@dataclass
class RiskAssessment:
    risk_score: float
    decision: str                      # LOW / MEDIUM / HIGH
    behavioural_similarity_pct: float
    components: List[RiskComponent]
    reasons: List[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "risk_score": round(self.risk_score, 1),
            "decision": self.decision,
            "behavioural_similarity_pct": self.behavioural_similarity_pct,
            "components": [
                {
                    "name": c.name,
                    "label": c.label,
                    "unit_score": round(c.unit_score, 3),
                    "weight": c.weight,
                    "contribution": round(c.contribution, 1),
                    "reason": c.reason,
                }
                for c in self.components
            ],
            "reasons": self.reasons,
            "generated_at": self.generated_at,
        }


def _recipient_component(feature_event: dict, dna: DigitalDNA) -> RiskComponent:
    recipient = feature_event.get("recipient")
    count = dna.recipient_counts.get(recipient, 0)
    if recipient in dna.trusted_recipients:
        unit = 0.0
        reason = None
    elif count > 0:
        unit = 0.45
        reason = f"Recipient has been paid before ({count}x) but is not yet a trusted recipient."
    else:
        unit = 1.0
        reason = "Recipient has never been used before on this account."
    contribution = unit * RISK_WEIGHTS["recipient"] * 100
    return RiskComponent("recipient", "Recipient Novelty", unit, RISK_WEIGHTS["recipient"], contribution, reason)


def _time_component(feature_event: dict, dna: DigitalDNA) -> RiskComponent:
    hour = feature_event["hour"]
    if not dna.typical_hours:
        distance = 0
    else:
        distance = min(min(abs(hour - h), 24 - abs(hour - h)) for h in dna.typical_hours)
    unit = _clip01(distance / 8.0)
    reason = None
    if unit > 0.3:
        reason = f"Transaction occurred at {int(hour):02d}:00, outside the account's typical activity hours ({dna.typical_hours})."
    contribution = unit * RISK_WEIGHTS["time"] * 100
    return RiskComponent("time", "Time Anomaly", unit, RISK_WEIGHTS["time"], contribution, reason)


def _velocity_component(recent_tx_count_24h: int, dna: DigitalDNA) -> RiskComponent:
    expected = max(dna.avg_tx_per_day, 0.1)
    ratio = recent_tx_count_24h / expected
    unit = _clip01((ratio - 1.0) / 4.0) if ratio > 1.0 else 0.0
    reason = None
    if unit > 0.3:
        reason = f"{recent_tx_count_24h} transactions in the last 24h vs an expected ~{expected:.1f}."
    contribution = unit * RISK_WEIGHTS["velocity"] * 100
    return RiskComponent("velocity", "Transaction Velocity", unit, RISK_WEIGHTS["velocity"], contribution, reason)


def assess_transaction(
    feature_event: dict,
    dna: DigitalDNA,
    anomaly: AnomalyResult,
    recent_tx_count_24h: int = 1,
) -> RiskAssessment:
    """The single entry point the API/dashboard call. `feature_event` must
    contain the standard feature keys plus 'recipient' and 'hour'."""

    amount_unit = _z_to_unit(anomaly.z_scores["amount"])
    amount_reason = None
    if amount_unit > 0.2:
        ratio = feature_event["amount"] / max(dna.amount_mean, 1e-6)
        amount_reason = f"Transaction amount is {ratio:.1f}x the account's typical amount."
    amount_component = RiskComponent(
        "transaction_amount", "Transaction Amount", amount_unit,
        RISK_WEIGHTS["transaction_amount"], amount_unit * RISK_WEIGHTS["transaction_amount"] * 100,
        amount_reason,
    )

    session_unit = _z_to_unit(anomaly.z_scores["session_duration"])
    session_reason = "Session duration differs significantly from baseline." if session_unit > 0.35 else None
    session_component = RiskComponent(
        "session", "Session Behaviour", session_unit, RISK_WEIGHTS["session"],
        session_unit * RISK_WEIGHTS["session"] * 100, session_reason,
    )

    mouse_z = np.mean([
        abs(anomaly.z_scores["mouse_speed_mean"]),
        abs(anomaly.z_scores["mouse_speed_variance"]),
        abs(anomaly.z_scores["click_interval_mean"]),
    ])
    mouse_unit = _clip01(mouse_z / 6.0)
    mouse_reason = "Mouse behaviour differs significantly from this account's baseline." if mouse_unit > 0.3 else None
    mouse_component = RiskComponent(
        "mouse", "Mouse Behaviour", mouse_unit, RISK_WEIGHTS["mouse"],
        mouse_unit * RISK_WEIGHTS["mouse"] * 100, mouse_reason,
    )

    typing_z = np.mean([
        abs(anomaly.z_scores["typing_speed_mean"]),
        abs(anomaly.z_scores["keystroke_interval_variance"]),
    ])
    typing_unit = _clip01(typing_z / 6.0)
    typing_reason = "Typing pattern deviation detected." if typing_unit > 0.3 else None
    typing_component = RiskComponent(
        "typing", "Typing Behaviour", typing_unit, RISK_WEIGHTS["typing"],
        typing_unit * RISK_WEIGHTS["typing"] * 100, typing_reason,
    )

    recipient_component = _recipient_component(feature_event, dna)
    time_component = _time_component(feature_event, dna)
    velocity_component = _velocity_component(recent_tx_count_24h, dna)

    ml_unit = anomaly.ml_anomaly_score
    ml_reason = "Combined behavioural pattern flagged as anomalous by the ensemble model." if ml_unit > 0.6 else None
    ml_component = RiskComponent(
        "ml_ensemble", "ML Ensemble Signal", ml_unit, RISK_WEIGHTS["ml_ensemble"],
        ml_unit * RISK_WEIGHTS["ml_ensemble"] * 100, ml_reason,
    )

    components = [
        amount_component, recipient_component, time_component,
        session_component, mouse_component, typing_component, velocity_component, ml_component,
    ]

    risk_score = float(np.clip(sum(c.contribution for c in components), 0.0, 100.0))

    if risk_score <= RISK_LOW_MAX:
        decision = "LOW"
    elif risk_score <= RISK_MEDIUM_MAX:
        decision = "MEDIUM"
    else:
        decision = "HIGH"

    reasons = [c.reason for c in sorted(components, key=lambda c: -c.contribution) if c.reason]

    return RiskAssessment(
        risk_score=risk_score,
        decision=decision,
        behavioural_similarity_pct=anomaly.behavioural_similarity_pct,
        components=components,
        reasons=reasons,
    )
