-- =====================================================
-- MIGRATION: Add 12-month columns to rolling_hours table
-- Run this SQL in Supabase SQL Editor to add missing columns
-- =====================================================

-- Add percentage_12m column if not exists
ALTER TABLE rolling_hours 
ADD COLUMN IF NOT EXISTS percentage_12m FLOAT DEFAULT 0;

-- Add status_12m column if not exists
ALTER TABLE rolling_hours 
ADD COLUMN IF NOT EXISTS status_12m TEXT DEFAULT 'normal';

-- Verify columns added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'rolling_hours'
ORDER BY ordinal_position;
