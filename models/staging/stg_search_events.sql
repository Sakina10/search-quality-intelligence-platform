-- Search Events Staging View
-- Google Search Quality Intelligence Platform

select
    cast(event_id as varchar(64)) as event_id,
    cast(event_timestamp as timestamp) as event_timestamp,
    cast(user_key as varchar(64)) as user_key,
    cast(query_key as varchar(64)) as query_key,
    cast(system_key as varchar(64)) as system_key,
    cast(geo_key as varchar(64)) as geo_key,
    cast(session_id as varchar(64)) as session_id,
    cast(position as integer) as position,
    cast(clicks as integer) as clicks,
    cast(impressions as integer) as impressions,
    cast(latency_ms as numeric) as latency_ms,
    cast(page_speed_score as numeric) as page_speed_score,
    cast(bounce_rate as numeric) as bounce_rate,
    cast(pogo_stick_flag as integer) as pogo_stick_flag,
    cast(reformulation_flag as integer) as reformulation_flag,
    cast(dwell_time_sec as numeric) as dwell_time_sec,
    cast(revenue_estimate_usd as numeric) as revenue_estimate_usd,
    cast(search_quality_score as numeric) as search_quality_score
from {{ source('raw_logs', 'fct_search_events') }}
