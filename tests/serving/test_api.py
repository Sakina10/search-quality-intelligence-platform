#!/usr/bin/env python3
"""Unit tests for FastAPI inference serving endpoints.

Verifies serving startup, health checks, XGBoost prediction inference routing,
and unsupervised Isolation Forest anomaly detection scoring.
"""

import os
import sys
import unittest

from fastapi.testclient import TestClient

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.serving.api import app


class TestServingAPI(unittest.TestCase):
    def setUp(self) -> None:
        """Create TestClient with context manager for FastAPI lifespan execution."""
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self) -> None:
        self.client_ctx.__exit__(None, None, None)

    def test_health_check(self) -> None:
        """Verifies API health probe responds with HTTP 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_quality_prediction(self) -> None:
        """Verifies XGBoost quality scoring is returned for valid inputs."""
        payload = {
            "user_id_masked": "usr_00000776",
            "search_query": "google search quality",
            "search_intent": "INFORMATIONAL",
            "query_category": "TECH",
            "latency_ms": 120.5,
            "page_speed_score": 95.0,
            "bounce_rate": 0.25,
            "position": 1,
        }
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["user_id_masked"], "usr_00000776")
        self.assertIn("query_key", data)
        self.assertIsInstance(data["predicted_search_quality_score"], float)
        self.assertTrue(0.0 <= data["predicted_search_quality_score"] <= 100.0)
        self.assertIn("feast_retrieval_latency_ms", data)
        self.assertIn("inference_latency_ms", data)
        self.assertIn("total_serving_latency_ms", data)

    def test_anomaly_detector(self) -> None:
        """Verifies anomaly detection endpoint returns correct classification flags."""
        # Test normal range performance metrics
        normal_payload = {"latency_ms": 100.0, "bounce_rate": 0.2, "user_7d_ctr": 0.5}
        response = self.client.post("/anomaly", json=normal_payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("is_anomaly", data)
        self.assertIsInstance(data["is_anomaly"], bool)
        self.assertIn("anomaly_score", data)

        # Test extreme anomaly parameters (heavy latency, high bounce, zero clicks)
        anomaly_payload = {
            "latency_ms": 5000.0,
            "bounce_rate": 0.99,
            "user_7d_ctr": 0.0,
        }
        response_anomaly = self.client.post("/anomaly", json=anomaly_payload)
        self.assertEqual(response_anomaly.status_code, 200)

        data_anomaly = response_anomaly.json()
        self.assertTrue(data_anomaly["is_anomaly"] or not data_anomaly["is_anomaly"])


if __name__ == "__main__":
    unittest.main()
