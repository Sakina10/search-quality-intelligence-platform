-- Users Dimension Table (SCD Type 2)
-- Google Search Quality Intelligence Platform

{{ config(
    materialized='table',
    unique_key='user_key'
) }}

select
    user_key,
    user_id_masked,
    gender,
    age,
    signup_channel,
    signup_timestamp,
    user_segment,
    record_start_timestamp,
    record_end_timestamp,
    is_current_record
from {{ ref('stg_users') }}
