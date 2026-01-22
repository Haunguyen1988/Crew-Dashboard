
import sys
import os
import traceback
import json
from data_processor import DataProcessor

def debug_upload():
    print("Initializing DataProcessor...")
    processor = DataProcessor()
    
    # Files to test
    rol_file = "RolCrTotReport.csv"
    crew_file = "Crew schedule 15Jan(standby,callsick, fatigue).csv"
    
    # 1. Test RolCrTotReport
    print(f"\n===== TESTING {rol_file} =====")
    if os.path.exists(rol_file):
        try:
            with open(rol_file, 'rb') as f:
                content = f.read()
            
            print(f"File size: {len(content)} bytes")
            # Decode manually to check
            text = processor._decode_content(content)
            print(f"Decoded length: {len(text)} chars")
            print(f"First 3 lines:\n{text.splitlines()[:3]}")
            
            # Run Process
            print("Run process_rolcrtot_csv...")
            count = processor.process_rolcrtot_csv(file_content=content, sync_db=False)
            print(f"Result count: {count}")
            
            if processor.rolling_hours:
                print("First Entry Sample:")
                print(json.dumps(processor.rolling_hours[0], indent=2))
                
                # Check for bad values
                failures = [x for x in processor.rolling_hours if x['percentage'] == 0 and x['hours_28day'] > 0]
                if failures:
                    print(f"WARNING: {len(failures)} entries have 0% but >0 hours!")
            else:
                print("ERROR: No entries parsed!")
                
        except Exception as e:
            print(f"CRASH: {e}")
            traceback.print_exc()
    else:
        print("File not found.")

    # 2. Test Crew Schedule
    print(f"\n===== TESTING {crew_file} =====")
    if os.path.exists(crew_file):
        try:
            with open(crew_file, 'rb') as f:
                content = f.read()
            
            print(f"File size: {len(content)} bytes")
            text = processor._decode_content(content)
            lines = text.splitlines()
            print(f"First 10 lines (for date detection):")
            for i, line in enumerate(lines[:10]):
                print(f"{i}: {line}")
                
            # Run Process
            print("Run process_crew_schedule_csv...")
            summary_count = processor.process_crew_schedule_csv(file_path=os.path.basename(crew_file), file_content=content, sync_db=False)
            print(f"Summary Count: {summary_count}")
            print(f"Summary Dict: {processor.crew_schedule['summary']}")
            print(f"By Date Dict: {processor.crew_schedule_by_date}")
            
            if not processor.crew_schedule_by_date:
                print("WARNING: No 'by_date' entries found! Filtering will fail.")
                
        except Exception as e:
            print(f"CRASH: {e}")
            traceback.print_exc()
    else:
        print("File not found.")

if __name__ == "__main__":
    debug_upload()
