"""
DBPTBS - Automated Tests
---------------------------
Uses stdlib unittest (zero extra dependency to run these). Covers:
synthetic data generation, Digital DNA derivation + adaptive baseline,
anomaly detection, risk scoring (legitimate + attack scenarios), the
blockchain simulator (hashing, chain-validity, tamper detection), and the
simulated additional-authentication flow.

Run with:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from datetime import datetime

from app.services.synthetic_data import new_demo_user
from app.services.dna_engine import build_digital_dna, adapt_baseline, event_to_vector
from app.services.anomaly_detector import build_and_fit_detector
from app.services.risk_engine import assess_transaction
from app.services.blockchain import Blockchain, hash_transaction
from app.services.auth_challenge import DemoAuthChallengeStore
from app.config import ADAPTIVE_BASELINE_MIN_OBSERVATIONS


def _build_test_fixture(seed=1, n_history=150):
    gen = new_demo_user(user_id="TESTUSR", seed=seed)
    raw_history = gen.sample_history(n_history)
    history = [dict(**e.to_feature_dict(), recipient=e.recipient, timestamp=e.timestamp) for e in raw_history]
    dna = build_digital_dna("TESTUSR", history)
    detector = build_and_fit_detector(dna, history)
    return gen, history, dna, detector


class TestSyntheticData(unittest.TestCase):
    def test_legitimate_event_has_expected_fields(self):
        gen = new_demo_user(seed=1)
        ev = gen.sample_legitimate_event()
        self.assertEqual(ev.label, "legitimate")
        self.assertGreater(ev.amount, 0)
        feat = ev.to_feature_dict()
        for key in ["amount", "hour", "session_duration", "mouse_speed_mean",
                    "mouse_speed_variance", "click_interval_mean", "typing_speed_mean",
                    "keystroke_interval_variance"]:
            self.assertIn(key, feat)

    def test_attacker_event_labelled_correctly(self):
        gen = new_demo_user(seed=2)
        ev = gen.sample_attacker_event(subtle=False)
        self.assertEqual(ev.label, "attacker")

    def test_history_generation_length(self):
        gen = new_demo_user(seed=3)
        history = gen.sample_history(37)
        self.assertEqual(len(history), 37)


class TestDigitalDNA(unittest.TestCase):
    def test_dna_is_derived_not_hardcoded(self):
        _, history, dna, _ = _build_test_fixture(seed=10)
        amounts = [h["amount"] for h in history]
        self.assertAlmostEqual(dna.amount_mean, sum(amounts) / len(amounts), places=6)
        self.assertGreater(dna.sample_count, 0)
        self.assertTrue(len(dna.trusted_recipients) >= 1)
        self.assertTrue(len(dna.typical_hours) >= 1)

    def test_dna_rejects_empty_history(self):
        with self.assertRaises(ValueError):
            build_digital_dna("EMPTY", [])

    def test_adaptive_baseline_requires_min_observations(self):
        _, history, dna, _ = _build_test_fixture(seed=11)
        original_mean = dna.amount_mean
        for i in range(ADAPTIVE_BASELINE_MIN_OBSERVATIONS - 1):
            adapt_baseline(dna, {
                "amount": original_mean * 5, "hour": 12, "session_duration": 1,
                "mouse_speed_mean": 1, "typing_speed_mean": 1, "recipient": "X",
            })
        # Should not have shifted yet - not enough low-risk observations.
        self.assertAlmostEqual(dna.amount_mean, original_mean, places=6)

    def test_adaptive_baseline_shifts_after_min_observations(self):
        _, history, dna, _ = _build_test_fixture(seed=12)
        original_mean = dna.amount_mean
        for i in range(ADAPTIVE_BASELINE_MIN_OBSERVATIONS):
            adapt_baseline(dna, {
                "amount": original_mean * 5, "hour": 12, "session_duration": 1,
                "mouse_speed_mean": 1, "typing_speed_mean": 1, "recipient": "X",
            })
        self.assertNotAlmostEqual(dna.amount_mean, original_mean, places=2)


class TestAnomalyDetector(unittest.TestCase):
    def test_legit_event_scores_high_similarity(self):
        gen, history, dna, detector = _build_test_fixture(seed=20)
        ev = gen.scenario_legitimate()
        feat = ev.to_feature_dict(); feat["recipient"] = ev.recipient
        result = detector.score(feat)
        self.assertGreater(result.behavioural_similarity_pct, 50.0)

    def test_attack_event_scores_low_similarity(self):
        gen, history, dna, detector = _build_test_fixture(seed=21)
        ev = gen.scenario_account_takeover()
        feat = ev.to_feature_dict(); feat["recipient"] = ev.recipient
        result = detector.score(feat)
        self.assertLess(result.behavioural_similarity_pct, 30.0)

    def test_attack_scores_lower_similarity_than_legit(self):
        gen, history, dna, detector = _build_test_fixture(seed=22)
        leg = gen.scenario_legitimate()
        atk = gen.scenario_account_takeover()
        f_leg = leg.to_feature_dict(); f_leg["recipient"] = leg.recipient
        f_atk = atk.to_feature_dict(); f_atk["recipient"] = atk.recipient
        r_leg = detector.score(f_leg)
        r_atk = detector.score(f_atk)
        self.assertLess(r_atk.behavioural_similarity_pct, r_leg.behavioural_similarity_pct)
        self.assertGreater(r_atk.ml_anomaly_score, r_leg.ml_anomaly_score)


class TestRiskEngine(unittest.TestCase):
    def test_scenario_a_legitimate_is_low_risk(self):
        gen, history, dna, detector = _build_test_fixture(seed=30)
        ev = gen.scenario_legitimate()
        feat = ev.to_feature_dict(); feat["recipient"] = ev.recipient
        anomaly = detector.score(feat)
        assessment = assess_transaction(feat, dna, anomaly, recent_tx_count_24h=1)
        self.assertEqual(assessment.decision, "LOW")
        self.assertLess(assessment.risk_score, 30)

    def test_scenario_b_attack_is_high_risk(self):
        gen, history, dna, detector = _build_test_fixture(seed=31)
        ev = gen.scenario_account_takeover()
        feat = ev.to_feature_dict(); feat["recipient"] = ev.recipient
        anomaly = detector.score(feat)
        assessment = assess_transaction(feat, dna, anomaly, recent_tx_count_24h=3)
        self.assertEqual(assessment.decision, "HIGH")
        self.assertGreater(assessment.risk_score, 70)
        self.assertTrue(len(assessment.reasons) > 0)

    def test_components_sum_to_overall_score(self):
        gen, history, dna, detector = _build_test_fixture(seed=32)
        ev = gen.scenario_account_takeover()
        feat = ev.to_feature_dict(); feat["recipient"] = ev.recipient
        anomaly = detector.score(feat)
        assessment = assess_transaction(feat, dna, anomaly, recent_tx_count_24h=3)
        total = sum(c.contribution for c in assessment.components)
        self.assertAlmostEqual(total, assessment.risk_score, places=3)

    def test_weights_sum_to_one(self):
        from app.config import RISK_WEIGHTS
        self.assertAlmostEqual(sum(RISK_WEIGHTS.values()), 1.0, places=6)


class TestBlockchain(unittest.TestCase):
    def test_genesis_block_exists_and_is_valid(self):
        chain = Blockchain()
        self.assertEqual(len(chain.chain), 1)
        ok, err = chain.is_valid()
        self.assertTrue(ok, err)

    def test_hash_linkage_between_blocks(self):
        chain = Blockchain()
        b1 = chain.add_transaction({"sender": "A", "recipient": "B", "amount": 10})
        b2 = chain.add_transaction({"sender": "B", "recipient": "C", "amount": 20})
        self.assertEqual(b2.previous_hash, b1.block_hash)

    def test_chain_validates_when_untampered(self):
        chain = Blockchain()
        for i in range(5):
            chain.add_transaction({"sender": "A", "recipient": f"W{i}", "amount": i + 1})
        ok, err = chain.is_valid()
        self.assertTrue(ok, err)

    def test_chain_detects_tampering(self):
        chain = Blockchain()
        for i in range(3):
            chain.add_transaction({"sender": "A", "recipient": f"W{i}", "amount": i + 1})
        chain.chain[1].transaction["amount"] = 999999
        ok, err = chain.is_valid()
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_transaction_hash_is_deterministic(self):
        tx = {"sender": "A", "recipient": "B", "amount": 100}
        self.assertEqual(hash_transaction(tx), hash_transaction(dict(tx)))

    def test_proof_of_work_prefix_satisfied(self):
        chain = Blockchain()
        block = chain.add_transaction({"sender": "A", "recipient": "B", "amount": 1})
        self.assertTrue(block.block_hash.startswith(chain.difficulty_prefix))


class TestAuthChallenge(unittest.TestCase):
    def test_correct_code_verifies(self):
        store = DemoAuthChallengeStore()
        challenge = store.issue("tx1")
        ok, msg = store.verify("tx1", challenge.code)
        self.assertTrue(ok)

    def test_wrong_code_rejected(self):
        store = DemoAuthChallengeStore()
        store.issue("tx2")
        ok, msg = store.verify("tx2", "000000")
        self.assertFalse(ok)

    def test_max_attempts_enforced(self):
        store = DemoAuthChallengeStore()
        store.issue("tx3")
        for _ in range(3):
            store.verify("tx3", "wrong")
        ok, msg = store.verify("tx3", "wrong")
        self.assertFalse(ok)
        self.assertIn("Maximum", msg)

    def test_unknown_transaction_rejected(self):
        store = DemoAuthChallengeStore()
        ok, msg = store.verify("does-not-exist", "123456")
        self.assertFalse(ok)


class TestEngineIntegration(unittest.TestCase):
    def test_full_pipeline_approves_legitimate_transaction(self):
        from app import engine
        engine.reset_session("TESTUSR_INT1")
        session = engine.get_session("TESTUSR_INT1")
        outcome = engine.analyze_and_decide(
            "TESTUSR_INT1", amount=session.dna.amount_mean,
            recipient=session.dna.trusted_recipients[0], behaviour_profile="legitimate",
        )
        self.assertIn(outcome.status, ("APPROVED",))
        self.assertEqual(outcome.assessment.decision, "LOW")

    def test_full_pipeline_holds_attack_and_verification_releases_it(self):
        from app import engine
        engine.reset_session("TESTUSR_INT2")
        outcome = engine.run_scenario_attack("TESTUSR_INT2")
        self.assertEqual(outcome.status, "HELD_FOR_VERIFICATION")
        self.assertIsNotNone(outcome.otp_code_for_demo)

        result = engine.verify_and_release("TESTUSR_INT2", outcome.tx_id, outcome.otp_code_for_demo)
        self.assertTrue(result["verified"])
        self.assertIsNotNone(result["block_index"])


if __name__ == "__main__":
    unittest.main()
