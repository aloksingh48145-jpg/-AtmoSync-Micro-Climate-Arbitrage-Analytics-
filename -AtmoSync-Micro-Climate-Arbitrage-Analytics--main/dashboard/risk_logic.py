"""
Risk-scoring and arbitrage-recommendation logic, shared between app.py and
the test suite. Kept dependency-free (no streamlit/pandas import required)
so it's trivial to unit test.
"""

HIGH_RISK_THRESHOLD = 10.0  # matches dbt's fct_spoilage_risk arbitrage_window logic


def compute_risk_level(peak_severity_score: float, has_high_risk_window: bool) -> str:
    """Classify a shipment's overall risk level.

    Mirrors the dbt arbitrage_window tiers (none/moderate/high), renamed
    to Low/Medium/High for display consistency with the Arbitrage View.
    """
    if has_high_risk_window:
        return "High"
    elif peak_severity_score > 0:
        return "Medium"
    return "Low"


def compute_temperature_status(out_of_band_readings: int) -> str:
    """Whether a shipment has ever left its commodity's safe band."""
    return "Out of Band" if out_of_band_readings > 0 else "In Band"


def arbitrage_recommendation(peak_severity_score: float, pct_readings_out_of_band: float) -> dict:
    """
    Returns a recommendation with a human-readable reason, not just a
    label -- this is the "explainability" layer: a reviewer (or an
    operations person in a real deployment) should be able to see *why*
    a shipment is flagged, not just that it is.
    """
    risk_level = compute_risk_level(peak_severity_score, peak_severity_score >= HIGH_RISK_THRESHOLD)

    if risk_level == "High":
        action = "Reroute Shipment"
        reason = (
            f"Peak severity score of {peak_severity_score:.1f} exceeds the "
            f"high-risk threshold ({HIGH_RISK_THRESHOLD:.0f}), and "
            f"{pct_readings_out_of_band:.1f}% of readings were outside the "
            f"safe band. Spoilage loss is likely if left in transit; "
            f"rerouting to the nearest cold-chain hub or discounting for "
            f"immediate sale is recommended."
        )
    elif risk_level == "Medium":
        action = "Monitor Closely"
        reason = (
            f"Some readings ({pct_readings_out_of_band:.1f}%) fell outside "
            f"the safe band, but peak severity ({peak_severity_score:.1f}) "
            f"stayed under the high-risk threshold. No action needed yet, "
            f"but flag for closer monitoring."
        )
    else:
        action = "Continue Shipment"
        reason = "All readings within the safe band for this commodity. No action needed."

    return {"risk_level": risk_level, "action": action, "reason": reason}
