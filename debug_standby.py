"""
Debug script to verify standby data fix
"""

import supabase_client as db
from data_processor import DataProcessor
from datetime import datetime

def main():
    print("=" * 60)
    print("VERIFYING STANDBY DATA FIX")
    print("=" * 60)
    
    # 1. Check Supabase connection
    print("\n1. Checking Supabase connection...")
    if db.is_connected():
        print("[OK] Connected to Supabase")
    else:
        print("[FAIL] NOT connected to Supabase")
        return
    
    # 2. Create fresh processor to test the fix
    print("\n2. Creating fresh DataProcessor...")
    processor = DataProcessor()
    
    # 3. Check if standby_records was reconstructed
    print(f"\n3. standby_records count: {len(processor.standby_records)}")
    
    if processor.standby_records:
        # Check unique dates in standby_records
        dates = set()
        for rec in processor.standby_records:
            dates.add(rec.get('start_date', ''))
        print(f"   Unique dates in standby_records: {sorted(dates)[:10]}")
        
        # Show sample
        print("\n   Sample records:")
        for i, rec in enumerate(processor.standby_records[:3]):
            print(f"   [{i+1}] status={rec.get('status_type')}, start={rec.get('start_date')}, end={rec.get('end_date')}")
    
    # 4. Test calculate_metrics with different date filters
    print("\n4. Testing calculate_metrics with date filters...")
    
    test_dates = [None, '2026-02-09', '2025-02-03']
    
    for test_date in test_dates:
        metrics = processor.calculate_metrics(filter_date=test_date)
        summary = metrics.get('crew_schedule', {}).get('summary', {})
        sby_count = summary.get('SBY', 0) + summary.get('OSBY', 0)
        sl_count = summary.get('SL', 0) + summary.get('CSL', 0)
        print(f"\n   Filter: {test_date or 'All Dates'}")
        print(f"   -> Standby Available (SBY+OSBY): {sby_count}")
        print(f"   -> Sick/Call-Sick (SL+CSL): {sl_count}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
