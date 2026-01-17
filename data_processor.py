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
        self.flights_by_date = defaultdict(list)  # Store flights grouped by date
        self.available_dates = []  # List of available dates
        self.current_filter_date = None  # Current date filter (None = all dates)
        self.crew_to_regs = defaultdict(set)
        self.crew_to_regs_by_date = defaultdict(lambda: defaultdict(set))  # Crew regs by date
        self.crew_roles = {}
        self.reg_flight_hours = defaultdict(float)
        self.reg_flight_hours_by_date = defaultdict(lambda: defaultdict(float))  # By date
        self.reg_flight_count = defaultdict(int)
        self.reg_flight_count_by_date = defaultdict(lambda: defaultdict(int))  # By date
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
        """Parse time string HH:MM to minutes from midnight"""
        if not time_str or ':' not in time_str:
            return None
        try:
            parts = time_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return None
    
    def get_operating_date(self, calendar_date, time_str):
        """
        Determine operating date based on flight departure time.
        Operating day: 04:00 to 03:59 next day
        - Flights departing 04:00-23:59 belong to that calendar date
        - Flights departing 00:00-03:59 belong to previous calendar date
        """
        if not time_str:
            return calendar_date
        
        time_minutes = self.parse_time(time_str)
        if time_minutes is None:
            return calendar_date
        
        # If departure time is 00:00-03:59 (0-239 minutes), it belongs to previous day
        if time_minutes < 240:  # 04:00 = 240 minutes
            # Adjust to previous day
            try:
                parts = calendar_date.split('/')
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2]) + 2000 if int(parts[2]) < 100 else int(parts[2])
                
                from datetime import date, timedelta
                current_date = date(year, month, day)
                prev_date = current_date - timedelta(days=1)
                
                return f"{prev_date.day:02d}/{prev_date.month:02d}/{str(prev_date.year)[-2:]}"
            except:
                return calendar_date
        
        return calendar_date
    
    def extract_crew_ids(self, crew_string):
        """Extract crew IDs from crew string like '-NAME(ROLE) ID'"""
        pattern = r'\(([A-Z]{2})\)\s*(\d+)'
        matches = re.findall(pattern, crew_string)
        return [(role, id) for role, id in matches]
    
    def get_crew_set_key(self, crew_string):
        """Get a unique key for a crew set (sorted crew IDs)"""
        crew_list = self.extract_crew_ids(crew_string)
        crew_ids = sorted([cid for _, cid in crew_list])
        return tuple(crew_ids)
    
    def normalize_date(self, date_str):
        """Normalize date string to DD/MM/YY format"""
        if not date_str:
            return None
        # Remove leading/trailing spaces
        date_str = date_str.strip()
        # Handle format like "15/01/26" or "15/01"
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) >= 2:
                day = parts[0].zfill(2)
                month = parts[1].zfill(2)
                year = parts[2] if len(parts) > 2 else '26'
                return f"{day}/{month}/{year}"
        return date_str
    
    def process_dayrep_csv(self, file_path=None, file_content=None):
        """Process DayRepReport CSV file with operating day logic (04:00-03:59)"""
        self.flights = []
        self.flights_by_date = defaultdict(list)
        self.available_dates = []
        self.crew_to_regs = defaultdict(set)
        self.crew_to_regs_by_date = defaultdict(lambda: defaultdict(set))
        self.crew_roles = {}
        self.reg_flight_hours = defaultdict(float)
        self.reg_flight_hours_by_date = defaultdict(lambda: defaultdict(float))
        self.reg_flight_count = defaultdict(int)
        self.reg_flight_count_by_date = defaultdict(lambda: defaultdict(int))
        
        # New: Track crew rotations at group level
        self.crew_group_rotations = defaultdict(list)  # crew_set -> list of REGs
        self.crew_group_rotations_by_date = defaultdict(lambda: defaultdict(list))
        
        unique_dates = set()
        
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
            # Check for date patterns - more flexible matching
            if len(row) >= 15 and row[0]:
                date_str = row[0].strip()
                # Check if first column looks like a date (contains / and digits)
                if '/' in date_str and any(c.isdigit() for c in date_str):
                    if row[1]:  # Has REG
                        calendar_date = self.normalize_date(date_str)
                        std_time = row[5].strip() if row[5] else ''
                        
                        # Apply operating day logic (04:00-03:59)
                        operating_date = self.get_operating_date(calendar_date, std_time)
                        unique_dates.add(operating_date)
                        
                        crew_string = row[14] if len(row) > 14 else ''
                        
                        flight = {
                            'date': operating_date,
                            'calendar_date': calendar_date,
                            'reg': row[1],
                            'flt': row[2],
                            'dep': row[3],
                            'arr': row[4],
                            'std': std_time,
                            'sta': row[6],
                            'crew': crew_string
                        }
                        self.flights.append(flight)
                        self.flights_by_date[operating_date].append(flight)
                        
                        # Calculate flight hours (both total and by date)
                        std = self.parse_time(std_time)
                        sta = self.parse_time(row[6])
                        if std is not None and sta is not None:
                            duration = sta - std
                            if duration < 0:
                                duration += 24 * 60
                            hours = duration / 60
                            self.reg_flight_hours[row[1]] += hours
                            self.reg_flight_count[row[1]] += 1
                            self.reg_flight_hours_by_date[operating_date][row[1]] += hours
                            self.reg_flight_count_by_date[operating_date][row[1]] += 1
                        
                        # Extract crew (both total and by date)
                        crew_list = self.extract_crew_ids(crew_string)
                        for role, crew_id in crew_list:
                            self.crew_to_regs[crew_id].add(row[1])
                            self.crew_to_regs_by_date[operating_date][crew_id].add(row[1])
                            self.crew_roles[crew_id] = role
                        
                        # Track crew group rotations
                        if crew_list:
                            crew_set_key = self.get_crew_set_key(crew_string)
                            if crew_set_key:
                                self.crew_group_rotations[crew_set_key].append(row[1])
                                self.crew_group_rotations_by_date[operating_date][crew_set_key].append(row[1])
        
        # Sort dates chronologically
        self.available_dates = sorted(list(unique_dates), key=lambda d: self._parse_date_for_sort(d))
        
        return len(self.flights)
    
    def _parse_date_for_sort(self, date_str):
        """Parse date string for sorting purposes"""
        try:
            parts = date_str.split('/')
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) + 2000 if int(parts[2]) < 100 else int(parts[2])
            return (year, month, day)
        except:
            return (9999, 99, 99)
    
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

    
    def calculate_metrics(self, filter_date=None):
        """Calculate all dashboard KPIs, optionally filtered by date"""
        # Determine which data to use based on filter
        if filter_date and filter_date in self.flights_by_date:
            flights = self.flights_by_date[filter_date]
            crew_to_regs = self.crew_to_regs_by_date[filter_date]
            reg_flight_hours = self.reg_flight_hours_by_date[filter_date]
            reg_flight_count = self.reg_flight_count_by_date[filter_date]
            crew_group_rotations = self.crew_group_rotations_by_date[filter_date]
        else:
            flights = self.flights
            crew_to_regs = self.crew_to_regs
            reg_flight_hours = self.reg_flight_hours
            reg_flight_count = self.reg_flight_count
            crew_group_rotations = self.crew_group_rotations
        
        unique_regs = set(f['reg'] for f in flights if f['reg'])
        total_flights = len(flights)
        total_crew = len(crew_to_regs)
        
        # Average flight hours per aircraft
        avg_flight_hours = 0
        if reg_flight_hours:
            avg_flight_hours = sum(reg_flight_hours.values()) / len(reg_flight_hours)
        
        # Calculate Crew Rotations (group-based)
        # A rotation is when a crew GROUP flies on multiple different aircraft
        # Count rotations as: (number of unique REGs - 1) for each group that has 2+ REGs
        rotation_count = 0
        rotation_details = []
        
        for crew_set_key, regs_list in crew_group_rotations.items():
            unique_regs_for_group = list(set(regs_list))
            if len(unique_regs_for_group) >= 2:
                # This group had a rotation (changed aircraft)
                rotation_count += 1  # Count as 1 rotation event per group
                
                # Get role info from first crew member
                if crew_set_key and len(crew_set_key) > 0:
                    first_crew_id = crew_set_key[0]
                    role = self.crew_roles.get(first_crew_id, 'UNK')
                    
                    rotation_details.append({
                        'crew_ids': list(crew_set_key),
                        'crew_count': len(crew_set_key),
                        'role': role,
                        'regs': sorted(unique_regs_for_group),
                        'rotations': len(unique_regs_for_group) - 1
                    })
        
        # Sort rotation details by number of rotations (descending)
        rotation_details.sort(key=lambda x: (-x['rotations'], -x['crew_count']))
        
        # Role counts (recalculate based on filtered data)
        role_counts = defaultdict(int)
        counted_crew = set()
        for f in flights:
            crew_list = self.extract_crew_ids(f.get('crew', ''))
            for role, crew_id in crew_list:
                if crew_id not in counted_crew:
                    role_counts[role] += 1
                    counted_crew.add(crew_id)
        
        # Aircraft details
        aircraft_data = []
        for reg in sorted(reg_flight_hours.keys()):
            hours = reg_flight_hours[reg]
            count = reg_flight_count[reg]
            aircraft_data.append({
                'reg': reg,
                'total_hours': round(hours, 1),
                'flights': count,
                'avg_per_flight': round(hours / count, 1) if count > 0 else 0
            })
        
        # Calculate rolling hours statistics
        rolling_stats = {'normal': 0, 'warning': 0, 'critical': 0}
        for crew in self.rolling_hours:
            rolling_stats[crew['status']] += 1
        
        return {
            'summary': {
                'total_aircraft': len(set(f['reg'] for f in flights if f['reg'])),
                'total_flights': total_flights,
                'total_crew': total_crew,
                'crew_rotation_count': rotation_count,  # Renamed from multi_reg_count
                'avg_flight_hours': round(avg_flight_hours, 1)
            },
            'available_dates': self.available_dates,
            'current_filter_date': filter_date,
            'crew_roles': dict(role_counts),
            'aircraft': aircraft_data,
            'crew_rotations': rotation_details[:20],  # Top 20 rotation groups
            'utilization': self.ac_utilization,
            'rolling_hours': self.rolling_hours[:50],  # Top 50
            'rolling_stats': rolling_stats,
            'crew_schedule': self.crew_schedule,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_dashboard_data(self, filter_date=None):
        """Get all data for dashboard, optionally filtered by date"""
        return self.calculate_metrics(filter_date)
    
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
