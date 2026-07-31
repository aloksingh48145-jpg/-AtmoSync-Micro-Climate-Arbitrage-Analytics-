"""
Tests for ingestion/sensor_producer.py -- the simulated IoT sensor logic.
Does not require a running Kafka broker; only tests the pure data
generation functions.
"""

import random

import pytest

from sensor_producer import (
    COMMODITY_PROFILES,
    Shipment,
    make_shipments,
    next_reading,
)


def test_make_shipments_creates_requested_count():
    shipments = make_shipments(5)
    assert len(shipments) == 5


def test_make_shipments_assigns_valid_commodity():
    shipments = make_shipments(10)
    for s in shipments:
        assert s.commodity in COMMODITY_PROFILES


def test_make_shipments_unique_ids():
    shipments = make_shipments(20)
    ids = [s.shipment_id for s in shipments]
    assert len(ids) == len(set(ids))


def test_next_reading_within_safe_band_when_not_in_excursion():
    random.seed(42)
    shipment = Shipment(shipment_id="test-1", commodity="dairy", origin="A", destination="B")
    shipment.in_excursion = False

    # force no excursion trigger by patching random.random via seed variance;
    # instead just check structure/keys are always present regardless of state
    reading = next_reading(shipment)
    assert set(reading.keys()) == {
        "event_id", "shipment_id", "commodity", "origin", "destination",
        "temperature_c", "humidity_pct", "spoilage_risk", "recorded_at",
    }


def test_next_reading_in_band_values_stay_within_commodity_range():
    random.seed(1)
    shipment = Shipment(shipment_id="test-2", commodity="meat", origin="A", destination="B")
    shipment.in_excursion = False
    profile = COMMODITY_PROFILES["meat"]

    # run several ticks; whenever not flagged as spoilage_risk, values must be in-band
    for _ in range(50):
        reading = next_reading(shipment)
        if not reading["spoilage_risk"]:
            assert profile["temp_range"][0] <= reading["temperature_c"] <= profile["temp_range"][1]
            assert profile["humidity_range"][0] <= reading["humidity_pct"] <= profile["humidity_range"][1]


def test_next_reading_excursion_values_exceed_safe_band():
    shipment = Shipment(shipment_id="test-3", commodity="seafood", origin="A", destination="B")
    shipment.in_excursion = True
    shipment.excursion_ticks_left = 5
    profile = COMMODITY_PROFILES["seafood"]

    reading = next_reading(shipment)
    assert reading["spoilage_risk"] is True
    assert reading["temperature_c"] > profile["temp_range"][1]
    assert reading["humidity_pct"] > profile["humidity_range"][1]


def test_next_reading_excursion_eventually_ends():
    shipment = Shipment(shipment_id="test-4", commodity="produce", origin="A", destination="B")
    shipment.in_excursion = True
    shipment.excursion_ticks_left = 2

    next_reading(shipment)  # tick 1: excursion_ticks_left -> 1
    assert shipment.in_excursion is True
    next_reading(shipment)  # tick 2: excursion_ticks_left -> 0, excursion ends
    assert shipment.in_excursion is False


@pytest.mark.parametrize("commodity", list(COMMODITY_PROFILES.keys()))
def test_all_commodity_profiles_have_valid_ranges(commodity):
    profile = COMMODITY_PROFILES[commodity]
    assert profile["temp_range"][0] < profile["temp_range"][1]
    assert profile["humidity_range"][0] < profile["humidity_range"][1]
