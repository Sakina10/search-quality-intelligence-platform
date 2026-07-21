-- Queries Staging View
-- Google Search Quality Intelligence Platform

select
    cast(query_key as varchar(64)) as query_key,
    lower(trim(cast(search_query_masked as text))) as search_query_masked,
    cast(search_intent as varchar(30)) as search_intent,
    cast(query_category as varchar(50)) as query_category,
    cast(is_navigational as integer) as is_navigational,
    cast(is_informational as integer) as is_informational,
    cast(is_transactional as integer) as is_transactional,
    cast(query_length_words as integer) as query_length_words
from {{ source('raw_logs', 'dim_queries') }}
