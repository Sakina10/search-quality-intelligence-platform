-- Users Staging View
-- Google Search Quality Intelligence Platform

select
    cast(user_key as varchar(64)) as user_key,
    cast(user_id_masked as varchar(64)) as user_id_masked,
    cast(gender as varchar(10)) as gender,
    cast(age as integer) as age,
    cast(signup_channel as varchar(50)) as signup_channel,
    cast(signup_timestamp as timestamp) as signup_timestamp,
    cast(user_segment as varchar(10)) as user_segment,
    cast(record_start_timestamp as timestamp) as record_start_timestamp,
    cast(record_end_timestamp as timestamp) as record_end_timestamp,
    cast(is_current_record as integer) as is_current_record
from {{ source('raw_logs', 'dim_users') }}
