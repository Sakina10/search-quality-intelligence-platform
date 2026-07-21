-- Geography Dimension Table
-- Google Search Quality Intelligence Platform

{{ config(
    materialized='table',
    unique_key='geo_key'
) }}

select
    geo_key,
    country,
    region,
    language
from {{ ref('stg_geography') }}
