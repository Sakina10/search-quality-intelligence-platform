-- Systems Staging View
-- Google Search Quality Intelligence Platform

select
    cast(system_key as varchar(64)) as system_key,
    cast(device_type as varchar(30)) as device_type,
    cast(browser_name as varchar(30)) as browser_name,
    cast(os_name as varchar(30)) as os_name,
    cast(browser_version as varchar(20)) as browser_version
from {{ source('raw_logs', 'dim_systems') }}
