"""
DBPTBS - API Endpoint Tests
------------------------------
Uses FastAPI's TestClient (needs `fastapi` + `httpx` installed - see
requirements.txt). Not run inside the code-generation sandbox that built
this project (fastapi wasn't available there), but written against the
documented FastAPI TestClient API and exercised against the same engine
covered by tests/test_dbptbs.py.

Run with:  python -m pytest tests/test_api.py -v
       or: python -m unittest tests.test_api -v
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app
from app import engine

client = TestClient(app)


class TestAuthEndpoint(unittest.TestCase):
    def test_login_returns_trust_score(self):
        resp = client.post("/auth/login", json={"user_id": "APITESTUSR1"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["user_id"], "APITESTUSR1")
        self.assertIn("trust_score", body)


class TestBehaviorEndpoint(unittest.TestCase):
    def test_get_profile_returns_dna_fields(self):
        client.post("/auth/login", json={"user_id": "APITESTUSR2"})
        resp = client.get("/behavior/profile/APITESTUSR2")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for key in ["amount_mean", "typical_hours", "trusted_recipients", "pattern_match"]:
            self.assertIn(key, body)


class TestTransactionEndpoints(unittest.TestCase):
    def test_analyze_legitimate_transaction_is_approved(self):
        engine.reset_session("APITESTUSR3")
        session = engine.get_session("APITESTUSR3")
        resp = client.post("/transaction/analyze", json={
            "user_id": "APITESTUSR3",
            "amount": session.dna.amount_mean,
            "recipient": session.dna.trusted_recipients[0],
            "behaviour_profile": "legitimate",
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "APPROVED")
        self.assertEqual(body["decision"], "LOW")

    def test_analyze_rejects_invalid_behaviour_profile(self):
        resp = client.post("/transaction/analyze", json={
            "user_id": "APITESTUSR4", "amount": 100, "recipient": "WALLET_X",
            "behaviour_profile": "not_a_real_profile",
        })
        self.assertEqual(resp.status_code, 400)

    def test_attack_simulation_then_verify_flow(self):
        engine.reset_session("APITESTUSR5")
        resp = client.post("/simulation/attack", params={"user_id": "APITESTUSR5"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "HELD_FOR_VERIFICATION")
        # The step-up code must NOT be in the same response that triggered
        # the challenge - it's fetched separately, simulating an
        # out-of-band channel (see /transaction/{tx_id}/demo-otp).
        self.assertNotIn("otp_code_for_demo", body)

        otp_resp = client.get(f"/transaction/{body['tx_id']}/demo-otp")
        self.assertEqual(otp_resp.status_code, 200)
        code = otp_resp.json()["code"]

        verify_resp = client.post("/transaction/verify", json={
            "user_id": "APITESTUSR5", "tx_id": body["tx_id"], "code": code,
        })
        self.assertEqual(verify_resp.status_code, 200)
        self.assertTrue(verify_resp.json()["verified"])

    def test_demo_otp_404_for_unknown_transaction(self):
        resp = client.get("/transaction/not-a-real-tx-id/demo-otp")
        self.assertEqual(resp.status_code, 404)


class TestBlockchainEndpoints(unittest.TestCase):
    def test_blockchain_is_valid_after_transactions(self):
        engine.reset_session("APITESTUSR6")
        client.post("/transaction/analyze", json={
            "user_id": "APITESTUSR6", "amount": 500, "recipient": "WALLET_ANY",
            "behaviour_profile": "legitimate",
        })
        resp = client.get("/blockchain/APITESTUSR6")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["valid"])


if __name__ == "__main__":
    unittest.main()
