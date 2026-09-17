"""
DBPTBS - Synthetic Behavioural Data Generator
----------------------------------------------
Generates realistic synthetic transaction, session, and interaction data
for a simulated user, plus adversarial ("account takeover") samples.

No real financial data, wallets, or people are involved anywhere in this
module. Everything is generated from probability distributions.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List


@dataclass
class BehaviouralEvent:
    """One simulated transaction attempt, with the full context DBPTBS
    would observe at pre-transaction time: the transaction itself, the
    session it happened in, and the interaction (mouse/keyboard) telemetry
    for that session."""

    user_id: str
    amount: float
    recipient: str
    timestamp: datetime
    session_duration: float          # seconds
    mouse_speed_mean: float          # px/s, synthetic units
    mouse_speed_variance: float
    click_interval_mean: float       # seconds between clicks
    typing_speed_mean: float         # chars/min
    keystroke_interval_variance: float
    label: str = "legitimate"        # "legitimate" or "attacker" (ground truth, for demo/eval only)

    def to_feature_dict(self) -> dict:
        return {
            "amount": self.amount,
            "hour": self.timestamp.hour,
            "session_duration": self.session_duration,
            "mouse_speed_mean": self.mouse_speed_mean,
            "mouse_speed_variance": self.mouse_speed_variance,
            "click_interval_mean": self.click_interval_mean,
            "typing_speed_mean": self.typing_speed_mean,
            "keystroke_interval_variance": self.keystroke_interval_variance,
        }


# A small pool of fake wallet addresses so recipients recur realistically.
def _fake_wallet(prefix: str = "WALLET") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


@dataclass
class UserBehaviourGenerator:
    """Generates a self-consistent synthetic behavioural history for one
    simulated user, i.e. their "ground truth" habits, then samples
    legitimate and attacker-style events from it.
    """

    user_id: str
    amount_mean: float = 1500.0
    amount_std: float = 450.0
    typical_hours: List[int] = field(default_factory=lambda: [18, 19, 20, 21])
    avg_tx_per_day: float = 2.0
    trusted_recipients: List[str] = field(default_factory=lambda: [_fake_wallet(), _fake_wallet()])
    session_duration_mean: float = 1200.0
    session_duration_std: float = 250.0
    mouse_speed_mean: float = 420.0
    mouse_speed_std: float = 35.0
    click_interval_mean: float = 0.42
    click_interval_std: float = 0.08
    typing_speed_mean: float = 55.0
    typing_speed_std: float = 8.0
    keystroke_var_mean: float = 0.015
    keystroke_var_std: float = 0.004

    seed: int = None

    def __post_init__(self):
        self._rng = random.Random(self.seed)

    # ------------------------------------------------------------------
    # Legitimate behaviour
    # ------------------------------------------------------------------
    def sample_legitimate_event(self, when: datetime = None) -> BehaviouralEvent:
        rng = self._rng
        if when is None:
            day_offset = rng.uniform(0, 60)
            hour = rng.choice(self.typical_hours) + rng.uniform(-0.6, 0.6)
            hour = min(max(hour, 0), 23.99)
            when = datetime.now() - timedelta(days=day_offset)
            when = when.replace(hour=int(hour), minute=rng.randint(0, 59), second=0, microsecond=0)

        amount = max(50.0, rng.gauss(self.amount_mean, self.amount_std))
        recipient = rng.choice(self.trusted_recipients) if rng.random() < 0.85 else _fake_wallet()

        return BehaviouralEvent(
            user_id=self.user_id,
            amount=round(amount, 2),
            recipient=recipient,
            timestamp=when,
            session_duration=max(30.0, rng.gauss(self.session_duration_mean, self.session_duration_std)),
            mouse_speed_mean=max(10.0, rng.gauss(self.mouse_speed_mean, self.mouse_speed_std)),
            mouse_speed_variance=abs(rng.gauss(18.0, 4.0)),
            click_interval_mean=max(0.05, rng.gauss(self.click_interval_mean, self.click_interval_std)),
            typing_speed_mean=max(10.0, rng.gauss(self.typing_speed_mean, self.typing_speed_std)),
            keystroke_interval_variance=max(0.001, rng.gauss(self.keystroke_var_mean, self.keystroke_var_std)),
            label="legitimate",
        )

    def sample_history(self, n: int) -> List[BehaviouralEvent]:
        return [self.sample_legitimate_event() for _ in range(n)]

    # ------------------------------------------------------------------
    # Attacker / account-takeover behaviour
    # ------------------------------------------------------------------
    def sample_attacker_event(self, subtle: bool = False) -> BehaviouralEvent:
        """Simulate a session where the credentials/session are valid
        (i.e. this event would pass ordinary authentication) but the
        underlying human behaviour differs from the account owner's
        Digital DNA.

        subtle=True produces a harder case with deviation in fewer
        dimensions, to demonstrate why single-signal rules would miss it.
        """
        rng = self._rng
        when = datetime.now() - timedelta(minutes=rng.uniform(0, 60))

        if subtle:
            # Deviates strongly in only 1-2 dimensions; the rest looks close
            # to normal. Multi-feature analysis is what catches this.
            amount = max(50.0, rng.gauss(self.amount_mean * rng.uniform(2.2, 3.5), self.amount_std))
            recipient = rng.choice(self.trusted_recipients) if rng.random() < 0.5 else _fake_wallet("NEW")
            hour = rng.choice(self.typical_hours)
            ts = when.replace(hour=hour)
            mouse_speed = max(10.0, rng.gauss(self.mouse_speed_mean, self.mouse_speed_std * 1.3))
            typing_speed = max(10.0, rng.gauss(self.typing_speed_mean, self.typing_speed_std * 1.4))
            session_duration = max(20.0, rng.gauss(self.session_duration_mean * 0.8, self.session_duration_std))
            click_interval = max(0.03, rng.gauss(self.click_interval_mean, self.click_interval_std * 1.5))
            keystroke_var = max(0.001, rng.gauss(self.keystroke_var_mean, self.keystroke_var_std * 1.5))
        else:
            # Overt account-takeover pattern: deviates across most channels.
            amount = max(50.0, rng.gauss(self.amount_mean * rng.uniform(4.0, 8.0), self.amount_std * 2))
            recipient = _fake_wallet("NEW")
            off_hour = rng.choice([h for h in range(24) if h not in range(min(self.typical_hours) - 2, max(self.typical_hours) + 3)])
            ts = when.replace(hour=off_hour, minute=rng.randint(0, 59))
            mouse_speed = max(5.0, rng.gauss(self.mouse_speed_mean * rng.choice([0.4, 2.1]), self.mouse_speed_std * 2.5))
            typing_speed = max(5.0, rng.gauss(self.typing_speed_mean * rng.choice([0.5, 1.9]), self.typing_speed_std * 2.5))
            session_duration = max(10.0, rng.gauss(self.session_duration_mean * 0.3, self.session_duration_std))
            click_interval = max(0.02, rng.gauss(self.click_interval_mean * 2.5, self.click_interval_std * 2))
            keystroke_var = max(0.001, rng.gauss(self.keystroke_var_mean * 3.0, self.keystroke_var_std * 2))

        return BehaviouralEvent(
            user_id=self.user_id,
            amount=round(amount, 2),
            recipient=recipient,
            timestamp=ts,
            session_duration=session_duration,
            mouse_speed_mean=mouse_speed,
            mouse_speed_variance=abs(rng.gauss(45.0, 15.0)),
            click_interval_mean=click_interval,
            typing_speed_mean=typing_speed,
            keystroke_interval_variance=keystroke_var,
            label="attacker",
        )

    # ------------------------------------------------------------------
    # Named demo scenarios (used by the "Live Attack Demo" button)
    # ------------------------------------------------------------------
    def scenario_legitimate(self) -> BehaviouralEvent:
        rng = self._rng
        when = datetime.now().replace(hour=rng.choice(self.typical_hours), minute=rng.randint(0, 59))
        return BehaviouralEvent(
            user_id=self.user_id,
            amount=round(max(50.0, rng.gauss(self.amount_mean * 0.9, self.amount_std * 0.4)), 2),
            recipient=self.trusted_recipients[0],
            timestamp=when,
            session_duration=max(60.0, rng.gauss(self.session_duration_mean, self.session_duration_std * 0.5)),
            mouse_speed_mean=rng.gauss(self.mouse_speed_mean, self.mouse_speed_std * 0.5),
            mouse_speed_variance=abs(rng.gauss(15.0, 3.0)),
            click_interval_mean=rng.gauss(self.click_interval_mean, self.click_interval_std * 0.5),
            typing_speed_mean=rng.gauss(self.typing_speed_mean, self.typing_speed_std * 0.5),
            keystroke_interval_variance=max(0.001, rng.gauss(self.keystroke_var_mean, self.keystroke_var_std * 0.5)),
            label="legitimate",
        )

    def scenario_account_takeover(self) -> BehaviouralEvent:
        return self.sample_attacker_event(subtle=False)


def new_demo_user(user_id: str = "USR001", seed: int = 7) -> UserBehaviourGenerator:
    """Factory for the default hackathon-demo user with fixed, reproducible
    habits (so the demo behaves the same way every rehearsal)."""
    return UserBehaviourGenerator(user_id=user_id, seed=seed)
