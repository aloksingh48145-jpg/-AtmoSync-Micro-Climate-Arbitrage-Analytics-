"""
AtmoSync sensor producer.

Simulates IoT temperature/humidity sensors attached to perishable shipments
(e.g. refrigerated trucks/containers) and streams readings to Kafka.

Each simulated shipment drifts within a normal range most of the time, but
occasionally enters a "spoilage risk" excursion (temp/humidity out of safe
band) so downstream consumers/dbt models have real signal to detect and
score arbitrage opportunities on.

Usage:
    python sensor_producer.py
    python sensor_producer.py --shipments 20 --interval 2 --duration 300
"""

import argparse
import json
import os
import random
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from confluent_kafka import Producer
from dotenv import load_dotenv
from faker import Faker

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "infra", ".env"))

fake = Faker()

TOPIC = os.getenv("KAFKA_TOPIC_SENSOR_READINGS", "iot.sensor.readings")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Safe operating bands per commodity type (temp in Celsius, humidity in %)
COMMODITY_PROFILES = {
    "dairy":    {"temp_range": (2.0, 4.0),  "humidity_range": (80, 90)},
    "produce":  {"temp_range": (0.0, 4.0),  "humidity_range": (85, 95)},
    "meat":     {"temp_range": (-2.0, 2.0), "humidity_range": (75, 85)},
    "seafood":  {"temp_range": (-1.0, 1.0), "humidity_range": (85, 95)},
    "flowers":  {"temp_range": (1.0, 4.0),  "humidity_range": (85, 95)},
}


@dataclass
class Shipment:
    shipment_id: str
    commodity: str
    origin: str
    destination: str
    in_excursion: bool = False
    excursion_ticks_left: int = 0


def make_shipments(n: int) -> list[Shipment]:
    shipments = []
    for _ in range(n):
        commodity = random.choice(list(COMMODITY_PROFILES.keys()))
        shipments.append(
            Shipment(
                shipment_id=str(uuid.uuid4()),
                commodity=commodity,
                origin=fake.city(),
                destination=fake.city(),
            )
        )
    return shipments


def next_reading(shipment: Shipment) -> dict:
    profile = COMMODITY_PROFILES[shipment.commodity]
    temp_lo, temp_hi = profile["temp_range"]
    hum_lo, hum_hi = profile["humidity_range"]

    # Randomly trigger a spoilage-risk excursion (~3% chance per tick),
    # lasting a handful of ticks once started.
    if not shipment.in_excursion and random.random() < 0.03:
        shipment.in_excursion = True
        shipment.excursion_ticks_left = random.randint(3, 8)

    if shipment.in_excursion:
        # Push readings outside the safe band
        temperature = round(temp_hi + random.uniform(2, 8), 2)
        humidity = round(hum_hi + random.uniform(2, 10), 2)
        shipment.excursion_ticks_left -= 1
        if shipment.excursion_ticks_left <= 0:
            shipment.in_excursion = False
    else:
        temperature = round(random.uniform(temp_lo, temp_hi), 2)
        humidity = round(random.uniform(hum_lo, hum_hi), 2)

    return {
        "event_id": str(uuid.uuid4()),
        "shipment_id": shipment.shipment_id,
        "commodity": shipment.commodity,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "spoilage_risk": shipment.in_excursion,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def delivery_report(err, msg):
    if err is not None:
        print(f"[ERROR] delivery failed: {err}")
    else:
        print(f"[OK] {msg.key().decode()} -> {msg.topic()} @ offset {msg.offset()}")


def run(num_shipments: int, interval_seconds: float, duration_seconds: int | None):
    producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})
    shipments = make_shipments(num_shipments)

    print(f"Producing to topic '{TOPIC}' on {BOOTSTRAP_SERVERS}")
    print(f"Simulating {num_shipments} shipments every {interval_seconds}s"
          + (f" for {duration_seconds}s" if duration_seconds else " (until Ctrl+C)"))

    start = time.time()
    try:
        while True:
            for shipment in shipments:
                reading = next_reading(shipment)
                producer.produce(
                    TOPIC,
                    key=reading["shipment_id"],
                    value=json.dumps(reading),
                    callback=delivery_report,
                )
            producer.poll(0)
            producer.flush(timeout=5)

            if duration_seconds and (time.time() - start) >= duration_seconds:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.flush()


def parse_args():
    parser = argparse.ArgumentParser(description="AtmoSync simulated sensor producer")
    parser.add_argument("--shipments", type=int, default=10, help="Number of simulated shipments")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between reading batches")
    parser.add_argument("--duration", type=int, default=None, help="Total run time in seconds (default: run forever)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.shipments, args.interval, args.duration)
