# AtmoSync Live Dashboard (Streamlit)

A lightweight, always-demoable dashboard that complements the Superset
setup. Great for quick screenshots, live demos, or presenting to
non-technical reviewers (e.g. an internship evaluation).

## Why this exists alongside Superset

Superset is the production-grade BI layer (`superset/SETUP.md`). This
Streamlit app is a fast, single-command dashboard that:
- Runs without Docker
- Falls back to realistic **sample data** automatically if Snowflake
  isn't reachable — so it never shows a blank screen, even mid-setup
  or during a live demo with shaky wifi
- Shows a clear "Live data" / "Sample data" badge in the sidebar so you
  always know which mode you're in

## Setup

```
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Opens automatically at `http://localhost:8501`.

## Pages

- **Dashboard** — key metrics, critical alert banner, temperature/humidity trend charts
- **Analytics** — average severity by commodity, full shipment risk table
- **Live Monitoring** — high-risk shipments needing attention, recent readings
- **Settings** — shows current data source and required env vars

## Data source behavior

Reads `infra/.env` for Snowflake credentials. If they're missing or the
connection fails for any reason, it silently generates sample data with
the same shape as the real `SHIPMENT_RISK_SUMMARY` / `FCT_SPOILAGE_RISK`
tables, so the UI always works.
