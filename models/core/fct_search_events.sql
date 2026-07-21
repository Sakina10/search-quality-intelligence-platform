-- Search Events Fact Table
-- Google Search Quality Intelligence Platform

{{ config(
    materialized='incremental',
    unique_key='event_id'
) }}

with staging_events as (
    select * from {{ ref('stg_search_events') }}
    
    {% if is_incremental() %}
        -- Only process new search events relative to already ingested warehouse records
        where event_timestamp > (select max(event_timestamp) from {{ this }})
    {% endif %}
)

select
    event_id,
    event_timestamp,
    user_key,
    query_key,
    system_key,
    geo_key,
    session_id,
    position,
    clicks,
    impressions,
    latency_ms,
    page_speed_score,
    bounce_rate,
    pogo_stick_flag,
    reformulation_flag,
    dwell_time_sec,
    revenue_estimate_usd,
    search_quality_score,
    -- Session step sequence logic using window function
    row_number() over (
        partition by session_id 
        order by event_timestamp
    ) as session_event_sequence
from staging_events
