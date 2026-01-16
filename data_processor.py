"""
Data Processor Module for Crew Dashboard
Handles CSV parsing and KPI calculations
"""

import csv
import re
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

class DataProcessor:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else Path(".")
        self.flights = []
        self.crew_to_regs = defaultdict(set)
        self.crew_roles = {}
        self.reg_flight_hours = defaultdict(float)
        self.reg_flight_count = defaultdict(int)
        self.ac_utilization = {}
        # New data structures for Rolling hours and Crew schedule
        self.rolling_hours = []  # Rolling 28-day/365-day block hours
        self.crew_schedule = {   # Standby, sick-call, fatigue status
            'standby': [],
            'sick_call': [],
            'fatigue': [],
            'office_standby': [],
            'summary': {'SL': 0, 'CSL': 0, 'SBY': 0, 'OSBY': 0}
        }
        
    def parse_time(self, time_str):
        """Parse time string HH:MM to minutes"""
        if not time_str or ':' not in time_str:
            return None
        try:
            parts = time_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return None
    
    def extract_crew_ids(self, crew_string):
        """Extract crew IDs from crew string like '-NAME(ROLE) ID'"""
        pattern = r'\(([A-Z]{2})\)\s*(\d+)'
        matches = re.findall(pattern, crew_string)
        return [(role, id) for role, id in matches]
    
    def process_dayrep_csv(self, file_path=None, file_content=None):
        """Process DayRepReport CSV file"""
        self.flights = []
        self.crew_to_regs = defaultdict(set)
        self.crew_roles = {}
        self.reg_flight_hours = defaultdict(float)
        self.reg_flight_count = defaultdict(int)
        
        lines = []
        if file_content:
            lines = file_content.decode('utf-8').split('\n')
            reader = csv.reader(lines)
        else:
            file_path = file_path or self.data_dir / 'DayRepReport15Jan2026.csv'
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                lines = list(reader)
            reader = iter(lines)
        
        for row in reader:
            if len(row) >= 15 and row[0] and ('15/01' in row[0] or '16/01' in row[0]):
                if row[1]:  # Has REG
                    flight = {
                        'date': row[0],
                        'reg': row[1],
                        'flt': row[2],
                        'dep': row[3],
                        'arr': row[4],
                        'std': row[5],
                        'sta': row[6],
                        'crew': row[14] if len(row) > 14 else ''
                    }
                    self.flights.append(flight)
                    
                    # Calculate flight hours
                    std = self.parse_time(row[5])
                    sta = self.parse_time(row[6])
                    if std is not None and sta is not None:
                        duration = sta - std
                        if duration < 0:
                            duration += 24 * 60
                        self.reg_flight_hours[row[1]] += duration / 60
                        self.reg_flight_count[row[1]] += 1
                    
                    # Extract crew
                    crew_list = self.extract_crew_ids(flight['crew'])
                    for role, crew_id in crew_list:
                        self.crew_to_regs[crew_id].add(row[1])
                        self.crew_roles[crew_id] = role
        
        return len(self.flights)
    
    def process_sacutil_csv(self, file_path=None, file_content=None):
        """Process SacutilReport CSV file"""
        self.ac_utilization = {}
        
        if file_content:
            content = file_content.decode('utf-8')
        else:
            file_path = file_path or self.data_dir / 'SacutilReport1.csv'
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        lines = content.split('\n')
        for line in lines:
            parts = line.strip().split(',')
            # Check if this is a data row (has date pattern like DD.MM or DD/MM)
            if len(parts) >= 12:
                first_col = parts[0].strip()
                # Accept any date pattern or if second column looks like aircraft type
                is_date = '.' in first_col or '/' in first_col
                is_ac_type = parts[1].strip() in ['A320', 'A321', 'A330', 'B737', 'E190']
                
                if is_date or is_ac_type:
                    ac_type = parts[1].strip()
                    if ac_type and ac_type not in ['', 'ACTYPE', 'Aircraft']:
                        self.ac_utilization[ac_type] = {
                            'dom_block': parts[2].strip() if len(parts) > 2 else '',
                            'int_block': parts[3].strip() if len(parts) > 3 else '',
                            'total_block': parts[4].strip() if len(parts) > 4 else '',
                            'dom_cycles': parts[5].strip() if len(parts) > 5 else '',
                            'int_cycles': parts[6].strip() if len(parts) > 6 else '',
                            'total_cycles': parts[7].strip() if len(parts) > 7 else '',
                            'avg_util': parts[11].strip() if len(parts) > 11 else ''
                        }
        
        return len(self.ac_utilization)
    
    def process_rolcrtot_csv(self, file_path=None, file_content=None):
        """Process RolCrTotReport CSV file - Rolling crew hours totals"""
        self.rolling_hours = []
        
        if file_content:
            content = file_content.decode('utf-8')
        else:
            file_path = file_path or self.data_dir / 'RolCrTotReport.csv'
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                return 0
        
        lines = content.split('\n')
        for line in lines:
            parts = line.strip().split(',')
            # Skip header lines and empty lines
            if len(parts) >= 5 and parts[0].isdigit():
                crew_id = parts[0]
                name = parts[1]
                seniority = parts[2]
                block_28day = parts[3] if len(parts) > 3 else '0:00'
                block_12month = parts[4] if len(parts) > 4 else '0:00'
                
                # Parse hours from HH:MM format
                def parse_hours(time_str):
                    try:
                        if ':' in time_str:
                            h, m = time_str.split(':')
                            return float(h) + float(m) / 60
                        return 0.0
                    except:
                        return 0.0
                
                hours_28day = parse_hours(block_28day)
                hours_12month = parse_hours(block_12month)
                
                # Determine status based on 28-day limit (100 hours)
                percentage = (hours_28day / 100) * 100
                if percentage >= 95:
                    status = 'critical'
                elif percentage >= 85:
                    status = 'warning'
                else:
                    status = 'normal'
                
                self.rolling_hours.append({
                    'id': crew_id,
                    'name': name,
                    'seniority': seniority,
                    'block_28day': block_28day,
                    'block_12month': block_12month,
                    'hours_28day': round(hours_28day, 2),
                    'hours_12month': round(hours_12month, 2),
                    'percentage': round(percentage, 1),
                    'status': status
                })
        
        # Sort by 28-day hours descending
        self.rolling_hours.sort(key=lambda x: x['hours_28day'], reverse=True)
        return len(self.rolling_hours)
    
    def process_crew_schedule_csv(self, file_path=None, file_content=None):
        """Process Crew schedule CSV file - Standby, sick-call, fatigue status"""
        self.crew_schedule = {
            'standby': [],
            'sick_call': [],
            'fatigue': [],
            'office_standby': [],
            'summary': {'SL': 0, 'CSL': 0, 'SBY': 0, 'OSBY': 0}
        }
        
        if file_content:
            content = file_content.decode('utf-8')
        else:
            file_path = file_path or self.data_dir / 'Crew schedule 15Jan(standby,callsick, fatigue).csv'
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                return 0
        
        lines = content.split('\n')
        for line in lines:
            parts = line.strip().split(',')
            # Skip header lines and empty lines
            if len(parts) >= 9 and parts[0].isdigit():
                crew_data = {
                    'index': parts[0],
                    'id': parts[1],
                    'name': parts[2],
                    'base_ac_pos': parts[3],
                    'totals': parts[4]
                }
                
                # Extract base and position
                base_info = parts[3].split() if parts[3] else []
                crew_data['base'] = base_info[0] if len(base_info) > 0 else ''
                crew_data['aircraft'] = base_info[1] if len(base_info) > 1 else ''
                crew_data['position'] = base_info[2] if len(base_info) > 2 else ''
                
                # Check status columns: SL(5), CSL(6), SBY(7), OSBY(8)
                sl = parts[5].strip() if len(parts) > 5 else ''
                csl = parts[6].strip() if len(parts) > 6 else ''
                sby = parts[7].strip() if len(parts) > 7 else ''
                osby = parts[8].strip() if len(parts) > 8 else ''
                
                if sl == '1':
                    crew_data['status'] = 'Sick Leave'
                    self.crew_schedule['sick_call'].append(crew_data)
                    self.crew_schedule['summary']['SL'] += 1
                elif csl == '1':
                    crew_data['status'] = 'Call Sick Leave'
                    self.crew_schedule['fatigue'].append(crew_data)
                    self.crew_schedule['summary']['CSL'] += 1
                elif sby == '1':
                    crew_data['status'] = 'Standby'
                    self.crew_schedule['standby'].append(crew_data)
                    self.crew_schedule['summary']['SBY'] += 1
                elif osby == '1':
                    crew_data['status'] = 'Office Standby'
                    self.crew_schedule['office_standby'].append(crew_data)
                    self.crew_schedule['summary']['OSBY'] += 1
        
        return sum([len(v) for k, v in self.crew_schedule.items() if isinstance(v, list)])

    
    def calculate_metrics(self):
        """Calculate all dashboard KPIs"""
        unique_regs = set(f['reg'] for f in self.flights if f['reg'])
        total_flights = len(self.flights)
        total_crew = len(self.crew_to_regs)
        
        # Average flight hours per aircraft
        avg_flight_hours = 0
        if self.reg_flight_hours:
            avg_flight_hours = sum(self.reg_flight_hours.values()) / len(self.reg_flight_hours)
        
        # Multi-REG crew
        multi_reg_crew = {cid: list(regs) for cid, regs in self.crew_to_regs.items() if len(regs) >= 2}
        
        # Role counts
        role_counts = defaultdict(int)
        for crew_id, role in self.crew_roles.items():
            role_counts[role] += 1
        
        # Aircraft details
        aircraft_data = []
        for reg in sorted(self.reg_flight_hours.keys()):
            hours = self.reg_flight_hours[reg]
            count = self.reg_flight_count[reg]
            aircraft_data.append({
                'reg': reg,
                'total_hours': round(hours, 1),
                'flights': count,
                'avg_per_flight': round(hours / count, 1) if count > 0 else 0
            })
        
        # Multi-REG details (top 20)
        multi_reg_details = []
        for cid, regs in sorted(multi_reg_crew.items(), key=lambda x: -len(x[1]))[:20]:
            multi_reg_details.append({
                'id': cid,
                'role': self.crew_roles.get(cid, 'UNK'),
                'regs': sorted(regs)
            })
        
        # Calculate rolling hours statistics
        rolling_stats = {'normal': 0, 'warning': 0, 'critical': 0}
        for crew in self.rolling_hours:
            rolling_stats[crew['status']] += 1
        
        return {
            'summary': {
                'total_aircraft': len(unique_regs),
                'total_flights': total_flights,
                'total_crew': total_crew,
                'multi_reg_count': len(multi_reg_crew),
                'avg_flight_hours': round(avg_flight_hours, 1)
            },
            'crew_roles': dict(role_counts),
            'aircraft': aircraft_data,
            'multi_reg_crew': multi_reg_details,
            'utilization': self.ac_utilization,
            'rolling_hours': self.rolling_hours[:50],  # Top 50
            'rolling_stats': rolling_stats,
            'crew_schedule': self.crew_schedule,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_dashboard_data(self):
        """Get all data for dashboard"""
        return self.calculate_metrics()
    
    def export_to_json(self, output_file='dashboard_data.json'):
        """Export data to JSON file"""
        data = self.calculate_metrics()
        output_path = self.data_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(output_path)


# Singleton instance for the API
_processor = None

def get_processor():
    global _processor
    if _processor is None:
        _processor = DataProcessor(Path(__file__).parent)
        # Load default data
        try:
            _processor.process_dayrep_csv()
            _processor.process_sacutil_csv()
            _processor.process_rolcrtot_csv()
            _processor.process_crew_schedule_csv()
        except Exception as e:
            print(f"Warning: Could not load default data: {e}")
    return _processor

def refresh_data():
    """Refresh data from default CSV files"""
    processor = get_processor()
    processor.process_dayrep_csv()
    processor.process_sacutil_csv()
    processor.process_rolcrtot_csv()
    processor.process_crew_schedule_csv()
    return processor.get_dashboard_data()


if __name__ == '__main__':
    # Test the processor
    processor = DataProcessor()
    print("Processing DayRepReport...")
    flights = processor.process_dayrep_csv('DayRepReport15Jan2026.csv')
    print(f"Loaded {flights} flights")
    
    print("\nProcessing SacutilReport...")
    utils = processor.process_sacutil_csv('SacutilReport1.csv')
    print(f"Loaded {utils} aircraft utilization records")
    
    print("\nCalculating metrics...")
    metrics = processor.calculate_metrics()
    print(json.dumps(metrics['summary'], indent=2))
    
    print("\nExporting to JSON...")
    output = processor.export_to_json()
    print(f"Exported to: {output}")
