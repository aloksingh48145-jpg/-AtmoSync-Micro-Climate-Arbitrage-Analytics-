"""
Data source layer for the AtmoSync Streamlit dashboard.

Tries to query live data from Snowflake (IOT_DB.MARTS.*). If credentials
are missing or the connection fails for any reason, falls back to
generated sample data with the same shape -- so the dashboard always
renders, even offline or mid-setup.
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "infra", ".env"))

COMMODITIES = ["dairy", "produce", "meat", "seafood", "flowers"]
COMMODITY_BANDS = {
    "dairy":   {"temp": (2.0, 4.0),  "hum": (80, 90)},
    "produce": {"temp": (0.0, 4.0),  "hum": (85, 95)},
    "meat":    {"temp": (-2.0, 2.0), "hum": (75, 85)},
    "seafood": {"temp": (-1.0, 1.0), "hum": (85, 95)},
    "flowers": {"temp": (1.0, 4.0),  "hum": (85, 95)},
}


def _try_snowflake_connection():
    """Return a live snowflake connection, or None if unavailable for any reason."""
    required = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
    ]
    if any(not os.getenv(v) for v in required):
        return None

    try:
        import snowflake.connector
        return snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            role=os.getenv("SNOWFLAKE_ROLE"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema="MARTS",
            login_timeout=8,
        )
    except Exception:
        return None


def get_data_source_status() -> str:
    """Returns 'live' or 'sample' without raising."""
    conn = _try_snowflake_connection()
    if conn is not None:
        conn.close()
        return "live"
    return "sample"


def _generate_sample_shipment_summary(n_shipments: int = 40) -> pd.DataFrame:
    rows = []
    for i in range(n_shipments):
        commodity = random.choice(COMMODITIES)
        total_readings = random.randint(20, 200)
        out_of_band = random.randint(0, total_readings // 3)
        peak_severity = round(random.uniform(0, 25), 2) if out_of_band else 0.0
        rows.append({
            "SHIPMENT_ID": f"SHIP-{1000 + i}",
            "COMMODITY": commodity,
            "ORIGIN": random.choice(["Mumbai", "Pune", "Delhi", "Chennai", "Kolkata", "Bangalore"]),
            "DESTINATION": random.choice(["Hyderabad", "Jaipur", "Lucknow", "Surat", "Nagpur"]),
            "TOTAL_READINGS": total_readings,
            "OUT_OF_BAND_READINGS": out_of_band,
            "PEAK_SEVERITY_SCORE": peak_severity,
            "AVG_SEVERITY_SCORE": round(peak_severity * random.uniform(0.3, 0.7), 2),
            "LAST_READING_AT": datetime.now() - timedelta(minutes=random.randint(0, 120)),
            "HAS_HIGH_RISK_WINDOW": peak_severity >= 10,
            "PCT_READINGS_OUT_OF_BAND": round(100 * out_of_band / total_readings, 1) if total_readings else 0,
        })
    return pd.DataFrame(rows)


def _generate_sample_readings(hours: int = 6, points_per_hour: int = 12) -> pd.DataFrame:
    now = datetime.now()
    rows = []
    for commodity in COMMODITIES:
        band = COMMODITY_BANDS[commodity]
        for i in range(hours * points_per_hour):
            ts = now - timedelta(minutes=5 * i)
            excursion = random.random() < 0.05
            temp = (
                round(band["temp"][1] + random.uniform(2, 6), 2)
                if excursion
                else round(random.uniform(*band["temp"]), 2)
            )
            hum = (
                round(band["hum"][1] + random.uniform(2, 8), 2)
                if excursion
                else round(random.uniform(*band["hum"]), 2)
            )
            rows.append({
                "RECORDED_AT": ts,
                "COMMODITY": commodity,
                "TEMPERATURE_C": temp,
                "HUMIDITY_PCT": hum,
                "RISK_SEVERITY_SCORE": round(max(0, temp - band["temp"][1]) * 1.5, 2) if excursion else 0.0,
            })
    df = pd.DataFrame(rows)
    return df.sort_values("RECORDED_AT")


def get_shipment_summary() -> tuple[pd.DataFrame, str]:
    """Returns (dataframe, source) where source is 'live' or 'sample'."""
    conn = _try_snowflake_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM IOT_DB.MARTS.SHIPMENT_RISK_SUMMARY")
            df = cursor.fetch_pandas_all()
            conn.close()
            if not df.empty:
                return df, "live"
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return _generate_sample_shipment_summary(), "sample"


def get_spoilage_readings(hours: int = 6) -> tuple[pd.DataFrame, str]:
    """Returns (dataframe, source) where source is 'live' or 'sample'."""
    conn = _try_snowflake_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT recorded_at, commodity, temperature_c, humidity_pct, risk_severity_score
                FROM IOT_DB.MARTS.FCT_SPOILAGE_RISK
                WHERE recorded_at >= dateadd(hour, -{hours}, current_timestamp())
                ORDER BY recorded_at
            """)
            df = cursor.fetch_pandas_all()
            conn.close()
            if not df.empty:
                return df, "live"
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return _generate_sample_readings(hours=hours), "sample"
