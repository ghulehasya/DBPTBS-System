"""
DBPTBS - Additional Authentication (PROTOTYPE ONLY)
------------------------------------------------------
When a transaction is scored HIGH risk, it is held rather than blocked
outright, and a step-up challenge is issued. This module simulates that
challenge with a demo one-time code.

*** THIS IS NOT A REAL OTP/SMS/EMAIL SYSTEM. *** No code is ever
transmitted anywhere; it is generated and returned directly so the demo can
show it on-screen. In a production system this would be replaced by a real
out-of-band channel (authenticator app push, SMS via a vetted provider,
hardware key, etc).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, Optional

from app.config import DEMO_MAX_VERIFICATION_ATTEMPTS, DEMO_OTP_LENGTH, DEMO_OTP_TTL_SECONDS


@dataclass
class Challenge:
    code: str
    issued_at: float
    attempts_used: int = 0
    verified: bool = False

    def is_expired(self) -> bool:
        return (time.time() - self.issued_at) > DEMO_OTP_TTL_SECONDS


class DemoAuthChallengeStore:
    """In-memory store of outstanding step-up challenges, keyed by
    transaction id. A real system would persist this server-side with
    proper expiry and rate limiting; in-memory is sufficient for a
    single-process hackathon demo."""

    def __init__(self):
        self._challenges: Dict[str, Challenge] = {}

    def issue(self, transaction_id: str) -> Challenge:
        code = "".join(random.choices("0123456789", k=DEMO_OTP_LENGTH))
        challenge = Challenge(code=code, issued_at=time.time())
        self._challenges[transaction_id] = challenge
        return challenge

    def verify(self, transaction_id: str, submitted_code: str) -> tuple[bool, str]:
        challenge = self._challenges.get(transaction_id)
        if challenge is None:
            return False, "No outstanding verification challenge for this transaction."
        if challenge.verified:
            return True, "Already verified."
        if challenge.is_expired():
            return False, "Verification code expired. Request a new one."
        if challenge.attempts_used >= DEMO_MAX_VERIFICATION_ATTEMPTS:
            return False, "Maximum verification attempts exceeded. Transaction remains blocked."

        challenge.attempts_used += 1
        if submitted_code.strip() == challenge.code:
            challenge.verified = True
            return True, "Identity verified. Transaction released."
        remaining = DEMO_MAX_VERIFICATION_ATTEMPTS - challenge.attempts_used
        return False, f"Incorrect code. {remaining} attempt(s) remaining."

    def get(self, transaction_id: str) -> Optional[Challenge]:
        return self._challenges.get(transaction_id)


# Module-level singleton store shared by the API layer and the dashboard in
# this single-process demo.
demo_challenge_store = DemoAuthChallengeStore()
