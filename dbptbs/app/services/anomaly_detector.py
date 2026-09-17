"""
DBPTBS - Anomaly Detector
--------------------------
Two complementary signals, combined:

1. Per-feature z-scores against the Digital DNA (statistical, fully
   explainable - "amount is 4.1 standard deviations above your baseline").
2. An Isolation Forest trained on the user's own historical feature
   vectors (machine-learned, catches multivariate/combination anomalies
   that no single z-score would flag on its own).

Neither signal alone is treated as ground truth; the risk engine blends
both. This module deliberately never returns a bare "risk score" - it
returns the underlying numbers so the risk engine (and the UI) can show
its work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest

from app.config import IFOREST_CONTAMINATION, IFOREST_N_ESTIMATORS, IFOREST_RANDOM_STATE
from app.services.dna_engine import DigitalDNA, FEATURE_ORDER, event_to_vector


@dataclass
class AnomalyResult:
    z_scores: Dict[str, float]              # per-feature, signed
    ml_anomaly_score: float                 # 0-1, higher = more anomalous
    cosine_similarity: float                # -1..1, similarity to DNA centroid
    behavioural_similarity_pct: float       # 0-100, the headline "match %" number


class AnomalyDetector:
    """One instance per user. Fit once on that user's historical feature
    vectors; then score new events against it."""

    def __init__(self, dna: DigitalDNA):
        self.dna = dna
        self._scaler_mean = dna.feature_means()
        self._scaler_std = dna.feature_stds()
        self._iforest: IsolationForest | None = None
        self._train_scores_range = (0.0, 1.0)

    def _scale(self, vector: np.ndarray) -> np.ndarray:
        return (vector - self._scaler_mean) / self._scaler_std

    def fit(self, historical_vectors: List[np.ndarray]) -> "AnomalyDetector":
        X = np.vstack([self._scale(v) for v in historical_vectors])
        n = len(X)
        # IsolationForest needs a handful of samples to be meaningful; for a
        # very young profile we simply skip ML scoring (handled in .score).
        if n >= 10:
            self._iforest = IsolationForest(
                n_estimators=IFOREST_N_ESTIMATORS,
                contamination=IFOREST_CONTAMINATION,
                random_state=IFOREST_RANDOM_STATE,
            )
            self._iforest.fit(X)
            # Calibrate a min/max range from the *training* distribution so
            # raw decision_function output can be mapped into a stable 0-1
            # "anomaly score" instead of an arbitrary unbounded number.
            raw = self._iforest.decision_function(X)
            self._train_scores_range = (float(raw.min()), float(raw.max()))
        return self

    def score(self, feature_dict: dict) -> AnomalyResult:
        vector = event_to_vector(feature_dict)
        scaled = self._scale(vector)

        z_scores = {name: float(scaled[i]) for i, name in enumerate(FEATURE_ORDER)}

        centroid = np.zeros_like(scaled)  # in scaled space, the DNA mean is the origin
        denom = (np.linalg.norm(scaled) * np.linalg.norm(np.ones_like(scaled)) or 1.0)
        # Cosine similarity between the observed (scaled) deviation vector and
        # the "zero deviation" ideal is undefined at the origin; instead we
        # compute similarity between this event's scaled vector and the
        # historical mean deviation vector (which is ~0), expressed as a
        # bounded similarity via a distance-based transform below.
        euclidean_dev = float(np.linalg.norm(scaled))
        # Convert an unbounded multivariate deviation distance into a 0-100
        # "behavioural similarity" percentage using a smooth decay. At
        # euclidean_dev = 0 (perfectly on-baseline) -> 100%. Similarity
        # decays as deviation grows, asymptoting toward 0.
        behavioural_similarity_pct = float(100.0 * np.exp(-euclidean_dev / (2.0 * np.sqrt(len(FEATURE_ORDER)))))

        if self._iforest is not None:
            raw = float(self._iforest.decision_function(scaled.reshape(1, -1))[0])
            lo, hi = self._train_scores_range
            span = max(hi - lo, 1e-6)
            # decision_function: higher = more normal. Flip and clip to 0-1.
            ml_anomaly_score = float(np.clip((hi - raw) / span, 0.0, 1.0))
        else:
            # Not enough history yet to train ML; fall back to a
            # statistical-only stand-in so the ensemble weight isn't wasted.
            ml_anomaly_score = float(np.clip(euclidean_dev / (2.0 * np.sqrt(len(FEATURE_ORDER))), 0.0, 1.0))

        return AnomalyResult(
            z_scores=z_scores,
            ml_anomaly_score=ml_anomaly_score,
            cosine_similarity=float(1.0 - min(euclidean_dev, 2.0) / 2.0),
            behavioural_similarity_pct=round(behavioural_similarity_pct, 1),
        )


def build_and_fit_detector(dna: DigitalDNA, history: List[dict]) -> AnomalyDetector:
    vectors = [event_to_vector(h) for h in history]
    return AnomalyDetector(dna).fit(vectors)
