"""
Tests for dashboard/data_source.py -- especially the live/sample fallback
behavior, since that's the part most worth guaranteeing with tests (a
silent failure here would mean the dashboard looks broken with no clear
reason why).
"""

import os

import data_source


def test_get_data_source_status_is_sample_without_credentials(monkeypatch):
    for var in [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
    ]:
        monkeypatch.delenv(var, raising=False)

    assert data_source.get_data_source_status() == "sample"


def test_sample_shipment_summary_has_expected_columns():
    df = data_source._generate_sample_shipment_summary(n_shipments=10)
    expected_cols = {
        "SHIPMENT_ID", "COMMODITY", "ORIGIN", "DESTINATION", "TOTAL_READINGS",
        "OUT_OF_BAND_READINGS", "PEAK_SEVERITY_SCORE", "AVG_SEVERITY_SCORE",
        "LAST_READING_AT", "HAS_HIGH_RISK_WINDOW", "PCT_READINGS_OUT_OF_BAND",
    }
    assert expected_cols.issubset(set(df.columns))
    assert len(df) == 10


def test_sample_shipment_summary_commodities_are_valid():
    df = data_source._generate_sample_shipment_summary(n_shipments=30)
    assert set(df["COMMODITY"].unique()).issubset(set(data_source.COMMODITIES))


def test_sample_readings_has_expected_columns():
    df = data_source._generate_sample_readings(hours=1, points_per_hour=6)
    expected_cols = {"RECORDED_AT", "COMMODITY", "TEMPERATURE_C", "HUMIDITY_PCT", "RISK_SEVERITY_SCORE"}
    assert expected_cols.issubset(set(df.columns))


def test_sample_readings_are_sorted_by_time():
    df = data_source._generate_sample_readings(hours=2, points_per_hour=4)
    assert list(df["RECORDED_AT"]) == sorted(df["RECORDED_AT"])


def test_get_shipment_summary_falls_back_to_sample_without_credentials(monkeypatch):
    for var in [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
    ]:
        monkeypatch.delenv(var, raising=False)

    df, source = data_source.get_shipment_summary()
    assert source == "sample"
    assert len(df) > 0
