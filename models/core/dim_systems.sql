-- Systems Dimension Table
-- Google Search Quality Intelligence Platform

{{ config(
    materialized='table',
    unique_key='system_key'
) }}

select
    system_key,
    device_type,
    browser_name,
    os_name,
    browser_version
from {{ ref('stg_systems') }}
