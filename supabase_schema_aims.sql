-- =====================================================
-- SUPABASE AIMS STAGING TABLES
-- Additional tables for AIMS API data sync
-- Run this SQL in Supabase SQL Editor after main schema
-- =====================================================

-- 1. DIM_CREW: Crew master data from AIMS
CREATE TABLE IF NOT EXISTS dim_crew (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    crew_id TEXT UNIQUE NOT NULL,
    name TEXT,
    short_name TEXT,
    qualifications TEXT,
    email TEXT,
    location TEXT,
    nationality TEXT,
    employment_date TEXT,
    contact_cell TEXT,
    source TEXT DEFAULT 'AIMS_API',
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. FACT_ACTUALS: Flight actuals from AIMS (block times, delays)
CREATE TABLE IF NOT EXISTS fact_actuals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    flight_date TEXT NOT NULL,
    flight_no TEXT NOT NULL,
    ac_reg TEXT,
    departure TEXT,
    arrival TEXT,
    std TEXT,
    sta TEXT,
    atd TEXT,
    ata TEXT,
    block_minutes INTEGER DEFAULT 0,
    status TEXT,
    source TEXT DEFAULT 'AIMS_API',
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flight_date, flight_no)
);

-- 3. FACT_ROSTER: Crew roster schedules
CREATE TABLE IF NOT EXISTS fact_roster (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    crew_id TEXT NOT NULL,
    activity_type TEXT,
    start_dt TIMESTAMPTZ,
    end_dt TIMESTAMPTZ,
    departure TEXT,
    arrival TEXT,
    carrier TEXT,
    route TEXT,
    crew_base TEXT,
    source TEXT DEFAULT 'AIMS_API',
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. FACT_LEG_MEMBERS: FetchLegMembersPerDay data
CREATE TABLE IF NOT EXISTS fact_leg_members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    leg_date TEXT NOT NULL,
    flight_no TEXT,
    reg TEXT,
    dep TEXT,
    arr TEXT,
    std TEXT,
    sta TEXT,
    crew_id TEXT,
    crew_name TEXT,
    crew_role TEXT,
    source TEXT DEFAULT 'AIMS_API',
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. ETL_LOG: Track ETL job runs
CREATE TABLE IF NOT EXISTS etl_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_name TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds FLOAT,
    flights_synced INTEGER DEFAULT 0,
    crew_synced INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT FALSE,
    errors JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- INDEXES for Performance
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_dim_crew_id ON dim_crew(crew_id);
CREATE INDEX IF NOT EXISTS idx_fact_actuals_date ON fact_actuals(flight_date);
CREATE INDEX IF NOT EXISTS idx_fact_actuals_flight ON fact_actuals(flight_no);
CREATE INDEX IF NOT EXISTS idx_fact_roster_crew ON fact_roster(crew_id);
CREATE INDEX IF NOT EXISTS idx_fact_roster_start ON fact_roster(start_dt);
CREATE INDEX IF NOT EXISTS idx_fact_leg_date ON fact_leg_members(leg_date);
CREATE INDEX IF NOT EXISTS idx_etl_log_time ON etl_log(start_time);

-- =====================================================
-- ENABLE ROW LEVEL SECURITY
-- =====================================================
ALTER TABLE dim_crew ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_actuals ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_roster ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_leg_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE etl_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies (allow all for dashboard)
DROP POLICY IF EXISTS "Allow all dim_crew" ON dim_crew;
CREATE POLICY "Allow all dim_crew" ON dim_crew FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all fact_actuals" ON fact_actuals;
CREATE POLICY "Allow all fact_actuals" ON fact_actuals FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all fact_roster" ON fact_roster;
CREATE POLICY "Allow all fact_roster" ON fact_roster FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all fact_leg_members" ON fact_leg_members;
CREATE POLICY "Allow all fact_leg_members" ON fact_leg_members FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all etl_log" ON etl_log;
CREATE POLICY "Allow all etl_log" ON etl_log FOR ALL USING (true) WITH CHECK (true);

-- =====================================================
-- VERIFY TABLES CREATED
-- =====================================================
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('dim_crew', 'fact_actuals', 'fact_roster', 'fact_leg_members', 'etl_log');
