
import sys
import os
from unittest.mock import MagicMock
from data_processor import DataProcessor

def test_logic():
    print("Initializing DataProcessor...")
    processor = DataProcessor()
    
    # Mock DB Data (Simulate what db.get_rolling_hours() returns)
    # 2 records: 1 critical, 1 normal
    mock_db_data = [
        {
            'id': '1001', 'name': 'Pilot A', 'block_28day': '99:00', 
            'hours_28day': 99.0, 'status': 'critical',
            'block_12month': '500:00', 'hours_12month': 500.0, 'status_12m': 'normal'
        },
        {
            'id': '1002', 'name': 'Pilot B', 'block_28day': '10:00', 
            'hours_28day': 10.0, 'status': 'normal',
            'block_12month': '100:00', 'hours_12month': 100.0, 'status_12m': 'normal'
        }
    ]
    
    print(f"Simulating DB Fetch: {len(mock_db_data)} records loaded.")
    
    # 1. Populate Processor (The Fix Logic)
    processor.rolling_hours = []
    for item in mock_db_data:
        processor.rolling_hours.append(item)
        
    print(f"Processor State: {len(processor.rolling_hours)} rolling records.")
    
    # 2. Calculate Metrics
    print("Calculating Metrics...")
    metrics = processor.calculate_metrics()
    
    # 3. Verify Stats
    stats = metrics['rolling_stats']
    print(f"Calculated Stats: {stats}")
    
    expected_critical = 1
    expected_normal = 1
    
    if stats['critical'] == expected_critical and stats['normal'] == expected_normal:
        print("SUCCESS: Stats calculation correctly counts statuses from populated data.")
    else:
        print(f"FAILURE: Stats mismatch. Expected Crit={expected_critical}, Norm={expected_normal}. Got {stats}")

if __name__ == "__main__":
    test_logic()
