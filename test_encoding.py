
import csv
import io
from data_processor import DataProcessor

def test_encoding_fix():
    print("Testing Encoding Fix...")
    processor = DataProcessor()
    
    # simulate content with special characters in CP1252
    # "Séniority" has an accent
    csv_content = """
Rolling Crew Hours Totals Report
as of 15/01/2026
ID,Name,Séniority,Last,Last
,,,28-Day(s),12-Month(s)
,,,Block Time,Block Time
1234,TEST PILOT,0,50:00,500:00
""".strip()
    
    # Encode as CP1252
    encoded_content = csv_content.encode('cp1252')
    
    print(f"Encoded content length: {len(encoded_content)}")
    print(f"Encoded content (hex): {encoded_content.hex()}")
    
    # Process
    count = processor.process_rolcrtot_csv(file_content=encoded_content, sync_db=False)
    
    print(f"Processed records: {count}")
    
    if count == 1:
        print("SUCCESS: Parsed CP1252 file correctly")
        pilot = processor.rolling_hours[0]
        print(f"Pilot Name: {pilot['name']}")
        print(f"28-Day Hours: {pilot['block_28day']}")
    else:
        print("FAILURE: Could not parse file")

if __name__ == "__main__":
    test_encoding_fix()
