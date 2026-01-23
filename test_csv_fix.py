"""
Test the Crew Schedule CSV parsing fix
"""

import sys
sys.path.insert(0, '.')

from data_processor import DataProcessor
from pathlib import Path

def main():
    print("=" * 60)
    print("TESTING CREW SCHEDULE CSV PARSING FIX")
    print("=" * 60)
    
    # Create fresh processor (don't load from Supabase)
    processor = DataProcessor(Path('.'))
    
    # Find the new CSV file
    csv_file = Path('Crew schedule 01-28Feb(standby,callsick, fatigue).csv')
    
    if not csv_file.exists():
        print(f"[ERROR] File not found: {csv_file}")
        return
    
    print(f"\n1. Processing file: {csv_file}")
    count = processor.process_crew_schedule_csv(file_path=csv_file, sync_db=False)
    print(f"   Records processed: {count}")
    
    # Check standby_records
    print(f"\n2. standby_records count: {len(processor.standby_records)}")
    
    if processor.standby_records:
        # Check unique dates
        dates = set()
        for rec in processor.standby_records:
            dates.add(rec.get('start_date', ''))
        
        sorted_dates = sorted(dates)
        print(f"   Unique dates: {sorted_dates[:10]}")
        
        # Check if year is 26 (not 25)
        year_26_count = sum(1 for d in dates if d.endswith('/26'))
        year_25_count = sum(1 for d in dates if d.endswith('/25'))
        print(f"\n3. Year check:")
        print(f"   Dates ending with /26: {year_26_count}")
        print(f"   Dates ending with /25: {year_25_count}")
        
        if year_26_count > 0:
            print("   [OK] Fix is working - dates are using 2026!")
        else:
            print("   [FAIL] Still using wrong year")
    
    # Test filtering
    print("\n4. Testing calculate_metrics with date filter...")
    test_date = '2026-02-09'
    metrics = processor.calculate_metrics(filter_date=test_date)
    summary = metrics.get('crew_schedule', {}).get('summary', {})
    sby_count = summary.get('SBY', 0) + summary.get('OSBY', 0)
    
    print(f"   Filter: {test_date}")
    print(f"   Standby Available (SBY+OSBY): {sby_count}")
    
    if sby_count > 0:
        print("   [OK] Standby data is now visible!")
    else:
        print("   [WARN] Standby still showing 0")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
