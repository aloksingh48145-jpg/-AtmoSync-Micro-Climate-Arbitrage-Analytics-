# AtmoSync Test Suite

Unit tests for the pure-logic parts of the pipeline (no live Kafka or
Snowflake connection required to run these).

## Running

From the project root:
```
pip install -r tests/requirements.txt
pytest tests/ -v
```

## What's covered

- **`test_producer.py`** — the Kafka sensor simulation logic (shipment
  generation, in-band vs. excursion readings, excursion lifecycle)
- **`test_risk_logic.py`** — risk-level classification and arbitrage
  recommendation reasoning (shared with the Streamlit dashboard)
- **`test_data_source.py`** — the dashboard's live/sample data fallback
  behavior

## A real bug this suite caught

While writing `test_next_reading_in_band_values_stay_within_commodity_range`,
the suite caught a genuine bug in `sensor_producer.py`: on the *last* tick
of a spoilage excursion, the temperature/humidity values were still
out-of-band, but the `spoilage_risk` flag had already flipped back to
`False` one tick early (it was read *after* the excursion counter ticked
down to zero, instead of before). This meant every excursion under-reported
its final abnormal reading as "safe." Fixed by capturing the excursion
state before mutating it. Good example of why testing the data generator
itself — not just the downstream logic — is worth doing.
