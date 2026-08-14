"""
AtmoSync Live Dashboard (Streamlit)

A lightweight, always-demoable dashboard that complements the Superset
setup. Reads live data from Snowflake marts when available; otherwise
falls back to realistic sample data so it never shows a blank screen.

Run with:
    streamlit run app.py
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from data_source import get_shipment_summary, get_spoilage_readings

st.set_page_config(page_title="AtmoSync Live Dashboard", page_icon="🌡️", layout="wide")

# ---------- Sidebar navigation ----------
st.sidebar.title("🌡️ AtmoSync")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Analytics", "Arbitrage View", "Live Monitoring", "Settings"],
    label_visibility="collapsed",
)

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")


@st.cache_data(ttl=30)
def load_shipment_summary():
    return get_shipment_summary()


@st.cache_data(ttl=30)
def load_readings(hours: int):
    return get_spoilage_readings(hours=hours)


shipments_df, shipment_source = load_shipment_summary()
readings_df, readings_source = load_readings(hours=6)
data_source = "live" if shipment_source == "live" else "sample"

# normalize column names to lowercase for consistent access regardless of source
shipments_df.columns = [c.lower() for c in shipments_df.columns]
readings_df.columns = [c.lower() for c in readings_df.columns]


def source_badge():
    if data_source == "live":
        st.sidebar.success("● Live data (Snowflake)")
    else:
        st.sidebar.warning("● Sample data (offline demo mode)")


source_badge()

total_shipments = shipments_df["shipment_id"].nunique()
high_risk_count = int(shipments_df["has_high_risk_window"].sum())
avg_health = round(100 - shipments_df["avg_severity_score"].mean(), 2) if len(shipments_df) else 0
total_sensors = int(shipments_df["total_readings"].sum()) if len(shipments_df) else 0


def _risk_level(row):
    if row["has_high_risk_window"]:
        return "High"
    elif row["peak_severity_score"] > 0:
        return "Medium"
    return "Low"


if len(shipments_df):
    shipments_df["risk_level"] = shipments_df.apply(_risk_level, axis=1)
    shipments_df["temperature_status"] = shipments_df["out_of_band_readings"].apply(
        lambda x: "Out of Band" if x > 0 else "In Band"
    )

# ---------- Dashboard page ----------
if page == "Dashboard":
    st.title("🌡️ AtmoSync Live Dashboard")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📡 Sensor Readings", f"{total_sensors:,}")
    col2.metric("📦 Shipments", f"{total_shipments:,}")
    col3.metric("🚨 High-Risk Shipments", f"{high_risk_count:,}")
    col4.metric("❤️ Avg Health Score", f"{avg_health}")

    if high_risk_count > 0:
        st.error(f"⚠️ {high_risk_count} shipment(s) are in CRITICAL condition — spoilage risk detected.")
    else:
        st.success("✅ No shipments currently in critical condition.")

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("🌡️ Temperature Trend")
        if len(readings_df):
            fig = px.line(
                readings_df, x="recorded_at", y="temperature_c", color="commodity",
                labels={"recorded_at": "Time", "temperature_c": "Temp (°C)"},
            )
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No readings available yet.")

    with chart_col2:
        st.subheader("💧 Humidity Trend")
        if len(readings_df):
            fig = px.line(
                readings_df, x="recorded_at", y="humidity_pct", color="commodity",
                labels={"recorded_at": "Time", "humidity_pct": "Humidity (%)"},
            )
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No readings available yet.")

# ---------- Analytics page ----------
elif page == "Analytics":
    st.title("📊 Analytics")

    st.subheader("Average Severity Score by Commodity")
    if len(shipments_df):
        by_commodity = (
            shipments_df.groupby("commodity")["avg_severity_score"]
            .mean()
            .reset_index()
            .sort_values("avg_severity_score", ascending=False)
        )
        fig = px.bar(by_commodity, x="commodity", y="avg_severity_score", color="commodity")
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Shipments Ranked by Risk")
    display_cols = [
        "shipment_id", "commodity", "origin", "destination",
        "peak_severity_score", "pct_readings_out_of_band", "has_high_risk_window",
    ]
    st.dataframe(
        shipments_df[display_cols].sort_values("peak_severity_score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

# ---------- Arbitrage View page ----------
elif page == "Arbitrage View":
    st.title("⚖️ AtmoSync — Spoilage & Arbitrage Analytics")

    # --- Filters ---
    with st.expander("🔎 Filters", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        shipment_options = ["All"] + sorted(shipments_df["shipment_id"].unique().tolist())
        selected_shipment = f_col1.selectbox("Container / Shipment ID", shipment_options)
        selected_risk = f_col2.multiselect(
            "Risk Level", ["Low", "Medium", "High"], default=["Low", "Medium", "High"]
        )
        selected_temp_status = f_col3.multiselect(
            "Temperature Status", ["In Band", "Out of Band"], default=["In Band", "Out of Band"]
        )

    filtered = shipments_df[
        shipments_df["risk_level"].isin(selected_risk)
        & shipments_df["temperature_status"].isin(selected_temp_status)
    ]
    if selected_shipment != "All":
        filtered = filtered[filtered["shipment_id"] == selected_shipment]

    # --- KPI cards ---
    avg_spoilage = round(filtered["peak_severity_score"].mean(), 2) if len(filtered) else 0.0
    high_risk_containers = int((filtered["risk_level"] == "High").sum())
    reroute_recommended = high_risk_containers
    spoilage_alerts = int(filtered["out_of_band_readings"].sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Average Spoilage Score", avg_spoilage)
    k2.metric("High Risk Containers", high_risk_containers)
    k3.metric("Reroute Recommended", reroute_recommended)
    k4.metric("Spoilage Risk Alerts", spoilage_alerts)

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Risk Level Distribution")
        if len(filtered):
            risk_counts = filtered["risk_level"].value_counts().reset_index()
            risk_counts.columns = ["risk_level", "count"]
            fig = px.pie(
                risk_counts, names="risk_level", values="count", hole=0.5,
                color="risk_level",
                color_discrete_map={"Low": "#2ecc71", "Medium": "#f39c12", "High": "#e74c3c"},
            )
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No shipments match the current filters.")

    with chart_col2:
        st.subheader("Arbitrage Opportunity")
        if len(filtered):
            continue_count = int((filtered["risk_level"] != "High").sum())
            reroute_count = int((filtered["risk_level"] == "High").sum())
            arb_df = pd.DataFrame({
                "action": ["Continue Shipment", "Reroute Shipment"],
                "count": [continue_count, reroute_count],
            })
            fig = px.bar(
                arb_df, x="action", y="count", color="action",
                color_discrete_map={"Continue Shipment": "#3498db", "Reroute Shipment": "#e74c3c"},
            )
            fig.update_layout(height=320, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No shipments match the current filters.")

    st.subheader("Average Spoilage Score by Container")
    if len(filtered):
        by_container = filtered[["shipment_id", "peak_severity_score"]].sort_values(
            "peak_severity_score", ascending=False
        ).head(15)
        fig = px.bar(by_container, x="shipment_id", y="peak_severity_score")
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ---------- Live Monitoring page ----------
elif page == "Live Monitoring":
    st.title("📡 Live Monitoring")
    st.caption("Click 'Refresh data' in the sidebar to pull the latest readings.")

    critical = shipments_df[shipments_df["has_high_risk_window"]]
    if len(critical):
        st.subheader("🚨 Shipments Needing Attention")
        st.dataframe(
            critical[["shipment_id", "commodity", "origin", "destination", "peak_severity_score"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No shipments currently flagged as high-risk.")

    st.subheader("Recent Readings")
    st.dataframe(readings_df.tail(50), use_container_width=True, hide_index=True)

# ---------- Settings page ----------
elif page == "Settings":
    st.title("⚙️ Settings")
    st.write(f"**Current data source:** `{data_source}`")
    st.write(
        "The dashboard automatically uses live Snowflake data from "
        "`IOT_DB.MARTS.SHIPMENT_RISK_SUMMARY` and `IOT_DB.MARTS.FCT_SPOILAGE_RISK` "
        "when valid credentials are found in `infra/.env`. Otherwise it falls back "
        "to generated sample data so the dashboard is always demoable."
    )
    st.subheader("Required environment variables (infra/.env)")
    st.code(
        "SNOWFLAKE_ACCOUNT=\n"
        "SNOWFLAKE_USER=\n"
        "SNOWFLAKE_PASSWORD=\n"
        "SNOWFLAKE_ROLE=ACCOUNTADMIN\n"
        "SNOWFLAKE_WAREHOUSE=COMPUTE_WH\n"
        "SNOWFLAKE_DATABASE=IOT_DB\n"
        "SNOWFLAKE_SCHEMA=RAW",
        language="bash",
    )
