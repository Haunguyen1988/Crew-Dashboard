from data_processor import DataProcessor
from unittest.mock import patch

def main():
    # Mock database connection to avoid timeout/dependency
    with patch('supabase_client.is_connected', return_value=False):
        processor = DataProcessor()
    
    # Test CSV Content with Date Header (Standard Format)
    # Note: Header date "15 Jan 2026" parses to "15/01/26" internally
    csv_content = """Crew Schedule Report
Report Date: 15 Jan 2026
ID,Name,Base,Rank,SL,CSL,SBY,OSBY
1001,Pilot A,SGN,CP,1,0,0,0
1002,Pilot B,HAN,FO,0,1,0,0
1003,Pilot C,DAD,PU,0,0,1,0
1004,Pilot D,SGN,FA,0,0,0,1
""".encode('utf-8')

    print("Processing Mock CrewSchedule CSV...")
    processor.process_crew_schedule_csv(file_content=csv_content, sync_db=False)
    
    # 1. Verify internal storage
    target_key = "15/01/26"
    print(f"By Date Keys: {list(processor.crew_schedule_by_date.keys())}")
    
    if target_key not in processor.crew_schedule_by_date:
        print(f"FAILURE: Expected key {target_key} not found.")
        return

    # 2. Test filtering with NORMALIZED date (as if from frontend)
    print("\nTesting filtering with '2026-01-15' (Frontend Format)...")
    filter_date = "2026-01-15"
    
    # Get metrics with filter
    metrics = processor.calculate_metrics(filter_date=filter_date)
    summary = metrics['crew_schedule']['summary']
    
    print(f"Summary returned: {summary}")
    
    # We expect SL=1, CSL=1, SBY=1, OSBY=1 (from the daily data)
    # If filtering failed, it would return the global summary (which is also 1,1,1,1 here since we only loaded one day).
    # To be sure filtering works, let's ADD another day's data so global != daily.
    
    print("\nAdding second day data...")
    csv_content_2 = """Crew Schedule Report
Report Date: 16 Jan 2026
ID,Name,Base,Rank,SL,CSL,SBY,OSBY
1005,Pilot E,SGN,CP,1,0,0,0
""".encode('utf-8')
    processor.process_crew_schedule_csv(file_content=csv_content_2, sync_db=False)
    
    print(f"Global Summary: {processor.crew_schedule['summary']}")
    # Now global SL should be 2.
    
    # Filter for 15th again
    metrics_15 = processor.calculate_metrics(filter_date="2026-01-15")
    summary_15 = metrics_15['crew_schedule']['summary']
    print(f"Summary for 2026-01-15: {summary_15}")
    
    if summary_15['SL'] == 1:
        print("SUCCESS: Filter correctly returned specific day's data (SL=1) instead of global (SL=2).")
    else:
        print(f"FAILURE: Expected SL=1, got {summary_15['SL']}. Filtering failed.")

if __name__ == "__main__":
    main()
