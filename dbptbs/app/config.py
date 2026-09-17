"""
DBPTBS - Configuration
-----------------------
Central, non-secret configuration for the prototype. Nothing here is a
real credential. All values are safe defaults for a local demo.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "dbptbs.sqlite3"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Risk thresholds (0-100 normalized risk score)
# ---------------------------------------------------------------------------
RISK_LOW_MAX = 30
RISK_MEDIUM_MAX = 70
# score > RISK_MEDIUM_MAX  => HIGH

# ---------------------------------------------------------------------------
# Component weights for the overall risk score.
# These are intentionally explicit (not hidden inside a black box) so the
# scoring is auditable during a hackathon Q&A. They sum to 1.0.
# ---------------------------------------------------------------------------
RISK_WEIGHTS = {
    "transaction_amount": 0.24,
    "recipient": 0.18,
    "time": 0.12,
    "session": 0.10,
    "mouse": 0.08,
    "typing": 0.08,
    "velocity": 0.10,
    "ml_ensemble": 0.10,
}

# Minimum number of times a recipient must have been paid before it is
# considered "trusted" rather than merely "seen before".
TRUSTED_RECIPIENT_MIN_COUNT = 3

# Isolation Forest contamination estimate (expected fraction of anomalies
# in the training distribution used to calibrate the score, not a claim
# about real-world attack prevalence).
IFOREST_CONTAMINATION = 0.06
IFOREST_RANDOM_STATE = 42
IFOREST_N_ESTIMATORS = 150

# Adaptive baseline: only low-risk transactions may nudge the Digital DNA,
# and only after this many consecutive low-risk observations accumulate,
# so a single lucky transaction can't shift the baseline.
ADAPTIVE_BASELINE_MIN_OBSERVATIONS = 5
ADAPTIVE_BASELINE_LEARNING_RATE = 0.15  # exponential-moving-average weight

# Simulated additional-authentication settings (NOT real OTP/SMS - demo only)
DEMO_OTP_LENGTH = 6
DEMO_OTP_TTL_SECONDS = 300
DEMO_MAX_VERIFICATION_ATTEMPTS = 3

# Toy proof-of-work difficulty for the blockchain simulator. Kept tiny on
# purpose: this is a pedagogical chain-linkage demo, not a consensus system.
BLOCKCHAIN_DIFFICULTY_PREFIX = "00"
