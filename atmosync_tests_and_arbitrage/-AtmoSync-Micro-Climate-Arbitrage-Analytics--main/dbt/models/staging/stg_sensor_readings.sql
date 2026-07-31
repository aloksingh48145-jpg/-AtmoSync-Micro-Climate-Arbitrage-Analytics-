-- Flattens raw JSON sensor payloads into typed, analysis-ready columns.
-- One row per sensor reading event.

with source as (

    select
        event_id,
        raw_payload,
        loaded_at
    from {{ source('raw', 'sensor_readings') }}

),

flattened as (

    select
        event_id,
        raw_payload:shipment_id::string      as shipment_id,
        raw_payload:commodity::string        as commodity,
        raw_payload:origin::string           as origin,
        raw_payload:destination::string      as destination,
        raw_payload:temperature_c::float     as temperature_c,
        raw_payload:humidity_pct::float      as humidity_pct,
        raw_payload:spoilage_risk::boolean   as spoilage_risk_flag,
        raw_payload:recorded_at::timestamp_ntz as recorded_at,
        loaded_at
    from source

)

select * from flattened
