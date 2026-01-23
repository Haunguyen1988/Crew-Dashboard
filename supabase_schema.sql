-- =====================================================
-- SUPABASE TABLES FOR CREW DASHBOARD
-- Run this SQL in Supabase SQL Editor
-- Dashboard -> SQL Editor -> New Query -> Paste & Run
-- =====================================================

-- 1. FLIGHTS TABLE (from DayRepReport CSV)
CREATE TABLE IF NOT EXISTS flights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date TEXT NOT NULL,
    calendar_date TEXT,
    reg TEXT NOT NULL,
    flt TEXT,
    dep TEXT,
    arr TEXT,
    std TEXT,
    sta TEXT,
    crew TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for date filtering
CREATE INDEX IF NOT EXISTS idx_flights_date ON flights(date);
CREATE INDEX IF NOT EXISTS idx_flights_reg ON flights(reg);

-- 2. AC UTILIZATION TABLE (from SacutilReport CSV)
CREATE TABLE IF NOT EXISTS ac_utilization (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date TEXT NOT NULL,
    ac_type TEXT NOT NULL,
    dom_block TEXT,
    int_block TEXT,
    total_block TEXT,
    dom_cycles INTEGER DEFAULT 0,
    int_cycles INTEGER DEFAULT 0,
    total_cycles INTEGER DEFAULT 0,
    avg_util TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ac_util_date ON ac_utilization(date);
CREATE INDEX IF NOT EXISTS idx_ac_util_type ON ac_utilization(ac_type);

-- 3. ROLLING HOURS TABLE (from RolCrTotReport CSV)
CREATE TABLE IF NOT EXISTS rolling_hours (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    crew_id TEXT NOT NULL,
    name TEXT,
    seniority TEXT,
    block_28day TEXT,
    block_12month TEXT,
    hours_28day FLOAT DEFAULT 0,
    hours_12month FLOAT DEFAULT 0,
    percentage FLOAT DEFAULT 0,
    percentage_12m FLOAT DEFAULT 0,
    status TEXT DEFAULT 'normal',
    status_12m TEXT DEFAULT 'normal',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rolling_crew ON rolling_hours(crew_id);
CREATE INDEX IF NOT EXISTS idx_rolling_status ON rolling_hours(status);

-- 4. CREW SCHEDULE TABLE (from Crew Schedule CSV)
CREATE TABLE IF NOT EXISTS crew_schedule (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date TEXT NOT NULL,
    crew_id TEXT,
    status_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crew_sched_date ON crew_schedule(date);
CREATE INDEX IF NOT EXISTS idx_crew_sched_status ON crew_schedule(status_type);

-- 5. STANDBY RECORDS TABLE (individual crew with date ranges)
CREATE TABLE IF NOT EXISTS standby_records (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    crew_id TEXT NOT NULL,
    name TEXT,
    base TEXT,
    status_type TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(crew_id, status_type, start_date)
);

CREATE INDEX IF NOT EXISTS idx_standby_crew ON standby_records(crew_id);
CREATE INDEX IF NOT EXISTS idx_standby_start ON standby_records(start_date);
CREATE INDEX IF NOT EXISTS idx_standby_end ON standby_records(end_date);
CREATE INDEX IF NOT EXISTS idx_standby_status ON standby_records(status_type);

-- =====================================================
-- ENABLE ROW LEVEL SECURITY (RLS) - Set to allow all for now
-- =====================================================

ALTER TABLE flights ENABLE ROW LEVEL SECURITY;
ALTER TABLE ac_utilization ENABLE ROW LEVEL SECURITY;
ALTER TABLE rolling_hours ENABLE ROW LEVEL SECURITY;
ALTER TABLE crew_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE standby_records ENABLE ROW LEVEL SECURITY;

-- Create policies to allow anonymous access (for demo purposes)
-- Create policies to allow anonymous access (for demo purposes)
-- Note: 'FOR ALL' covers SELECT, INSERT, UPDATE, DELETE
DROP POLICY IF EXISTS "Allow all access to flights" ON flights;
CREATE POLICY "Allow all access to flights" ON flights FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all access to ac_utilization" ON ac_utilization;
CREATE POLICY "Allow all access to ac_utilization" ON ac_utilization FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all access to rolling_hours" ON rolling_hours;
CREATE POLICY "Allow all access to rolling_hours" ON rolling_hours FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all access to crew_schedule" ON crew_schedule;
CREATE POLICY "Allow all access to crew_schedule" ON crew_schedule FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all access to standby_records" ON standby_records;
CREATE POLICY "Allow all access to standby_records" ON standby_records FOR ALL USING (true) WITH CHECK (true);

-- =====================================================
-- VERIFY TABLES CREATED
-- =====================================================
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
