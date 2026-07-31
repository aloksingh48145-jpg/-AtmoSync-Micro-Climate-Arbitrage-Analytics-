-- Scores each sensor reading against its commodity's safe temperature/humidity
-- band. Deviation columns are 0 when within band, and positive when outside
-- it (in degrees C / percentage points over the nearest limit).
--
-- risk_severity_score combines both deviations into a single number that
-- dashboards / alerting can threshold on to flag "arbitrage windows" --
-- i.e. shipments at high spoilage risk that should be rerouted, discounted,
-- or liquidated before the loss is total.

with readings as (

    select * from {{ ref('stg_sensor_readings') }}

),

thresholds as (

    select * from {{ ref('commodity_thresholds') }}

),

scored as (

    select
        r.event_id,
        r.shipment_id,
        r.commodity,
        r.origin,
        r.destination,
        r.temperature_c,
        r.humidity_pct,
        r.recorded_at,

        greatest(r.temperature_c - t.temp_max_c, t.temp_min_c - r.temperature_c, 0)
            as temp_deviation_c,
        greatest(r.humidity_pct - t.humidity_max_pct, t.humidity_min_pct - r.humidity_pct, 0)
            as humidity_deviation_pct,

        r.spoilage_risk_flag as source_flagged_risk

    from readings r
    left join thresholds t
        on r.commodity = t.commodity

),

final as (

    select
        *,
        -- simple weighted severity score; tune weights once real loss data exists
        round((temp_deviation_c * 1.5) + (humidity_deviation_pct * 0.5), 2)
            as risk_severity_score,
        case
            when temp_deviation_c > 0 or humidity_deviation_pct > 0 then true
            else false
        end as out_of_band,
        case
            when (temp_deviation_c * 1.5) + (humidity_deviation_pct * 0.5) >= 10 then 'high'
            when (temp_deviation_c * 1.5) + (humidity_deviation_pct * 0.5) > 0  then 'moderate'
            else 'none'
        end as arbitrage_window
    from scored

)

select * from final
