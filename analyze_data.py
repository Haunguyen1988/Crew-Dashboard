import csv
import re
from collections import defaultdict
from datetime import datetime

# Read flight data
flights = []
with open('DayRepReport15Jan2026.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 15 and row[0] and (row[0].startswith('15/01') or row[0].startswith('16/01')):
            if row[1]:  # Has REG
                flights.append({
                    'date': row[0],
                    'reg': row[1],
                    'flt': row[2],
                    'dep': row[3],
                    'arr': row[4],
                    'std': row[5],  # Scheduled Time Departure
                    'sta': row[6],  # Scheduled Time Arrival
                    'crew': row[14] if len(row) > 14 else ''
                })

# 1. Count unique aircraft registrations and calculate average flight hours
unique_regs = set(f['reg'] for f in flights if f['reg'])
total_flights = len(flights)

# Calculate flight hours per aircraft (REG)
def parse_time(time_str):
    """Parse time string HH:MM to minutes"""
    if not time_str or ':' not in time_str:
        return None
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return None

reg_flight_hours = defaultdict(float)
reg_flight_count = defaultdict(int)

for flight in flights:
    reg = flight['reg']
    std = parse_time(flight['std'])
    sta = parse_time(flight['sta'])
    
    if std is not None and sta is not None:
        # Calculate flight duration
        duration = sta - std
        if duration < 0:  # Flight crosses midnight
            duration += 24 * 60
        reg_flight_hours[reg] += duration / 60  # Convert to hours
        reg_flight_count[reg] += 1

print("=" * 60)
print("CREW MANAGEMENT DASHBOARD - DATA ANALYSIS")
print("Date: 15/01/2026")
print("=" * 60)

# 1. AIRCRAFT METRICS
print(f"\n{'='*60}")
print("1. AIRCRAFT METRICS")
print("=" * 60)
print(f"Total Aircraft Flying Today: {len(unique_regs)}")
print(f"Total Flights Today: {total_flights}")

# Calculate average flight hours per aircraft
if reg_flight_hours:
    avg_flight_hours_overall = sum(reg_flight_hours.values()) / len(reg_flight_hours)
    print(f"Average Flight Hours per Aircraft: {avg_flight_hours_overall:.1f}h")
    
    print("\nFlight Hours by Aircraft Registration:")
    for reg in sorted(reg_flight_hours.keys()):
        hours = reg_flight_hours[reg]
        count = reg_flight_count[reg]
        avg = hours / count if count > 0 else 0
        print(f"  {reg}: {hours:.1f}h ({count} flights, avg {avg:.1f}h/flight)")

# 2. Parse crew members and their assignments
def extract_crew_ids(crew_string):
    """Extract crew IDs from crew string like '-NAME(ROLE) ID'"""
    crew_ids = []
    # Match pattern like (CP) 7531 or (FO) 7440
    pattern = r'\(([A-Z]{2})\)\s*(\d+)'
    matches = re.findall(pattern, crew_string)
    return [(role, id) for role, id in matches]

# Track crew to REG mapping
crew_to_regs = defaultdict(set)
crew_roles = {}

for flight in flights:
    reg = flight['reg']
    crew_list = extract_crew_ids(flight['crew'])
    for role, crew_id in crew_list:
        crew_to_regs[crew_id].add(reg)
        crew_roles[crew_id] = role

# 2. CREW METRICS
print(f"\n{'='*60}")
print("2. CREW METRICS")
print("=" * 60)
print(f"Total Crew Operating Today: {len(crew_to_regs)}")

# Count by role
role_counts = defaultdict(int)
for crew_id, role in crew_roles.items():
    role_counts[role] += 1

print("\nCrew by Role:")
for role in sorted(role_counts.keys()):
    print(f"  {role}: {role_counts[role]}")

# 3. MULTI-REG ROTATION (Crew jumping between 2+ aircraft registrations)
print(f"\n{'='*60}")
print("3. MULTI-REG ROTATION (Crew flying on 2+ REGs)")
print("=" * 60)

multi_reg_crew = {cid: regs for cid, regs in crew_to_regs.items() if len(regs) >= 2}
print(f"Crew with 2+ aircraft registrations: {len(multi_reg_crew)}")

if multi_reg_crew:
    print("\nDetails:")
    for cid, regs in sorted(multi_reg_crew.items(), key=lambda x: -len(x[1])):
        role = crew_roles.get(cid, 'UNK')
        print(f"  ID {cid} ({role}): {len(regs)} REGs -> {sorted(regs)}")

# 4. AIRCRAFT UTILIZATION from SacutilReport
print(f"\n{'='*60}")
print("4. AIRCRAFT UTILIZATION (from SacutilReport)")
print("=" * 60)

ac_utilization = {}
with open('SacutilReport1.csv', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')
    for line in lines:
        if '15.01' in line:
            parts = line.split(',')
            if len(parts) >= 12:
                ac_type = parts[1]
                dom_block = parts[2]
                int_block = parts[3]
                total_block = parts[4]
                avg_util = parts[11] if len(parts) > 11 else ''
                ac_utilization[ac_type] = {
                    'dom': dom_block,
                    'int': int_block,
                    'total': total_block,
                    'avg': avg_util
                }
                print(f"  {ac_type}: Dom={dom_block}, Int={int_block}, Total={total_block}, Avg={avg_util}")

# 5. SUMMARY FOR DASHBOARD
print("\n" + "=" * 60)
print("SUMMARY FOR DASHBOARD")
print("=" * 60)
print(f"Total Aircraft (REGs): {len(unique_regs)}")
print(f"Total Flights: {total_flights}")
print(f"Total Crew Operating: {len(crew_to_regs)}")
print(f"Multi-REG Rotations: {len(multi_reg_crew)}")

# Calculate role summary
cp_count = role_counts.get('CP', 0)
fo_count = role_counts.get('FO', 0)
pu_count = role_counts.get('PU', 0)
fa_count = role_counts.get('FA', 0)
tv_count = role_counts.get('TV', 0)

print(f"\nCrew Role Distribution:")
print(f"  Captains (CP): {cp_count}")
print(f"  First Officers (FO): {fo_count}")
print(f"  Pursers (PU): {pu_count}")
print(f"  Flight Attendants (FA): {fa_count}")
if tv_count > 0:
    print(f"  Technicians (TV): {tv_count}")

# Export data for dashboard
dashboard_data = {
    'total_aircraft': len(unique_regs),
    'total_flights': total_flights,
    'total_crew': len(crew_to_regs),
    'multi_reg_crew': len(multi_reg_crew),
    'avg_flight_hours': avg_flight_hours_overall if reg_flight_hours else 0,
    'crew_roles': dict(role_counts),
    'multi_reg_details': [
        {
            'id': cid,
            'role': crew_roles.get(cid, 'UNK'),
            'regs': sorted(regs)
        }
        for cid, regs in sorted(multi_reg_crew.items(), key=lambda x: -len(x[1]))[:20]
    ]
}

print(f"\n--- Dashboard Data ---")
print(f"Total Aircraft: {dashboard_data['total_aircraft']}")
print(f"Total Flights: {dashboard_data['total_flights']}")
print(f"Total Crew: {dashboard_data['total_crew']}")
print(f"Multi-REG Crew: {dashboard_data['multi_reg_crew']}")
print(f"Avg Flight Hours/Aircraft: {dashboard_data['avg_flight_hours']:.1f}h")
