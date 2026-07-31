-- AtmoSync Snowflake setup
-- Uses your existing IOT_DB database and the account's default COMPUTE_WH
-- warehouse / ACCOUNTADMIN role, instead of creating project-specific ones.
-- Run this in a Snowflake worksheet with "Run All" (not just a selected
-- block) so every statement executes in the same session.

-- 1. Database + schemas (IOT_DB may already exist from earlier setup)
CREATE DATABASE IF NOT EXISTS IOT_DB;

CREATE SCHEMA IF NOT EXISTS IOT_DB.RAW;
CREATE SCHEMA IF NOT EXISTS IOT_DB.STAGING;
CREATE SCHEMA IF NOT EXISTS IOT_DB.MARTS;

-- 2. Raw landing table for sensor readings
-- Stored as VARIANT (semi-structured) so the full JSON payload (including
-- shipment_id, commodity, origin, destination) is preserved. dbt's
-- stg_sensor_readings model flattens/types this into columns.
--
-- NOTE: if you already created a SENSOR_READINGS table with separate typed
-- columns (SENSOR_ID, TEMPERATURE, HUMIDITY, ...), drop it first so this
-- VARIANT version replaces it -- the two schemas are incompatible:
-- DROP TABLE IF EXISTS IOT_DB.RAW.SENSOR_READINGS;

CREATE TABLE IF NOT EXISTS IOT_DB.RAW.SENSOR_READINGS (
    event_id        STRING,
    raw_payload      VARIANT,
    loaded_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 3. (Optional) Snowpipe alternative note:
-- For production, prefer Snowpipe + an external stage (S3/GCS/Azure) fed by
-- a Kafka Connect Snowflake sink connector, rather than a custom Python
-- consumer. The Python consumer in ingestion/snowflake_consumer.py is a
-- dev/prototype path that batches inserts directly via the Snowflake
-- connector -- good enough to validate the pipeline end-to-end before
-- investing in Kafka Connect infra.
