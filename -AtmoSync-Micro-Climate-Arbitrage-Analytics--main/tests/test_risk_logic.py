"""
Tests for dashboard/risk_logic.py -- the risk classification and
arbitrage recommendation engine.
"""

from risk_logic import (
    compute_risk_level,
    compute_temperature_status,
    arbitrage_recommendation,
    HIGH_RISK_THRESHOLD,
)


def test_risk_level_low_when_no_severity():
    assert compute_risk_level(peak_severity_score=0.0, has_high_risk_window=False) == "Low"


def test_risk_level_medium_when_some_severity_but_not_high():
    assert compute_risk_level(peak_severity_score=3.5, has_high_risk_window=False) == "Medium"


def test_risk_level_high_when_flagged():
    assert compute_risk_level(peak_severity_score=15.0, has_high_risk_window=True) == "High"


def test_temperature_status_in_band():
    assert compute_temperature_status(out_of_band_readings=0) == "In Band"


def test_temperature_status_out_of_band():
    assert compute_temperature_status(out_of_band_readings=5) == "Out of Band"


def test_recommendation_high_risk_recommends_reroute():
    rec = arbitrage_recommendation(
        peak_severity_score=HIGH_RISK_THRESHOLD + 5,
        pct_readings_out_of_band=40.0,
    )
    assert rec["risk_level"] == "High"
    assert rec["action"] == "Reroute Shipment"
    assert "reroute" in rec["reason"].lower() or "cold-chain" in rec["reason"].lower()


def test_recommendation_medium_risk_recommends_monitoring():
    rec = arbitrage_recommendation(peak_severity_score=2.0, pct_readings_out_of_band=10.0)
    assert rec["risk_level"] == "Medium"
    assert rec["action"] == "Monitor Closely"


def test_recommendation_low_risk_recommends_continue():
    rec = arbitrage_recommendation(peak_severity_score=0.0, pct_readings_out_of_band=0.0)
    assert rec["risk_level"] == "Low"
    assert rec["action"] == "Continue Shipment"


def test_recommendation_boundary_at_threshold_is_high():
    # exactly at the threshold should count as High, not Medium
    rec = arbitrage_recommendation(peak_severity_score=HIGH_RISK_THRESHOLD, pct_readings_out_of_band=5.0)
    assert rec["risk_level"] == "High"
