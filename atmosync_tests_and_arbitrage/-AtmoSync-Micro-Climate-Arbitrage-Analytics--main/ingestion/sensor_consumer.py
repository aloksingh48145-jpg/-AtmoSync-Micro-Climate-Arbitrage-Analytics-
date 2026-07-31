"""
AtmoSync sensor consumer (dev/debug tool).

Reads and pretty-prints messages from the sensor readings topic so you can
verify the producer is working end-to-end before wiring up real Snowflake
ingestion.

Usage:
    python sensor_consumer.py
"""

import json
import os

from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "infra", ".env"))

TOPIC = os.getenv("KAFKA_TOPIC_SENSOR_READINGS", "iot.sensor.readings")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "group.id": "atmosync-debug-consumer",
    "auto.offset.reset": "earliest",
})

consumer.subscribe([TOPIC])

print(f"Listening on '{TOPIC}' at {BOOTSTRAP_SERVERS} (Ctrl+C to stop)...")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[ERROR] {msg.error()}")
            continue

        reading = json.loads(msg.value())
        flag = "SPOILAGE RISK" if reading["spoilage_risk"] else "ok"
        print(
            f"[{reading['recorded_at']}] {reading['commodity']:8s} "
            f"shipment={reading['shipment_id'][:8]} "
            f"temp={reading['temperature_c']:>6.2f}C "
            f"hum={reading['humidity_pct']:>6.2f}% "
            f"-> {flag}"
        )
except KeyboardInterrupt:
    print("\nStopping consumer...")
finally:
    consumer.close()
