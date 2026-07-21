-- PostgreSQL Data Warehouse Schema DDL
-- Google Search Quality Intelligence Platform
-- Target Database: PostgreSQL 14+

-- -----------------------------------------------------------------------------
-- 1. CLEANUP PRE-EXISTING OBJECTS
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS fct_search_events CASCADE;
DROP TABLE IF EXISTS dim_users CASCADE;
DROP TABLE IF EXISTS dim_queries CASCADE;
DROP TABLE IF EXISTS dim_systems CASCADE;
DROP TABLE IF EXISTS dim_geography CASCADE;

-- -----------------------------------------------------------------------------
-- 2. DIMENSION TABLES CREATION
-- -----------------------------------------------------------------------------

-- Dimension: Users (Tracks user metadata over time using SCD Type 2)
CREATE TABLE dim_users (
    user_key VARCHAR(64) PRIMARY KEY,
    user_id_masked VARCHAR(64) NOT NULL,
    gender VARCHAR(10),
    age INTEGER,
    signup_channel VARCHAR(50),
    signup_timestamp TIMESTAMP,
    user_segment VARCHAR(10),
    record_start_timestamp TIMESTAMP NOT NULL,
    record_end_timestamp TIMESTAMP,
    is_current_record INTEGER NOT NULL CHECK (is_current_record IN (0, 1))
);

-- Dimension: Queries (Search queries classifications)
CREATE TABLE dim_queries (
    query_key VARCHAR(64) PRIMARY KEY,
    search_query_masked TEXT NOT NULL,
    search_intent VARCHAR(30),
    query_category VARCHAR(50),
    is_navigational INTEGER NOT NULL CHECK (is_navigational IN (0, 1)),
    is_informational INTEGER NOT NULL CHECK (is_informational IN (0, 1)),
    is_transactional INTEGER NOT NULL CHECK (is_transactional IN (0, 1)),
    query_length_words INTEGER NOT NULL CHECK (query_length_words > 0)
);

-- Dimension: Systems (Technical user agents details)
CREATE TABLE dim_systems (
    system_key VARCHAR(64) PRIMARY KEY,
    device_type VARCHAR(30) NOT NULL,
    browser_name VARCHAR(30) NOT NULL,
    os_name VARCHAR(30) NOT NULL,
    browser_version VARCHAR(20)
);

-- Dimension: Geography (Geographic locations mapping)
CREATE TABLE dim_geography (
    geo_key VARCHAR(64) PRIMARY KEY,
    country VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    primary_language VARCHAR(10) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. PARTITIONED FACT TABLE CREATION
-- -----------------------------------------------------------------------------

-- Fact Table: Search Events (Partitioned by range of event_timestamp)
CREATE TABLE fct_search_events (
    event_id VARCHAR(64) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    user_key VARCHAR(64) REFERENCES dim_users(user_key),
    query_key VARCHAR(64) REFERENCES dim_queries(query_key),
    system_key VARCHAR(64) REFERENCES dim_systems(system_key),
    geo_key VARCHAR(64) REFERENCES dim_geography(geo_key),
    session_id VARCHAR(64) NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 1 AND position <= 10),
    clicks INTEGER NOT NULL CHECK (clicks IN (0, 1)),
    impressions INTEGER NOT NULL CHECK (impressions = 1),
    latency_ms NUMERIC NOT NULL CHECK (latency_ms >= 0.0),
    page_speed_score NUMERIC NOT NULL CHECK (page_speed_score BETWEEN 0.0 AND 100.0),
    bounce_rate NUMERIC NOT NULL CHECK (bounce_rate BETWEEN 0.0 AND 1.0),
    pogo_stick_flag INTEGER NOT NULL CHECK (pogo_stick_flag IN (0, 1)),
    reformulation_flag INTEGER NOT NULL CHECK (reformulation_flag IN (0, 1)),
    dwell_time_sec NUMERIC NOT NULL CHECK (dwell_time_sec >= 0.0),
    revenue_estimate_usd NUMERIC NOT NULL CHECK (revenue_estimate_usd >= 0.0),
    search_quality_score NUMERIC NOT NULL CHECK (search_quality_score BETWEEN 0.0 AND 100.0),
    PRIMARY KEY (event_id, event_timestamp)
) PARTITION BY RANGE (event_timestamp);

-- -----------------------------------------------------------------------------
-- 4. PARTITION DEFINITIONS
-- -----------------------------------------------------------------------------

-- Monthly Partition: June 2026
CREATE TABLE fct_search_events_2026_06 PARTITION OF fct_search_events
    FOR VALUES FROM ('2026-06-01 00:00:00') TO ('2026-07-01 00:00:00');

-- Monthly Partition: July 2026
CREATE TABLE fct_search_events_2026_07 PARTITION OF fct_search_events
    FOR VALUES FROM ('2026-07-01 00:00:00') TO ('2026-08-01 00:00:00');

-- Catch-all Default Partition
CREATE TABLE fct_search_events_default PARTITION OF fct_search_events DEFAULT;

-- -----------------------------------------------------------------------------
-- 5. INDEX OPTIMIZATIONS
-- -----------------------------------------------------------------------------

-- Indexing Foreign Keys on the base partitioned table
CREATE INDEX idx_fct_search_events_user ON fct_search_events(user_key);
CREATE INDEX idx_fct_search_events_query ON fct_search_events(query_key);
CREATE INDEX idx_fct_search_events_system ON fct_search_events(system_key);
CREATE INDEX idx_fct_search_events_geo ON fct_search_events(geo_key);

-- Filtered Index for active current records inside the SCD Type 2 Users Dimension
CREATE INDEX idx_dim_users_active ON dim_users(user_id_masked) 
    WHERE is_current_record = 1;

-- Indexing Query categories inside Queries Dimension
CREATE INDEX idx_dim_queries_category ON dim_queries(query_category);

-- Indexing Country and Region inside Geography Dimension
CREATE INDEX idx_dim_geography_country ON dim_geography(country, region);
