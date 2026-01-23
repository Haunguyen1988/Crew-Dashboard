
from data_processor import DataProcessor
import os

def test_parser():
    processor = DataProcessor()
    
    file_path = "RolCrTotReport.csv"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    print(f"Reading {file_path}...")
    with open(file_path, 'rb') as f:
        content = f.read()

    # Pass sync_db=False to avoid messing with Supabase during debug
    count = processor.process_rolcrtot_csv(file_content=content, sync_db=False)
    
    print(f"Parsed {count} records.")
    
    if count > 0:
        print("First 3 records:")
        for item in processor.rolling_hours[:3]:
            print(item)
    else:
        print("Parsing failed (0 records).")

if __name__ == "__main__":
    test_parser()
