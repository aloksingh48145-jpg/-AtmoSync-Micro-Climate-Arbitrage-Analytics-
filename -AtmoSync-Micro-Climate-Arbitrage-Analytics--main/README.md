# AtmoSync — Micro-Climate Arbitrage Analytics

IoT streaming pipeline for spoilage arbitrage analytics using Kafka, Snowflake, dbt, and Superset.

## Architecture

```
IoT sensors → Kafka (Redpanda) → Snowflake (raw) → dbt (staging/marts) → Superset (dashboards)
```

## Project structure

```
ingestion/      Kafka producer(s) simulating/reading IoT sensor + spoilage data
dbt/            dbt project: staging models, marts, Snowflake profile template
superset/       Superset dashboard configs/exports
infra/          docker-compose stack + environment variable templates
scripts/        one-off setup/utility scripts
```

## Getting started

1. Copy env template and fill in Snowflake credentials:
   ```
   cp infra/.env.example infra/.env
   ```
2. Start the local stack (Redpanda broker + console, Superset):
   ```
   docker compose -f infra/docker-compose.yml up -d
   ```
3. Install ingestion dependencies:
   ```
   pip install -r ingestion/requirements.txt
   ```
4. (Coming next) Run the producer to start streaming simulated sensor readings, then set up dbt models against the raw Snowflake tables.

## Status

- [x] Repo scaffolding, docker-compose stack, env/config templates
- [ ] Kafka producer: simulated IoT sensor + spoilage event data
- [ ] Snowflake raw ingestion (consumer or Snowpipe)
- [ ] dbt staging + marts models
- [ ] Superset dashboards
