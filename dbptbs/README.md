# DBPTBS
### DNA Behavioural Pre-Transaction Blockchain Security System

> "Don't just verify where the money is going. Verify who is actually sending it."

A behavioural risk-assessment and pre-transaction security layer that detects
deviations from a user's established behavioural profile and triggers
additional verification **before** a transaction is allowed to reach a
(simulated) blockchain.

**This is a 48-hour hackathon prototype.** Every wallet, transaction, and
behavioural sample in this repository is simulated or synthetically
generated. No real cryptocurrency network, private key, or financial
account is used anywhere.

---

## 1. Problem

A blockchain transaction can be cryptographically valid while still being
initiated by an attacker. If someone compromises a legitimate user's
credentials, session, or device, they can pass:

- recipient verification (the destination wallet is real),
- wallet/session authentication (the credentials are valid),
- transaction cryptographic validation (the signature checks out),

...and still not be the account owner. Traditional security stacks stop
checking at that point. DBPTBS adds one more question before the money
moves: **does the behaviour behind this transaction match the account
owner's behavioural DNA?**

## 2. Solution

DBPTBS sits in front of transaction execution and evaluates:

```
ACCOUNT VALIDITY + RECIPIENT RISK + TRANSACTION RISK + BEHAVIOURAL CONSISTENCY
```

It builds a per-user behavioural baseline ("Digital DNA") from historical
transaction, session, and interaction data, scores every new transaction
attempt against that baseline using a statistical + machine-learning
ensemble, and produces an explainable 0-100 risk score. Low/medium risk
transactions proceed to the (simulated) blockchain; high-risk transactions
are held and require a step-up verification before release.

## 3. Architecture

```
dbptbs/
├── app/
│   ├── main.py                 # FastAPI app + startup wiring
│   ├── config.py                # thresholds, weights, paths (no secrets)
│   ├── database.py               # sqlite3 persistence layer
│   ├── models.py                 # Pydantic API schemas
│   ├── engine.py                  # orchestrates the full pipeline (used by API + dashboard)
│   ├── api/
│   │   └── routes.py              # HTTP endpoints (thin - delegates to engine.py)
│   └── services/
│       ├── synthetic_data.py       # synthetic behavioural data generator
│       ├── dna_engine.py            # Digital DNA derivation + adaptive baseline
│       ├── anomaly_detector.py       # Isolation Forest + statistical z-scores
│       ├── risk_engine.py             # weighted, explainable risk scoring
│       ├── auth_challenge.py           # simulated step-up verification (demo OTP)
│       └── blockchain.py                # toy proof-of-work blockchain simulator
├── dashboard.py                  # Streamlit security console (primary demo UI)
├── tests/
│   ├── test_dbptbs.py             # core engine/service tests (stdlib unittest)
│   └── test_api.py                 # FastAPI endpoint tests (needs fastapi+httpx)
├── data/                          # sqlite3 database lives here at runtime
├── requirements.txt
├── run.py                          # convenience runner for the API
└── README.md
```

**Why this shape:** the engine (`app/engine.py`) is the *only* place the
pipeline is implemented. Both the FastAPI routes and the Streamlit
dashboard call into it, so there is exactly one risk-scoring code path -
no divergence between "what the API says" and "what the dashboard shows."

## 4. Features

- Digital DNA derived from historical behavioural data (never hard-coded)
- Explainable risk scoring: every point of the 0-100 score traces back to a
  named, weighted component
- Ensemble anomaly detection: per-feature z-scores (statistical,
  transparent) + Isolation Forest (multivariate, catches combinations no
  single rule would flag)
- Adaptive baseline that tolerates legitimate behavioural drift, but only
  from transactions that were themselves scored low-risk
- Toy blockchain with real SHA-256 hash-chaining, proof-of-work, and
  tamper detection
- Simulated step-up authentication (demo OTP) for held transactions
- A dedicated attack-simulation button for a reliable, repeatable demo

## 5. How Digital DNA works

`app/services/dna_engine.py::build_digital_dna()` takes a list of historical
behavioural events and derives, purely from the data:

- mean/std of transaction amount
- the busiest activity hours (by actual frequency, not an assumption)
- average transactions per day (from the real time span of the history)
- which recipients are "trusted" (paid ≥3 times) vs merely "seen"
- mean/std of session duration, mouse speed/variance, click interval,
  typing speed, and keystroke-interval variance

`adapt_baseline()` lets the DNA drift gradually via an exponential moving
average - but **only** after several consecutive *low-risk* observations,
and the caller (the engine) is the only code allowed to decide something
was low-risk. This is the mitigation for baseline poisoning: a single
high-risk session, even from a real attacker, can never move the baseline.

## 6. Risk scoring

`app/services/risk_engine.py::assess_transaction()` combines eight
components, each already 0-100 after weighting:

| Component | What it measures | Weight |
|---|---|---|
| Transaction Amount | z-score of amount vs. baseline | 24% |
| Recipient Novelty | trusted / seen-once / never-seen | 18% |
| Time Anomaly | distance from typical active hours | 12% |
| Session Behaviour | session-duration z-score | 10% |
| Mouse Behaviour | mouse speed/variance/click-interval z-scores | 8% |
| Typing Behaviour | typing-speed/keystroke-variance z-scores | 8% |
| Transaction Velocity | tx count in last 24h vs. expected | 10% |
| ML Ensemble Signal | Isolation Forest anomaly score | 10% |

Weights sum to 1.0 (enforced by a unit test). Thresholds: **0-30 LOW · 31-70
MEDIUM · 71-100 HIGH**. Every non-trivial component also produces a
human-readable reason string, sorted by contribution, which is exactly what
the UI displays - there is no separate, hand-authored explanation layer.

## 7. Machine-learning approach

An `IsolationForest` (scikit-learn) is fit per-user on their own historical
feature vectors (amount, hour, session duration, mouse speed/variance,
click interval, typing speed, keystroke-interval variance), after scaling
by that user's own mean/std (so "anomalous" is always relative to *that*
person, not a global population). Its `decision_function` output is
calibrated into a 0-1 anomaly score using the min/max of the training
distribution. This ML signal is blended with (not a replacement for) the
statistical z-score components, per the "ensemble" requirement - if the ML
model is ever unavailable (e.g. too little history), the engine falls back
to a purely statistical estimate rather than failing closed or open
silently.

## 8. Blockchain simulator

`app/services/blockchain.py` is a minimal educational chain: each `Block`
hashes its index, timestamp, previous block's hash, and transaction hash
with SHA-256, subject to a small proof-of-work difficulty. `is_valid()`
recomputes every hash and checks linkage, catching any tampering.
**Transactions only ever enter this chain after DBPTBS approves them** (or
after step-up verification releases a held one) - this is what
"pre-transaction security" means in this project. It is not a distributed
ledger and has no peer-to-peer network; see Limitations.

## 9. Attack simulation

The sidebar's **🚨 Live Attack Demo** page (and `POST /simulation/attack`)
generates an account-takeover-style event from the same per-user generator:
a valid-looking recipient, but amount/time/mouse/typing/session values
drawn from a deliberately different distribution. It is scored by the exact
same pipeline as any other transaction - nothing about the scoring path is
special-cased for the demo button.

## 10. Installation

```bash
# from the project root
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 11. Running the application

**Dashboard (primary demo surface):**
```bash
streamlit run dashboard.py
```

**API (in a separate terminal, optional but part of the required architecture):**
```bash
python run.py
# or: uvicorn app.main:app --reload --port 8000
```
Interactive API docs: http://localhost:8000/docs

The dashboard calls the shared engine directly (not over HTTP), so it works
standalone even if you never start the API - useful if your demo laptop's
Wi-Fi is unreliable on stage.

## 12. API documentation

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Load/bootstrap a user's Digital DNA session |
| GET | `/behavior/profile/{user_id}` | Digital DNA + pattern-match view |
| POST | `/transaction/analyze` | Run the full pipeline on a transaction |
| POST | `/transaction/verify` | Submit a step-up verification code |
| GET | `/transactions` | List recorded transactions |
| GET | `/security/events` | List security events |
| GET | `/blockchain/{user_id}` | Full chain + validity |
| GET | `/blockchain/{user_id}/validate` | Validity check only |
| POST | `/simulation/attack` | Trigger the account-takeover demo scenario |
| GET | `/dashboard/stats/{user_id}` | Summary counters for the dashboard |

Full request/response schemas are in `app/models.py` and served live at
`/docs`.

## 13. Project structure

See section 3 above.

## 14. Security considerations

- **No raw biometrics stored.** Only derived statistics (mean/variance of
  mouse speed, typing speed, keystroke intervals) are ever persisted -
  never raw mouse trajectories or keystrokes.
- Behavioural biometrics are sensitive data. A production deployment must
  apply data minimization, encryption at rest and in transit, access
  control, a defined retention policy, explicit user consent, and secure
  model storage.
- The demo OTP in `auth_challenge.py` is shown directly in the API
  response/UI **for demo purposes only**. A real system would deliver it
  over a genuine out-of-band channel and never return it in an API
  response.

## 15. Limitations

**DBPTBS does not mathematically prove that the current user is the
account owner.** It estimates whether current behaviour is *consistent*
with the established behavioural profile. A high anomaly score indicates
elevated risk, not definitive proof of compromise. Known limitations:

- **False positives**: legitimate behavioural drift (new device, injury
  affecting typing, being in a hurry) can be flagged.
- **False negatives**: a patient, well-resourced attacker who studies the
  victim's habits could partially imitate them.
- **Behavioural drift / concept drift**: habits genuinely change over time;
  the adaptive baseline mitigates but does not eliminate this.
- **Device changes**: a new phone/mouse/keyboard changes interaction
  telemetry through no fault of the user.
- **Accessibility**: assistive technologies can produce interaction
  patterns that differ from an "average" baseline; thresholds must be
  tuned per-user, not globally.
- **Shared devices / shared accounts**: multiple legitimate people using
  one account will look like "drift" or "anomaly" to this model.
- **Adversarial imitation**: behavioural biometrics are not unforgeable.
- **Insufficient historical data**: a brand-new account has no reliable
  baseline; the engine falls back to weaker statistical-only scoring until
  enough history accumulates.
- **Model poisoning**: mitigated (not eliminated) by only adapting the
  baseline from already-low-risk events.
- **Privacy risk**: behavioural telemetry can itself be sensitive; see
  Security Considerations.

We explicitly do **not** claim "100% hacker detection," "impossible to
bypass," "guaranteed identity verification," "zero false positives," or
that "blockchain makes the system completely secure." None of these claims
are true of this system or any behavioural-biometrics system.

## 16. Threat model (summary)

| Threat | Mitigated by DBPTBS? | Notes |
|---|---|---|
| Stolen credentials | Yes (partially) | Behaviour still doesn't match → held for verification |
| Session hijacking | Yes (partially) | Same mechanism as above |
| Compromised device | Partially | Interaction telemetry may still look anomalous |
| Insider misuse | Limited | If the insider *is* the legitimate user, behaviour matches |
| Behavioural mimicry | Limited | Sophisticated imitation can reduce detection |
| Model poisoning | Mitigated | Only low-risk events adapt the baseline |
| Replay attacks | Not addressed here | Needs nonce/replay protection at the transaction-signing layer |
| Transaction manipulation | Not addressed here | Needs cryptographic integrity at the wallet/signing layer |
| API abuse | Partially | Needs rate limiting/auth in front of the API in production |

## 17. Future improvements

- Mahalanobis-distance scoring using the full feature covariance matrix
  (currently we use per-feature z-scores plus a separate Isolation Forest,
  rather than a single joint Mahalanobis distance)
- Federated/differential-privacy training so raw behavioural statistics
  never leave the user's device
- Continuous (not just pre-transaction) risk scoring during a session
- A real, persisted, cross-restart trained-model store instead of the
  current in-memory per-process session
- Multi-device / multi-context baselines (phone vs. desktop) instead of one
  merged profile

## 18. Hackathon demo flow (2-3 minutes)

1. Open the **Overview** tab - point out "PROTECTED" status and trust score.
2. Open **Digital DNA** - explain it was derived from ~150 synthetic
   historical events, not hand-typed.
3. Go to **Transaction Simulator**, submit a normal-looking transaction as
   *Legitimate User* → LOW risk, approved instantly.
4. Switch to **🚨 Live Attack Demo**, click the button. Walk through:
   credentials valid → wallet valid → recipient legitimate-looking →
   traditional auth passed → DBPTBS behavioural analysis **failed** → risk
   score ~85-95 → HIGH risk → blocked pending verification.
5. Point out the itemized "why" list (amount 8-9x normal, unseen recipient,
   off-hours, mouse/typing deviation).
6. Enter the demo OTP shown on screen → transaction releases → show it
   landing as a new block in the **Blockchain Explorer**, and click
   "Re-validate chain" to show hash-chain integrity.

## Demo credentials

This is a prototype with no real login system. The default demo user is:

```
user_id: USR001
```

No password is needed to view the dashboard. Step-up "OTP" codes are
generated fresh per held transaction and shown directly on screen (see
Security Considerations - this is explicitly not how a production OTP
flow would work).

## Testing

```bash
# Core engine/service tests - stdlib only, no extra install needed
python -m unittest discover -s tests -v

# Full suite including API endpoint tests (needs fastapi + httpx installed)
python -m pytest tests/ -v
```

## Future version: real blockchain integration

This prototype intentionally never touches a real chain. A future version
could integrate with real infrastructure by:

1. Keeping DBPTBS as a **pre-signing gate** in the wallet/client, not part
   of consensus - it decides whether to *ask the user to sign* or *hold for
   step-up verification*, never trying to alter transaction validity rules.
2. Emitting its risk assessment as a signed, auditable attestation that a
   wallet UI or custodial backend can require before releasing a signature.
3. Replacing the toy proof-of-work chain with a real testnet (e.g. an EVM
   testnet) purely as the execution target once a transaction is approved.
4. Moving behavioural feature storage to on-device or federated storage,
   so raw telemetry never has to be centrally collected at all.
5. Replacing the demo OTP with a real out-of-band step-up channel
   (authenticator app push, hardware key, etc).

None of this is implemented here; this repository is a self-contained,
safe simulation.
