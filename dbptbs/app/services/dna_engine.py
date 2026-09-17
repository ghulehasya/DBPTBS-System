"""
DBPTBS - Digital DNA Engine
----------------------------
Derives a user's behavioural baseline ("Digital DNA") from their historical
behavioural events, rather than hard-coding it. Also implements *adaptive*
baseline updates: legitimate behavioural drift is allowed to gradually shift
the DNA, but only from events that were themselves scored as low-risk, so an
attacker cannot poison the baseline in a single high-risk session.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np

from app.config import (
    ADAPTIVE_BASELINE_LEARNING_RATE,
    ADAPTIVE_BASELINE_MIN_OBSERVATIONS,
    TRUSTED_RECIPIENT_MIN_COUNT,
)

# The canonical, ordered list of numeric features every behavioural event is
# reduced to. Every other module (anomaly detector, risk engine) must agree
# on this order.
FEATURE_ORDER = [
    "amount",
    "hour",
    "session_duration",
    "mouse_speed_mean",
    "mouse_speed_variance",
    "click_interval_mean",
    "typing_speed_mean",
    "keystroke_interval_variance",
]


def event_to_vector(feature_dict: dict) -> np.ndarray:
    return np.array([feature_dict[k] for k in FEATURE_ORDER], dtype=float)


@dataclass
class DigitalDNA:
    user_id: str

    amount_mean: float = 0.0
    amount_std: float = 1.0

    hour_counts: Dict[int, int] = field(default_factory=dict)
    typical_hours: List[int] = field(default_factory=list)

    avg_tx_per_day: float = 1.0

    recipient_counts: Dict[str, int] = field(default_factory=dict)
    trusted_recipients: List[str] = field(default_factory=list)

    session_duration_mean: float = 0.0
    session_duration_std: float = 1.0

    mouse_speed_mean: float = 0.0
    mouse_speed_std: float = 1.0
    mouse_variance_mean: float = 0.0
    mouse_variance_std: float = 1.0

    click_interval_mean: float = 0.0
    click_interval_std: float = 1.0

    typing_speed_mean: float = 0.0
    typing_speed_std: float = 1.0
    keystroke_variance_mean: float = 0.0
    keystroke_variance_std: float = 1.0

    sample_count: int = 0
    low_risk_observations_since_update: int = 0
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def feature_means(self) -> np.ndarray:
        return np.array([
            self.amount_mean,
            statistics.fmean(self.typical_hours) if self.typical_hours else 12.0,
            self.session_duration_mean,
            self.mouse_speed_mean,
            self.mouse_variance_mean,
            self.click_interval_mean,
            self.typing_speed_mean,
            self.keystroke_variance_mean,
        ])

    def feature_stds(self) -> np.ndarray:
        # Floor every std so a feature that happened to be constant in the
        # (small) historical sample can't produce a divide-by-near-zero
        # explosion in z-score math downstream.
        floor = 1e-3
        return np.array([
            max(self.amount_std, floor),
            max(statistics.pstdev(self.typical_hours) if len(self.typical_hours) > 1 else 3.0, 1.0),
            max(self.session_duration_std, floor),
            max(self.mouse_speed_std, floor),
            max(self.mouse_variance_std, floor),
            max(self.click_interval_std, floor),
            max(self.typing_speed_std, floor),
            max(self.keystroke_variance_std, floor),
        ])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DigitalDNA":
        d = dict(d)
        d["hour_counts"] = {int(k): v for k, v in d.get("hour_counts", {}).items()}
        return cls(**d)


def _std(values: List[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else max(abs(statistics.fmean(values)) * 0.15, 1.0)


def build_digital_dna(user_id: str, history: List[dict]) -> DigitalDNA:
    """Derive a Digital DNA profile from a list of historical behavioural
    events (as feature dicts, see synthetic_data.BehaviouralEvent.to_feature_dict,
    plus 'recipient' and 'timestamp' keys). This is the ONLY place the
    baseline is computed - it is always derived from data, never hand-set.
    """
    if not history:
        raise ValueError("Cannot build Digital DNA from empty history")

    amounts = [h["amount"] for h in history]
    hours = [h["hour"] for h in history]
    durations = [h["session_duration"] for h in history]
    mouse_speeds = [h["mouse_speed_mean"] for h in history]
    mouse_vars = [h["mouse_speed_variance"] for h in history]
    click_intervals = [h["click_interval_mean"] for h in history]
    typing_speeds = [h["typing_speed_mean"] for h in history]
    keystroke_vars = [h["keystroke_interval_variance"] for h in history]
    recipients = [h["recipient"] for h in history]
    timestamps = [h["timestamp"] for h in history]

    hour_counts = dict(Counter(hours))
    # "Typical hours" = hours that together account for the busiest activity
    # window, derived from the actual distribution (not assumed).
    sorted_hours = sorted(hour_counts.items(), key=lambda kv: -kv[1])
    top_n = max(1, min(6, len(sorted_hours)))
    typical_hours = sorted([h for h, _ in sorted_hours[:top_n]])

    recipient_counts = dict(Counter(recipients))
    trusted = sorted([r for r, c in recipient_counts.items() if c >= TRUSTED_RECIPIENT_MIN_COUNT])
    if not trusted:
        # Fall back to the single most-used recipient so a brand-new
        # profile still has *something* it recognises as familiar.
        trusted = [max(recipient_counts.items(), key=lambda kv: kv[1])[0]]

    if isinstance(timestamps[0], datetime):
        span_days = max((max(timestamps) - min(timestamps)).total_seconds() / 86400.0, 1.0)
    else:
        span_days = max(len(history) / 2.0, 1.0)
    avg_tx_per_day = len(history) / span_days

    return DigitalDNA(
        user_id=user_id,
        amount_mean=statistics.fmean(amounts),
        amount_std=_std(amounts),
        hour_counts=hour_counts,
        typical_hours=typical_hours,
        avg_tx_per_day=round(avg_tx_per_day, 3),
        recipient_counts=recipient_counts,
        trusted_recipients=trusted,
        session_duration_mean=statistics.fmean(durations),
        session_duration_std=_std(durations),
        mouse_speed_mean=statistics.fmean(mouse_speeds),
        mouse_speed_std=_std(mouse_speeds),
        mouse_variance_mean=statistics.fmean(mouse_vars),
        mouse_variance_std=_std(mouse_vars),
        click_interval_mean=statistics.fmean(click_intervals),
        click_interval_std=_std(click_intervals),
        typing_speed_mean=statistics.fmean(typing_speeds),
        typing_speed_std=_std(typing_speeds),
        keystroke_variance_mean=statistics.fmean(keystroke_vars),
        keystroke_variance_std=_std(keystroke_vars),
        sample_count=len(history),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def adapt_baseline(dna: DigitalDNA, low_risk_event: dict) -> DigitalDNA:
    """Nudge the Digital DNA towards a new, *already-approved, low-risk*
    behavioural sample using an exponential moving average.

    Caller contract: only ever pass events whose risk score was LOW. This
    function does not itself check risk, by design, so that policy lives in
    exactly one place (the risk engine / API layer) rather than being
    duplicated here.
    """
    dna.low_risk_observations_since_update += 1
    if dna.low_risk_observations_since_update < ADAPTIVE_BASELINE_MIN_OBSERVATIONS:
        return dna

    lr = ADAPTIVE_BASELINE_LEARNING_RATE
    dna.amount_mean = (1 - lr) * dna.amount_mean + lr * low_risk_event["amount"]
    dna.session_duration_mean = (1 - lr) * dna.session_duration_mean + lr * low_risk_event["session_duration"]
    dna.mouse_speed_mean = (1 - lr) * dna.mouse_speed_mean + lr * low_risk_event["mouse_speed_mean"]
    dna.typing_speed_mean = (1 - lr) * dna.typing_speed_mean + lr * low_risk_event["typing_speed_mean"]

    hour = low_risk_event["hour"]
    dna.hour_counts[hour] = dna.hour_counts.get(hour, 0) + 1
    sorted_hours = sorted(dna.hour_counts.items(), key=lambda kv: -kv[1])
    dna.typical_hours = sorted([h for h, _ in sorted_hours[: max(1, min(6, len(sorted_hours)))]])

    recipient = low_risk_event.get("recipient")
    if recipient:
        dna.recipient_counts[recipient] = dna.recipient_counts.get(recipient, 0) + 1
        dna.trusted_recipients = sorted(
            r for r, c in dna.recipient_counts.items() if c >= TRUSTED_RECIPIENT_MIN_COUNT
        )

    dna.sample_count += 1
    dna.low_risk_observations_since_update = 0
    dna.updated_at = datetime.now(timezone.utc).isoformat()
    return dna
