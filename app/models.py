"""
DBPTBS - API Schemas (Pydantic)
----------------------------------
Request/response models for the FastAPI layer. Kept separate from the
internal dataclasses in app/services/* so the wire format can evolve
independently of the engine's internal representation.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_id: str = Field(..., examples=["USR001"])


class LoginResponse(BaseModel):
    user_id: str
    trust_score: float
    message: str


class TransactionAnalyzeRequest(BaseModel):
    user_id: str = Field(..., examples=["USR001"])
    amount: float = Field(..., gt=0)
    recipient: str
    behaviour_profile: str = Field(
        "legitimate", description="'legitimate' or 'attacker' - simulation control for the hackathon demo only."
    )
    timestamp: Optional[datetime] = None


class RiskComponentOut(BaseModel):
    name: str
    label: str
    unit_score: float
    weight: float
    contribution: float
    reason: Optional[str] = None


class TransactionAnalyzeResponse(BaseModel):
    tx_id: str
    status: str
    risk_score: float
    decision: str
    behavioural_similarity_pct: float
    components: List[RiskComponentOut]
    reasons: List[str]
    otp_code_for_demo: Optional[str] = Field(
        None, description="PROTOTYPE ONLY: a real system would deliver this over an out-of-band channel, never in the API response."
    )


class TransactionVerifyRequest(BaseModel):
    user_id: str
    tx_id: str
    code: str


class TransactionVerifyResponse(BaseModel):
    verified: bool
    message: str
    block_index: Optional[int] = None


class DnaProfileResponse(BaseModel):
    user_id: str
    amount_mean: float
    amount_std: float
    typical_hours: List[int]
    avg_tx_per_day: float
    trusted_recipients: List[str]
    sample_count: int
    updated_at: str
    pattern_match: dict


class BlockOut(BaseModel):
    index: int
    timestamp: float
    previous_hash: str
    transaction: dict
    transaction_hash: str
    nonce: int
    block_hash: str


class BlockchainResponse(BaseModel):
    valid: bool
    error: Optional[str]
    length: int
    blocks: List[BlockOut]


class SecurityEventOut(BaseModel):
    event_id: str
    user_id: str
    event_type: str
    risk_score: Optional[float]
    timestamp: str
    description: Optional[str]


class DashboardStatsResponse(BaseModel):
    protected_count: int
    approved: int
    suspicious: int
    blocked: int
    trust_score: float
    current_risk: float
