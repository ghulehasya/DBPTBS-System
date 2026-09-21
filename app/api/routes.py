"""
DBPTBS - API Routes
---------------------
Thin HTTP layer over app.engine. No business logic lives here; every
endpoint validates its request, calls the engine, and serializes the
result.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app import database as db
from app import engine
from app.models import (
    BlockchainResponse,
    BlockOut,
    DashboardStatsResponse,
    DnaProfileResponse,
    LoginRequest,
    LoginResponse,
    RiskComponentOut,
    SecurityEventOut,
    TransactionAnalyzeRequest,
    TransactionAnalyzeResponse,
    TransactionVerifyRequest,
    TransactionVerifyResponse,
)

router = APIRouter()

_last_assessment_by_user: dict = {}


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    session = engine.get_session(payload.user_id)
    stats = engine.get_stats(payload.user_id)
    return LoginResponse(
        user_id=payload.user_id,
        trust_score=stats["trust_score"],
        message=f"Digital DNA loaded for {payload.user_id} ({session.dna.sample_count} historical samples).",
    )


@router.get("/behavior/profile/{user_id}", response_model=DnaProfileResponse)
def get_profile(user_id: str):
    session = engine.get_session(user_id)
    last_assessment = _last_assessment_by_user.get(user_id)
    pattern_match = engine.get_dna_visualization(user_id, last_assessment)
    return DnaProfileResponse(
        user_id=user_id,
        amount_mean=round(session.dna.amount_mean, 2),
        amount_std=round(session.dna.amount_std, 2),
        typical_hours=session.dna.typical_hours,
        avg_tx_per_day=session.dna.avg_tx_per_day,
        trusted_recipients=session.dna.trusted_recipients,
        sample_count=session.dna.sample_count,
        updated_at=session.dna.updated_at,
        pattern_match=pattern_match,
    )


@router.post("/transaction/analyze", response_model=TransactionAnalyzeResponse)
def analyze_transaction(payload: TransactionAnalyzeRequest):
    if payload.behaviour_profile not in ("legitimate", "attacker"):
        raise HTTPException(400, "behaviour_profile must be 'legitimate' or 'attacker'")

    outcome = engine.analyze_and_decide(
        user_id=payload.user_id,
        amount=payload.amount,
        recipient=payload.recipient,
        when=payload.timestamp or datetime.now(),
        behaviour_profile=payload.behaviour_profile,
    )
    _last_assessment_by_user[payload.user_id] = outcome.assessment

    return TransactionAnalyzeResponse(
        tx_id=outcome.tx_id,
        status=outcome.status,
        risk_score=outcome.assessment.risk_score,
        decision=outcome.assessment.decision,
        behavioural_similarity_pct=outcome.assessment.behavioural_similarity_pct,
        components=[RiskComponentOut(**c.__dict__) for c in outcome.assessment.components],
        reasons=outcome.assessment.reasons,
        otp_code_for_demo=outcome.otp_code_for_demo,
    )


@router.post("/transaction/verify", response_model=TransactionVerifyResponse)
def verify_transaction(payload: TransactionVerifyRequest):
    result = engine.verify_and_release(payload.user_id, payload.tx_id, payload.code)
    return TransactionVerifyResponse(**result)


@router.get("/transactions")
def list_transactions(user_id: str = None, limit: int = 100):
    return db.list_transactions(sender=user_id, limit=limit)


@router.get("/security/events")
def security_events(limit: int = 100):
    events = db.list_security_events(limit=limit)
    return [SecurityEventOut(**e) for e in events]


@router.get("/blockchain/{user_id}", response_model=BlockchainResponse)
def get_blockchain(user_id: str):
    session = engine.get_session(user_id)
    ok, err = session.blockchain.is_valid()
    return BlockchainResponse(
        valid=ok, error=err, length=len(session.blockchain.chain),
        blocks=[BlockOut(**b.to_dict()) for b in session.blockchain.chain],
    )


@router.get("/blockchain/{user_id}/validate")
def validate_blockchain(user_id: str):
    session = engine.get_session(user_id)
    ok, err = session.blockchain.is_valid()
    return {"valid": ok, "error": err}


@router.post("/simulation/attack")
def simulate_attack(user_id: str = "USR001"):
    outcome = engine.run_scenario_attack(user_id)
    _last_assessment_by_user[user_id] = outcome.assessment
    return TransactionAnalyzeResponse(
        tx_id=outcome.tx_id,
        status=outcome.status,
        risk_score=outcome.assessment.risk_score,
        decision=outcome.assessment.decision,
        behavioural_similarity_pct=outcome.assessment.behavioural_similarity_pct,
        components=[RiskComponentOut(**c.__dict__) for c in outcome.assessment.components],
        reasons=outcome.assessment.reasons,
        otp_code_for_demo=outcome.otp_code_for_demo,
    )


@router.get("/dashboard/stats/{user_id}", response_model=DashboardStatsResponse)
def dashboard_stats(user_id: str):
    return DashboardStatsResponse(**engine.get_stats(user_id))
