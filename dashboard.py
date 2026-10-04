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

# Wipes any leftover demo data from a previous run, exactly once per
# process lifetime (see app/database.py:ensure_fresh_start). This is what
# guarantees closing and reopening the dashboard always starts clean, and
# that a copy of this project handed to someone else never carries your
# transaction history with it.
db.ensure_fresh_start()

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
    --dbptbs-bg-alt: #0e141b;
    --dbptbs-card: #131a22;
    --dbptbs-border: #1f2a35;
    --dbptbs-green: #22c55e;
    --dbptbs-yellow: #eab308;
    --dbptbs-red: #ef4444;
    --dbptbs-accent: #38bdf8;
    --dbptbs-accent-soft: rgba(56,189,248,0.12);
    --dbptbs-text-dim: #94a3b8;
}

.stApp { background-color: var(--dbptbs-bg); }
h1, h2, h3, h4 { color: #e6edf3 !important; }
[data-testid="stSidebar"] { background-color: var(--dbptbs-bg-alt); border-right: 1px solid var(--dbptbs-border); }
[data-testid="stSidebar"] hr { border-color: var(--dbptbs-border); }

/* ---- Hero header --------------------------------------------------- */
.dbptbs-hero {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin-bottom: 0.15rem;
}
.dbptbs-hero-title { font-size: 1.9rem; font-weight: 700; color: #e6edf3; letter-spacing: 0.01em; }
.dbptbs-hero-rule {
    height: 3px;
    width: 100%;
    border-radius: 999px;
    margin: 0.55rem 0 1.3rem 0;
    background: linear-gradient(90deg, var(--dbptbs-accent) 0%, rgba(56,189,248,0.05) 65%, transparent 100%);
}
.dbptbs-live-dot {
    display: inline-block; width: 10px; height: 10px; border-radius: 50%;
    background: var(--dbptbs-green); margin-right: 8px; position: relative; top: -1px;
    box-shadow: 0 0 0 rgba(34,197,94,0.5);
    animation: dbptbs-pulse 1.8s infinite;
}
.dbptbs-live-dot.alert { background: var(--dbptbs-red); animation: dbptbs-pulse-red 1.2s infinite; }
@keyframes dbptbs-pulse {
    0% { box-shadow: 0 0 0 0 rgba(34,197,94,0.55); }
    70% { box-shadow: 0 0 0 8px rgba(34,197,94,0); }
    100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
}
@keyframes dbptbs-pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.55); }
    70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
    100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
}

/* ---- Generic card + badges ----------------------------------------- */
.dbptbs-card {
    background: var(--dbptbs-card);
    border: 1px solid var(--dbptbs-border);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem;
    transition: border-color 0.15s ease;
}
.dbptbs-card:hover { border-color: #2a3a4a; }
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
.dbptbs-mono { font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace; color: var(--dbptbs-text-dim); font-size: 0.85rem; }

/* ---- Streamlit metric tiles, restyled to match the console theme --- */
div[data-testid="stMetric"] {
    background: var(--dbptbs-card);
    border: 1px solid var(--dbptbs-border);
    border-radius: 12px;
    padding: 0.95rem 1.1rem 0.75rem 1.1rem;
    transition: border-color 0.15s ease, transform 0.15s ease;
}
div[data-testid="stMetric"]:hover { border-color: var(--dbptbs-accent); transform: translateY(-1px); }
div[data-testid="stMetricLabel"] { color: var(--dbptbs-text-dim) !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.04em; }
div[data-testid="stMetricValue"] { color: #e6edf3 !important; font-family: "JetBrains Mono", monospace; }

/* ---- Progress bars (Digital DNA pattern-match rows) ----------------- */
.stProgress > div > div > div > div { background: linear-gradient(90deg, var(--dbptbs-accent), #7dd3fc) !important; }

/* ---- Buttons ---------------------------------------------------------*/
.stButton > button {
    border-radius: 8px !important;
    border: 1px solid var(--dbptbs-border) !important;
}
.stButton > button:hover { border-color: var(--dbptbs-accent) !important; color: var(--dbptbs-accent) !important; }

/* ---- Blockchain "chain" visualization -------------------------------- */
.dbptbs-chain-row { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.9rem; }
.dbptbs-chain-node {
    font-family: "JetBrains Mono", monospace; font-size: 0.78rem;
    background: var(--dbptbs-accent-soft); color: var(--dbptbs-accent);
    border: 1px solid rgba(56,189,248,0.35); border-radius: 8px;
    padding: 0.3rem 0.6rem; white-space: nowrap;
}
.dbptbs-chain-node.genesis { background: rgba(148,163,184,0.12); color: var(--dbptbs-text-dim); border-color: var(--dbptbs-border); }
.dbptbs-chain-arrow { color: var(--dbptbs-text-dim); font-size: 1rem; }

/* ---- Sidebar system status line -------------------------------------- */
.dbptbs-sidebar-status {
    font-family: "JetBrains Mono", monospace; font-size: 0.78rem;
    color: var(--dbptbs-text-dim); line-height: 1.5;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def badge(decision: str) -> str:
    cls = {"LOW": "badge-low", "MEDIUM": "badge-medium", "HIGH": "badge-high"}[decision]
    icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}[decision]
    return f'<span class="dbptbs-badge {cls}">{icon} {decision} RISK</span>'


def hero(title: str, live: bool = True, alert: bool = False) -> None:
    """Page title with a small pulsing status dot and an accent underline,
    used at the top of every page instead of a plain st.title()."""
    dot = f'<span class="dbptbs-live-dot{" alert" if alert else ""}"></span>' if live else ""
    st.markdown(
        f'<div class="dbptbs-hero">{dot}<span class="dbptbs-hero-title">{title}</span></div>'
        f'<div class="dbptbs-hero-rule"></div>',
        unsafe_allow_html=True,
    )


def otp_reveal_box(otp_code: str, key_suffix: str) -> None:
    """Presents the step-up code as a simulated out-of-band push rather
    than printing it straight on screen. This is still a single-process
    demo (the code has to live somewhere the presenter can see it), but it
    reads as "check your device", not "here is the secret in plain view" -
    matching how the FastAPI layer now handles it via a separate
    GET /transaction/{tx_id}/demo-otp call instead of the analyze response."""
    st.markdown(
        '<div class="dbptbs-card">📲 <b>Simulated step-up push</b> sent to the registered device '
        '<span class="dbptbs-mono">(demo only — never a real SMS/authenticator send)</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("Check simulated device", key=f"reveal_otp_{key_suffix}"):
        st.session_state[f"otp_revealed_{key_suffix}"] = True
    if st.session_state.get(f"otp_revealed_{key_suffix}"):
        st.code(f"VERIFICATION CODE: {otp_code}", language=None)


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
st.sidebar.markdown(
    f'<div class="dbptbs-sidebar-status">'
    f'DEMO USER &nbsp;{USER_ID}<br>'
    f'BASELINE &nbsp;{session.dna.sample_count} events<br>'
    f'DATA &nbsp;wiped fresh on every restart'
    f'</div>',
    unsafe_allow_html=True,
)
st.sidebar.write("")
if st.sidebar.button("↻ Reset demo data", use_container_width=True):
    # Clears the in-memory session AND every row in the .sqlite3 file, so
    # the Overview / Security Events tables go back to empty too - not
    # just the regenerated Digital DNA baseline.
    db.wipe_all_data()
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
    stats = engine.get_stats(USER_ID)
    is_alert = stats["current_risk"] >= 70
    hero("DBPTBS Security Console", alert=is_alert)
    st.caption("“Don't just verify where the money is going. Verify who is actually sending it.”")

    status_label = "🔴 ALERT" if is_alert else "🟢 PROTECTED"

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
    hero("Digital DNA Profile", live=False)
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
    hero("Transaction Simulator", live=False)

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
            otp_reveal_box(outcome.otp_code_for_demo, key_suffix=outcome.tx_id)
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
    hero("🚨 Live Attack Simulation", alert=True)
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
            otp_reveal_box(outcome.otp_code_for_demo, key_suffix=outcome.tx_id)
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
    ok, err = session.blockchain.is_valid()
    hero("Blockchain Explorer", alert=not ok)
    st.caption("A transaction only ever enters this chain AFTER DBPTBS (and, if required, step-up verification) approves it.")

    c1, c2 = st.columns(2)
    c1.metric("Chain length", len(session.blockchain.chain))
    c2.metric("Chain valid", "✅ YES" if ok else "❌ NO")
    if not ok:
        st.error(err)

    if st.button("Re-validate chain"):
        st.rerun()

    # Compact "chain" strip: every block as a linked node, oldest → newest,
    # so the hash-linkage is something you can actually see at a glance
    # before drilling into any one block below.
    nodes = []
    for block in session.blockchain.chain:
        cls = "genesis" if block.index == 0 else ""
        label = "GENESIS" if block.index == 0 else f"#{block.index} {block.block_hash[:8]}…"
        nodes.append(f'<span class="dbptbs-chain-node {cls}">{label}</span>')
    chain_html = f'<span class="dbptbs-chain-arrow">→</span>'.join(nodes)
    st.markdown(f'<div class="dbptbs-chain-row">{chain_html}</div>', unsafe_allow_html=True)

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
    hero("Security Events", live=False)
    events = db.list_security_events(limit=200)
    if events:
        df = pd.DataFrame(events)[["timestamp", "event_type", "risk_score", "description"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No security events logged yet.")
