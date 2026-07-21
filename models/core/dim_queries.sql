-- Queries Dimension Table
-- Google Search Quality Intelligence Platform

{{ config(
    materialized='table',
    unique_key='query_key'
) }}

select
    query_key,
    search_query_masked,
    search_intent,
    query_category,
    is_navigational,
    is_informational,
    is_transactional,
    query_length_words
from {{ ref('stg_queries') }}
