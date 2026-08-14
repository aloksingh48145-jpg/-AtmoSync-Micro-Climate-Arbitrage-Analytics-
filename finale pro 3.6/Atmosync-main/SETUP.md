# Superset Setup — AtmoSync Dashboard

Superset connections and charts are built through its web UI, not config
files, so this doc is a click-by-click guide rather than code to run.

## 1. Rebuild and start Superset (picks up the Snowflake driver)

```
cd infra
docker compose build superset
docker compose up -d
```

## 2. First-time admin account

The first time the container starts, create an admin user:

```
docker exec -it atmosync-superset superset fab create-admin \
  --username admin --firstname Admin --lastname User \
  --email admin@example.com --password admin

docker exec -it atmosync-superset superset db upgrade
docker exec -it atmosync-superset superset init
```

Then open **http://localhost:8088** and log in with `admin` / `admin`.

## 3. Connect Superset to Snowflake

1. Settings (top right) → **Database Connections** → **+ Database**
2. Choose **Snowflake**
3. Fill in the SQLAlchemy URI:
   ```
   snowflake://{user}:{password}@{account}/IOT_DB/MARTS?warehouse=COMPUTE_WH&role=ACCOUNTADMIN
   ```
   Replace `{user}`, `{password}`, `{account}` with your real values from `infra/.env`.
4. Test connection → Connect

## 4. Add datasets

Settings → **Datasets** → **+ Dataset**, add both:
- `IOT_DB.MARTS.SHIPMENT_RISK_SUMMARY` (primary dashboard table)
- `IOT_DB.MARTS.FCT_SPOILAGE_RISK` (for time-series / drill-down charts)

## 5. Charts to build

| Chart | Dataset | Type | Config |
|---|---|---|---|
| Shipments at risk (table) | shipment_risk_summary | Table | Sort by `peak_severity_score` desc; filter `has_high_risk_window = TRUE` |
| Risk by commodity | shipment_risk_summary | Bar chart | X: `commodity`, Y: `avg(peak_severity_score)` |
| % readings out of band | shipment_risk_summary | Bar chart | X: `shipment_id`, Y: `pct_readings_out_of_band`, sorted desc |
| Severity over time | fct_spoilage_risk | Line chart | X: `recorded_at`, Y: `avg(risk_severity_score)`, group by `commodity` |
| High-risk shipment count | shipment_risk_summary | Big Number | `count` where `has_high_risk_window = TRUE` |

## 6. Assemble the dashboard

Dashboards → **+ Dashboard** → name it "AtmoSync — Spoilage Risk & Arbitrage" →
drag in the 5 charts above → Save.

## 7. Verify

The "Shipments at risk" table and "High-risk shipment count" should update
each time you re-run `dbt run` after the producer/consumer add new data —
that's confirmation the whole pipeline (Kafka → Snowflake → dbt → Superset)
is working end to end.
