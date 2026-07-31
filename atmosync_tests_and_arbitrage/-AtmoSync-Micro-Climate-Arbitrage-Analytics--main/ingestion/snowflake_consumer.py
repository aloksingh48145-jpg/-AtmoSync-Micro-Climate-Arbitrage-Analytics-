"""
AtmoSync Snowflake ingestion consumer.

Reads sensor readings off Kafka and batches them into the raw Snowflake
landing table (ATMOSYNC_DB.RAW.SENSOR_READINGS) as VARIANT rows, so dbt
staging models can flatten/type them downstream.

This is a dev/prototype ingestion path (direct connector inserts). For
production-scale volume, swap this for Kafka Connect's Snowflake sink
connector + Snowpipe -- see scripts/snowflake_setup.sql for notes.

Usage:
    python snowflake_consumer.py
    python snowflake_consumer.py --batch-size 100 --flush-interval 5
"""

import argparse
import json
import os
import time

import snowflake.connector
from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "infra", ".env"))

TOPIC = os.getenv("KAFKA_TOPIC_SENSOR_READINGS", "iot.sensor.readings")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

INSERT_SQL = """
    INSERT INTO IOT_DB.RAW.SENSOR_READINGS (event_id, raw_payload)
    SELECT $1, PARSE_JSON($2)
    FROM VALUES (%s, %s)
"""


def get_snowflake_connection():
    required = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_ROLE", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required Snowflake env vars: {', '.join(missing)}. "
            f"Fill these in infra/.env before running this consumer."
        )

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


def flush_batch(cursor, batch: list[tuple[str, str]]):
    if not batch:
        return
    cursor.executemany(INSERT_SQL, batch)
    print(f"[Snowflake] inserted {len(batch)} rows")


def run(batch_size: int, flush_interval: float):
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": "atmosync-snowflake-sink",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    print(f"Consuming '{TOPIC}' from {BOOTSTRAP_SERVERS} -> Snowflake ATMOSYNC_DB.RAW.SENSOR_READINGS")
    print(f"Batch size: {batch_size}, flush interval: {flush_interval}s (Ctrl+C to stop)")

    batch: list[tuple[str, str]] = []
    last_flush = time.time()

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is not None and not msg.error():
                reading = json.loads(msg.value())
                batch.append((reading["event_id"], json.dumps(reading)))

            should_flush = (
                len(batch) >= batch_size
                or (batch and (time.time() - last_flush) >= flush_interval)
            )
            if should_flush:
                flush_batch(cursor, batch)
                conn.commit()
                consumer.commit(asynchronous=False)
                batch = []
                last_flush = time.time()

    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        flush_batch(cursor, batch)
        conn.commit()
        cursor.close()
        conn.close()
        consumer.close()


def parse_args():
    parser = argparse.ArgumentParser(description="AtmoSync Kafka -> Snowflake sink consumer")
    parser.add_argument("--batch-size", type=int, default=50, help="Rows per batch insert")
    parser.add_argument("--flush-interval", type=float, default=5.0, help="Max seconds between flushes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.batch_size, args.flush_interval)
