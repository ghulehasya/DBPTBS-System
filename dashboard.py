"""
DBPTBS - Security Dashboard (Streamlit)
------------------------------------------
Run with:  streamlit run dashboard.py

This dashboard calls app.engine directly (the same orchestration module
the FastAPI backend uses) rather than making HTTP calls to the API. For a
live hackathon demo this means one process, zero network flakiness, and
the numbers on screen are guaranteed to be exactly what the engine
computed - nothing here is a hand-set UI value.
"""

from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import streamlit as st

from app import database as db
from app import engine

USER_ID = "USR001"

st.set_page_config(
    page_title="DBPTBS Security Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
:root {
    --dbptbs-bg: #0b0f14;
    --dbptbs-card: #131a22;
    --dbptbs-border: #1f2a35;
    --dbptbs-green: #22c55e;
    --dbptbs-yellow: #eab308;
    --dbptbs-red: #ef4444;
    --dbptbs-accent: #38bdf8;
}
.stApp { background-color: var(--dbptbs-bg); }
h1, h2, h3, h4 { color: #e6edf3 !important; }
.dbptbs-card {
    background: var(--dbptbs-card);
    border: 1px solid var(--dbptbs-border);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem;
}
.dbptbs-badge {
    display: inline-block;
    padding: 0.15rem 0.7rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.85rem;
}
.badge-low { background: rgba(34,197,94,0.15); color: var(--dbptbs-green); border: 1px solid var(--dbptbs-green); }
.badge-medium { background: rgba(234,179,8,0.15); color: var(--dbptbs-yellow); border: 1px solid var(--dbptbs-yellow); }
.badge-high { background: rgba(239,68,68,0.15); color: var(--dbptbs-red); border: 1px solid var(--dbptbs-red); }
.dbptbs-reason { color: #f87171; margin: 0.15rem 0; }
.dbptbs-mono { font-family: "JetBrains Mono", monospace; color: #94a3b8; font-size: 0.85rem; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def badge(decision: str) -> str:
    cls = {"LOW": "badge-low", "MEDIUM": "badge-medium", "HIGH": "badge-high"}[decision]
    icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}[decision]
    return f'<span class="dbptbs-badge {cls}">{icon} {decision} RISK</span>'


# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------
if "bootstrapped" not in st.session_state:
    engine.get_session(USER_ID)
    st.session_state.bootstrapped = True
if "last_outcome" not in st.session_state:
    st.session_state.last_outcome = None
if "attack_outcome" not in st.session_state:
    st.session_state.attack_outcome = None

session = engine.get_session(USER_ID)

st.sidebar.markdown("## 🛡️ DBPTBS")
st.sidebar.caption("DNA Behavioural Pre-Transaction Blockchain Security System")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Digital DNA", "Transaction Simulator", "🚨 Live Attack Demo", "Blockchain Explorer", "Security Events"],
)
st.sidebar.divider()
st.sidebar.caption(f"Demo user: **{USER_ID}**")
st.sidebar.caption(f"Baseline built from **{session.dna.sample_count}** historical events")
if st.sidebar.button("↻ Reset demo session"):
    engine.reset_session(USER_ID)
    st.session_state.last_outcome = None
    st.session_state.attack_outcome = None
    st.rerun()

st.sidebar.divider()
st.sidebar.caption(
    "⚠️ Prototype: simulated wallets, synthetic behavioural data, and a local "
    "blockchain simulator. No real financial accounts are involved."
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("DBPTBS Security Console")
    st.caption("“Don't just verify where the money is going. Verify who is actually sending it.”")

    stats = engine.get_stats(USER_ID)
    status_label = "🟢 PROTECTED" if stats["current_risk"] < 70 else "🔴 ALERT"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("System Status", status_label)
    c2.metric("Trust Score", f"{stats['trust_score']:.0f}/100")
    c3.metric("Current Risk", f"{stats['current_risk']:.0f}/100")
    c4.metric("Transactions Protected", stats["protected_count"])
    c5.metric("Blocked", stats["blocked"])

    st.markdown("### Transaction Monitor")
    txs = db.list_transactions(sender=USER_ID, limit=25)
    if txs:
        df = pd.DataFrame(txs)[["timestamp", "amount", "recipient", "risk_score", "status"]]
        df["risk_score"] = df["risk_score"].round(1)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet. Try the **Transaction Simulator** or **Live Attack Demo** in the sidebar.")

# ---------------------------------------------------------------------------
# Digital DNA
# ---------------------------------------------------------------------------
elif page == "Digital DNA":
    st.title("Digital DNA Profile")
    st.caption(f"Behavioural baseline for {USER_ID}, derived from {session.dna.sample_count} historical events.")

    last_assessment = st.session_state.last_outcome.assessment if st.session_state.last_outcome else None
    pattern = engine.get_dna_visualization(USER_ID, last_assessment)
    similarity = last_assessment.behavioural_similarity_pct if last_assessment else 100.0

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown("#### Pattern Match (vs. most recent analyzed transaction)")
        for label, pct in pattern.items():
            st.write(f"**{label}**  —  {pct}%")
            st.progress(min(max(pct / 100, 0.0), 1.0))
    with col_right:
        st.markdown("#### Behavioural Similarity")
        st.metric("Overall match to baseline", f"{similarity}%")
        if last_assessment is None:
            st.caption("No transaction analyzed yet — showing a clean baseline (100% by definition).")

    st.markdown("#### Baseline statistics (derived from history, not hard-coded)")
    d1, d2, d3 = st.columns(3)
    d1.metric("Typical amount", f"₹{session.dna.amount_mean:,.0f}", f"±{session.dna.amount_std:,.0f}")
    d2.metric("Typical hours", ", ".join(f"{h:02d}:00" for h in session.dna.typical_hours))
    d3.metric("Avg. transactions/day", f"{session.dna.avg_tx_per_day:.1f}")
    st.markdown("**Trusted recipients:**")
    st.code("\n".join(session.dna.trusted_recipients), language=None)

# ---------------------------------------------------------------------------
# Transaction Simulator
# ---------------------------------------------------------------------------
elif page == "Transaction Simulator":
    st.title("Transaction Simulator")

    with st.form("tx_form"):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount (₹)", min_value=1.0, value=float(round(session.dna.amount_mean)), step=100.0)
            profile_choice = st.radio("Behaviour Profile", ["Legitimate User", "Suspicious Attacker"], horizontal=True)
        with col2:
            recipient_choice = st.selectbox(
                "Recipient Wallet",
                options=session.dna.trusted_recipients + ["<new / unseen wallet>"],
            )
            tx_time = st.time_input("Transaction Time", value=datetime.now().time())
        submitted = st.form_submit_button("ANALYZE TRANSACTION", use_container_width=True)

    if submitted:
        recipient = recipient_choice
        if recipient == "<new / unseen wallet>":
            import uuid
            recipient = f"WALLET_NEW_{uuid.uuid4().hex[:6].upper()}"

        profile = "legitimate" if profile_choice == "Legitimate User" else "attacker"
        when = datetime.now().replace(hour=tx_time.hour, minute=tx_time.minute)

        progress_box = st.empty()
        for step in ["Analyzing Digital DNA...", "Extracting behavioural features...",
                     "Calculating behavioural similarity...", "Generating risk score..."]:
            progress_box.info(step)
            time.sleep(0.35)
        progress_box.empty()

        if profile == "attacker":
            outcome = engine.run_scenario_attack(USER_ID)
        else:
            outcome = engine.analyze_and_decide(
                USER_ID, amount=amount, recipient=recipient, when=when, behaviour_profile=profile,
            )
        st.session_state.last_outcome = outcome

    if st.session_state.last_outcome is not None:
        outcome = st.session_state.last_outcome
        a = outcome.assessment
        st.markdown("---")
        st.markdown(f"### Result  &nbsp; {badge(a.decision)}", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Risk Score", f"{a.risk_score:.0f}/100")
        m2.metric("Behavioural Similarity", f"{a.behavioural_similarity_pct}%")
        m3.metric("Decision", "✅ APPROVED" if outcome.status == "APPROVED" else (
            "⏸ HELD" if outcome.status == "HELD_FOR_VERIFICATION" else "⛔ BLOCKED"
        ))

        st.markdown("#### Contributing factors")
        if a.reasons:
            for r in a.reasons:
                st.markdown(f'<div class="dbptbs-reason">❌ {r}</div>', unsafe_allow_html=True)
        else:
            st.markdown("✅ No significant behavioural deviation detected.")

        with st.expander("Full risk breakdown (from the engine, not hand-set)"):
            comp_df = pd.DataFrame([{
                "Component": c.label, "Unit score (0-1)": round(c.unit_score, 2),
                "Weight": c.weight, "Contribution (pts)": round(c.contribution, 1),
            } for c in a.components])
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

        if outcome.status == "HELD_FOR_VERIFICATION":
            st.warning("🚨 HIGH RISK — transaction held pending additional verification.")
            st.caption("Prototype step-up authentication (demo OTP, never transmitted anywhere real).")
            st.code(f"DEMO OTP: {outcome.otp_code_for_demo}", language=None)
            code_input = st.text_input("Enter verification code", key="verify_code_sim")
            if st.button("Verify identity", key="verify_btn_sim"):
                result = engine.verify_and_release(USER_ID, outcome.tx_id, code_input)
                if result["verified"]:
                    st.success(f"{result['message']} → added to blockchain as block #{result['block_index']}.")
                else:
                    st.error(result["message"])

# ---------------------------------------------------------------------------
# Live Attack Demo
# ---------------------------------------------------------------------------
elif page == "🚨 Live Attack Demo":
    st.title("🚨 Live Attack Simulation")
    st.caption("Simulates an account takeover: valid credentials, valid wallet, legitimate-looking recipient — but the human behind the keyboard has changed.")

    if st.button("🚨 LAUNCH ATTACK SIMULATION", type="primary", use_container_width=True):
        steps = [
            ("Attacker obtained valid account credentials.", None),
            ("Credentials check", "✓ Valid"),
            ("Wallet check", "✓ Valid"),
            ("Recipient check", "✓ Legitimate-looking wallet"),
            ("Traditional authentication", "✓ Passed"),
            ("DBPTBS behavioural analysis", "❌ Running..."),
        ]
        box = st.empty()
        for label, val in steps:
            box.info(f"{label}{': ' + val if val else ''}")
            time.sleep(0.3)
        box.empty()

        outcome = engine.run_scenario_attack(USER_ID)
        st.session_state.attack_outcome = outcome

    if st.session_state.attack_outcome is not None:
        outcome = st.session_state.attack_outcome
        a = outcome.assessment
        st.markdown("---")
        st.markdown("#### DBPTBS behavioural analysis: ❌ FAILED")
        m1, m2 = st.columns(2)
        m1.metric("Risk Score", f"{a.risk_score:.0f}/100")
        m2.metric("Behavioural Similarity", f"{a.behavioural_similarity_pct}%")
        st.markdown(f"### {badge(a.decision)}", unsafe_allow_html=True)

        st.markdown("**Why this was flagged:**")
        for r in a.reasons:
            st.markdown(f'<div class="dbptbs-reason">❌ {r}</div>', unsafe_allow_html=True)

        if outcome.status == "HELD_FOR_VERIFICATION":
            st.error("ACTION: TRANSACTION BLOCKED — additional verification required before this can reach the blockchain.")
            st.code(f"DEMO OTP: {outcome.otp_code_for_demo}", language=None)
            code_input = st.text_input("Enter verification code to simulate the true owner regaining control", key="verify_code_attack")
            if st.button("Verify identity", key="verify_btn_attack"):
                result = engine.verify_and_release(USER_ID, outcome.tx_id, code_input)
                if result["verified"]:
                    st.success(f"{result['message']} → added to blockchain as block #{result['block_index']}.")
                else:
                    st.error(result["message"])
        else:
            st.info(f"This attack sample scored {a.decision} risk and was allowed through — try again, "
                    "synthetic attacker sampling has natural variance across runs.")

# ---------------------------------------------------------------------------
# Blockchain Explorer
# ---------------------------------------------------------------------------
elif page == "Blockchain Explorer":
    st.title("Blockchain Explorer")
    st.caption("A transaction only ever enters this chain AFTER DBPTBS (and, if required, step-up verification) approves it.")

    ok, err = session.blockchain.is_valid()
    c1, c2 = st.columns(2)
    c1.metric("Chain length", len(session.blockchain.chain))
    c2.metric("Chain valid", "✅ YES" if ok else "❌ NO")
    if not ok:
        st.error(err)

    if st.button("Re-validate chain"):
        st.rerun()

    for block in reversed(session.blockchain.chain):
        title = f"Block #{block.index} — {block.block_hash[:12]}…"
        with st.expander(title):
            st.markdown(f'<span class="dbptbs-mono">previous_hash: {block.previous_hash[:24]}…</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="dbptbs-mono">block_hash: &nbsp;&nbsp;{block.block_hash[:24]}…</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="dbptbs-mono">nonce: {block.nonce}</span>', unsafe_allow_html=True)
            st.json(block.transaction)

# ---------------------------------------------------------------------------
# Security Events
# ---------------------------------------------------------------------------
elif page == "Security Events":
    st.title("Security Events")
    events = db.list_security_events(limit=200)
    if events:
        df = pd.DataFrame(events)[["timestamp", "event_type", "risk_score", "description"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No security events logged yet.")
