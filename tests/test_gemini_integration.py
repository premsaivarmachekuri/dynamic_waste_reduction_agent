"""
test_gemini_integration.py

Tests for the Gemini AI integration module.
Covers:
  1. Simulation pipeline (all tools run without error)
  2. Prompt construction
  3. Full run_gemini_analysis() with a mocked Gemini response
  4. Fallback behaviour when the API key is invalid
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on the path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-placeholder")

from dotenv import load_dotenv
load_dotenv()

import pytest
from gemini_ai import (
    _run_simulations,
    _build_analysis_prompt,
    run_gemini_analysis,
)
from tools.inventory_tools import get_inventory_status, get_transfer_options
from tools.weather_tools import get_weather_forecast
from tools.pricing_tools import simulate_discount_action, simulate_loyalty_coupon


# ── Fixtures ──────────────────────────────────────────────────────────────────

STORE_ID = "ST001"

@pytest.fixture
def inv():
    return get_inventory_status(STORE_ID)

@pytest.fixture
def weather():
    return get_weather_forecast(STORE_ID)

@pytest.fixture
def critical_high(inv):
    return [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH")]

@pytest.fixture
def simulations(critical_high, weather):
    return _run_simulations(STORE_ID, critical_high, weather)


# ── Tool layer tests ──────────────────────────────────────────────────────────

class TestToolLayer:
    def test_inventory_returns_data(self, inv):
        assert "inventory" in inv
        assert inv["total_skus_checked"] > 0

    def test_weather_returns_demand_impact(self, weather):
        assert "demand_impact" in weather
        assert "overall" in weather["demand_impact"]
        assert "heatwave" in weather["demand_impact"]

    def test_critical_high_items_present(self, critical_high):
        assert len(critical_high) > 0, "Need at least one CRITICAL/HIGH item for meaningful tests"

    def test_discount_simulation_structure(self, critical_high):
        item = critical_high[0]
        result = simulate_discount_action(item["sku_id"], STORE_ID, 20, item["days_to_expiry"])
        assert "viable" in result
        assert "gross_margin_pct" in result
        assert "waste_reduction_gbp" in result
        assert "discounted_price_gbp" in result

    def test_coupon_simulation_structure(self, critical_high):
        item = critical_high[0]
        result = simulate_loyalty_coupon(item["sku_id"], STORE_ID, 15, 500)
        assert "expected_redemptions" in result
        assert "net_benefit_gbp" in result

    def test_transfer_options_structure(self, critical_high):
        item = critical_high[0]
        result = get_transfer_options(item["sku_id"], STORE_ID)
        assert "transfer_options" in result


# ── Simulation pipeline tests ─────────────────────────────────────────────────

class TestSimulationPipeline:
    def test_simulations_produced_for_each_item(self, critical_high, simulations):
        expected_count = min(len(critical_high), 5)
        assert len(simulations) == expected_count

    def test_simulation_keys(self, simulations):
        required_keys = {
            "sku_id", "product", "risk_level", "stock_qty",
            "days_to_expiry", "potential_waste_value_gbp",
            "discount_10pct", "discount_20pct", "discount_30pct",
            "loyalty_coupon_15pct",
        }
        for sim in simulations:
            assert required_keys.issubset(sim.keys()), f"Missing keys in {sim['sku_id']}"

    def test_discount_levels_present(self, simulations):
        for sim in simulations:
            for level in ("discount_10pct", "discount_20pct", "discount_30pct"):
                d = sim[level]
                assert "viable" in d
                assert "margin_pct" in d
                assert "waste_saved_gbp" in d


# ── Prompt builder test ───────────────────────────────────────────────────────

class TestPromptBuilder:
    def test_prompt_contains_store_id(self, inv, weather, simulations):
        prompt = _build_analysis_prompt(STORE_ID, inv, weather, simulations)
        assert STORE_ID in prompt

    def test_prompt_contains_json_structure_instruction(self, inv, weather, simulations):
        prompt = _build_analysis_prompt(STORE_ID, inv, weather, simulations)
        assert '"decisions"' in prompt
        assert '"total_saving_gbp"' in prompt
        assert '"executive_summary"' in prompt

    def test_prompt_contains_simulation_data(self, inv, weather, simulations):
        prompt = _build_analysis_prompt(STORE_ID, inv, weather, simulations)
        # At least one SKU ID should appear in the prompt
        assert simulations[0]["sku_id"] in prompt


# ── Full integration test (mocked Gemini) ─────────────────────────────────────

MOCK_GEMINI_RESPONSE = {
    "decisions": [
        {
            "sku_id": "SKU_PLACEHOLDER",
            "product": "Test Product",
            "risk_level": "CRITICAL",
            "action": "DISCOUNT",
            "detail": "Apply 30% markdown immediately. Price: £1.05",
            "units": 50,
            "saving_gbp": 22.50,
            "kg_saved": 25.0,
            "reasoning": "CRITICAL expiry risk. 30% discount maximises sell-through at 42% margin. Combined with loyalty coupon, recovers £22.50 of potential waste."
        }
    ],
    "total_saving_gbp": 22.50,
    "total_kg_saved": 25.0,
    "co2_avoided_kg": 82.5,
    "meals_equivalent": 83,
    "executive_summary": "Gemini identified 1 CRITICAL item requiring immediate intervention. A 30% markdown on Test Product is projected to recover £22.50 and prevent 25 kg of food waste, equivalent to 83 meals."
}


class TestGeminiIntegration:
    """Full run_gemini_analysis() with Gemini responses mocked out."""

    def _make_mock_response(self, inv):
        """Build a mock response that uses a real SKU from the store's inventory."""
        critical_high = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH")]
        if not critical_high:
            return None, None

        real_item = critical_high[0]
        mock_result = {
            "decisions": [
                {
                    "sku_id": real_item["sku_id"],
                    "product": real_item["name"],
                    "risk_level": real_item["risk_level"],
                    "action": "DISCOUNT",
                    "detail": f"Apply 30% markdown. Price: £{real_item['unit_price'] * 0.7:.2f}",
                    "units": real_item["stock_qty"],
                    "saving_gbp": round(real_item["potential_waste_value_gbp"] * 0.8, 2),
                    "kg_saved": round(real_item["stock_qty"] * real_item.get("weight_kg", 0.5), 2),
                    "reasoning": f"{real_item['risk_level']} risk. 30% discount boosts sell-through while maintaining margin above 25%."
                }
            ],
            "total_saving_gbp": round(real_item["potential_waste_value_gbp"] * 0.8, 2),
            "total_kg_saved": round(real_item["stock_qty"] * real_item.get("weight_kg", 0.5), 2),
            "co2_avoided_kg": round(real_item["stock_qty"] * real_item.get("weight_kg", 0.5) * 3.3, 2),
            "meals_equivalent": int(real_item["stock_qty"] * real_item.get("weight_kg", 0.5) / 0.3),
            "executive_summary": f"AI identified {real_item['name']} as {real_item['risk_level']} risk. Immediate discount action recommended."
        }
        return real_item, mock_result

    def test_run_gemini_analysis_mocked(self, inv):
        real_item, mock_result = self._make_mock_response(inv)
        if real_item is None:
            pytest.skip("No CRITICAL/HIGH items in ST001")

        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_result)

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("gemini_ai._get_client", return_value=mock_client):
            result = run_gemini_analysis(STORE_ID)

        # Core shape assertions
        assert "decisions" in result
        assert "total_saving_gbp" in result
        assert "total_kg_saved" in result
        assert "co2_avoided_kg" in result
        assert "meals_equivalent" in result
        assert result["ai_powered"] is True

    def test_decisions_logged_to_store(self, inv):
        """Verify that decisions get logged (decision_id added) during analysis."""
        real_item, mock_result = self._make_mock_response(inv)
        if real_item is None:
            pytest.skip("No CRITICAL/HIGH items in ST001")

        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_result)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("gemini_ai._get_client", return_value=mock_client):
            result = run_gemini_analysis(STORE_ID)

        for decision in result["decisions"]:
            assert "decision_id" in decision, "Each decision must be logged with a decision_id"

    def test_gemini_api_error_propagates(self):
        """Verify that API errors propagate (so app.py can catch and fall back)."""
        from google.genai.errors import ClientError

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API quota exceeded")

        with patch("gemini_ai._get_client", return_value=mock_client):
            with pytest.raises(Exception, match="API quota exceeded"):
                run_gemini_analysis(STORE_ID)

    def test_gemini_handles_markdown_fenced_json(self, inv):
        """Verify stripping of ```json ... ``` fences that Gemini sometimes adds."""
        real_item, mock_result = self._make_mock_response(inv)
        if real_item is None:
            pytest.skip("No CRITICAL/HIGH items in ST001")

        # Wrap the JSON in markdown fences as Gemini sometimes does
        fenced_text = f"```json\n{json.dumps(mock_result)}\n```"

        mock_response = MagicMock()
        mock_response.text = fenced_text
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("gemini_ai._get_client", return_value=mock_client):
            result = run_gemini_analysis(STORE_ID)

        assert "decisions" in result


# ── Flask app fallback test ───────────────────────────────────────────────────

class TestFlaskFallback:
    """Verify the Flask /api/run_analysis endpoint falls back correctly."""

    def test_app_falls_back_when_gemini_raises(self):
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        client = flask_app.app.test_client()

        with patch("app.run_gemini_analysis", side_effect=Exception("API disabled")):
            with patch("app._GEMINI_AVAILABLE", True):
                with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-key"}):
                    resp = client.post(
                        "/api/run_analysis",
                        json={"store_id": "ST001"},
                        content_type="application/json",
                    )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ai_mode"] == "rule-based-mock"
        assert "ai_warning" in data

    def test_app_returns_200_without_api_key(self):
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        client = flask_app.app.test_client()

        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            with patch("app._GEMINI_AVAILABLE", True):
                resp = client.post(
                    "/api/run_analysis",
                    json={"store_id": "ST001"},
                    content_type="application/json",
                )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "decisions" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
