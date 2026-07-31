-- One row per shipment, summarizing spoilage risk across all its readings.
-- This is the table Superset dashboards should query for "which shipments
-- need attention right now" style views.

with risk_events as (

    select * from {{ ref('fct_spoilage_risk') }}

),

aggregated as (

    select
        shipment_id,
        commodity,
        origin,
        destination,

        count(*)                                              as total_readings,
        count_if(out_of_band)                                 as out_of_band_readings,
        max(risk_severity_score)                               as peak_severity_score,
        avg(risk_severity_score)                               as avg_severity_score,
        max(recorded_at)                                       as last_reading_at,

        max(case when arbitrage_window = 'high' then 1 else 0 end) = 1
            as has_high_risk_window

    from risk_events
    group by shipment_id, commodity, origin, destination

)

select
    *,
    round(100.0 * out_of_band_readings / nullif(total_readings, 0), 1)
        as pct_readings_out_of_band
from aggregated
