-- Geography Staging View
-- Google Search Quality Intelligence Platform

select
    cast(geo_key as varchar(64)) as geo_key,
    cast(country as varchar(50)) as country,
    cast(region as varchar(50)) as region,
    cast(primary_language as varchar(10)) as language
from {{ source('raw_logs', 'dim_geography') }}
