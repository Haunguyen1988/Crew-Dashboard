"""
Supabase Client Module for Crew Dashboard
Handles database operations for storing and retrieving CSV data
Works with both local development and Vercel deployment
"""

import os

# Try to load dotenv for local development, skip if not available (Vercel)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import supabase, handle gracefully if not available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

# Get environment variables - works on both local and Vercel
SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

supabase: Client = None
_init_error = None

def init_supabase():
    """Initialize Supabase client with proper error handling"""
    global supabase, _init_error
    
    if not SUPABASE_AVAILABLE:
        _init_error = "Supabase package not installed"
        return False
    
    if not SUPABASE_URL:
        _init_error = "SUPABASE_URL not configured"
        return False
    
    if not SUPABASE_KEY:
        _init_error = "SUPABASE_KEY not configured"
        return False
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        _init_error = None
        return True
    except Exception as e:
        _init_error = f"Failed to create Supabase client: {str(e)}"
        return False

def get_client() -> Client:
    """Get initialized Supabase client"""
    global supabase
    if supabase is None:
        init_supabase()
    return supabase

def is_connected():
    """Check if Supabase is properly configured and connected"""
    return get_client() is not None


# ==================== FLIGHTS TABLE ====================

def insert_flights(flights_data: list):
    """Insert flight records from DayRepReport CSV"""
    client = get_client()
    if not client:
        print(f"Supabase insert_flights failed: {_init_error}")
        return None
    
    try:
        # Clear existing data before insert
        # Check if we can delete (RLS might block)
        client.table('flights').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Insert new data in batches of 500
        batch_size = 500
        for i in range(0, len(flights_data), batch_size):
            batch = flights_data[i:i+batch_size]
            client.table('flights').insert(batch).execute()
        
        return len(flights_data)
    except Exception as e:
        print(f"Error inserting flights: {e}")
        return None

def _fetch_all(query):
    """Fetch all records using pagination to bypass 1000-row limit"""
    all_data = []
    limit = 1000
    start = 0
    
    while True:
        try:
            # Use range for pagination: start to start + limit - 1
            result = query.range(start, start + limit - 1).execute()
            data = result.data if result.data else []
            all_data.extend(data)
            
            # If we fetched fewer than limit, we're done
            if len(data) < limit:
                break
                
            start += limit
        except Exception as e:
            print(f"Error in pagination: {e}")
            break
            
    return all_data

def get_flights(filter_date: str = None):
    """Get flights, optionally filtered by date"""
    client = get_client()
    if not client:
        return []
    
    try:
        query = client.table('flights').select('*')
        if filter_date:
            query = query.eq('date', filter_date)
        
        # Use pagination helper
        return _fetch_all(query)
    except Exception as e:
        print(f"Error getting flights: {e}")
        return []

def get_available_dates():
    """Get list of unique dates from flights"""
    client = get_client()
    if not client:
        return []
    
    try:
        # Increase limit to check all dates
        query = client.table('flights').select('date')
        all_data = _fetch_all(query)
        
        if all_data:
            dates = list(set([r['date'] for r in all_data]))
            # Sort dates chronologically
            try:
                dates.sort(key=lambda d: tuple(map(int, d.split('/')[::-1])))
            except:
                dates.sort()
            return dates
        return []
    except Exception as e:
        print(f"Error getting available dates: {e}")
        return []


# ==================== AC UTILIZATION TABLE ====================

def insert_ac_utilization(util_data: list):
    """Insert AC utilization records from SacutilReport CSV"""
    client = get_client()
    if not client:
        return None
    
    try:
        # Clear existing data
        client.table('ac_utilization').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Insert new data
        batch_size = 500
        for i in range(0, len(util_data), batch_size):
            batch = util_data[i:i+batch_size]
            client.table('ac_utilization').insert(batch).execute()
        
        return len(util_data)
    except Exception as e:
        print(f"Error inserting AC utilization: {e}")
        return None

def get_ac_utilization(filter_date: str = None):
    """Get AC utilization, optionally filtered by date"""
    client = get_client()
    if not client:
        return []
    
    try:
        query = client.table('ac_utilization').select('*')
        if filter_date:
            query = query.eq('date', filter_date)
        
        return _fetch_all(query)
    except Exception as e:
        print(f"Error getting AC utilization: {e}")
        return []


# ==================== ROLLING HOURS TABLE ====================

def insert_rolling_hours(hours_data: list):
    """Insert rolling hours records from RolCrTotReport CSV"""
    client = get_client()
    if not client:
        return None
    
    try:
        # Clear existing data
        client.table('rolling_hours').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Insert new data
        batch_size = 500
        for i in range(0, len(hours_data), batch_size):
            batch = hours_data[i:i+batch_size]
            client.table('rolling_hours').insert(batch).execute()
        
        return len(hours_data)
    except Exception as e:
        print(f"Error inserting rolling hours: {e}")
        return None

def get_rolling_hours():
    """Get all rolling hours data"""
    client = get_client()
    if not client:
        return []
    
    try:
        query = client.table('rolling_hours').select('*').order('hours_28day', desc=True)
        return _fetch_all(query)
    except Exception as e:
        print(f"Error getting rolling hours: {e}")
        return []


# ==================== CREW SCHEDULE TABLE ====================

def insert_crew_schedule(schedule_data: list):
    """Insert crew schedule records from Crew Schedule CSV"""
    client = get_client()
    if not client:
        return None
    
    try:
        # Clear existing data
        client.table('crew_schedule').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Insert new data
        batch_size = 500
        for i in range(0, len(schedule_data), batch_size):
            batch = schedule_data[i:i+batch_size]
            client.table('crew_schedule').insert(batch).execute()
        
        return len(schedule_data)
    except Exception as e:
        print(f"Error inserting crew schedule: {e}")
        return None

def get_crew_schedule(filter_date: str = None):
    """Get crew schedule, optionally filtered by date"""
    client = get_client()
    if not client:
        return []
    
    try:
        query = client.table('crew_schedule').select('*')
        if filter_date:
            query = query.eq('date', filter_date)
        
        return _fetch_all(query)
    except Exception as e:
        print(f"Error getting crew schedule: {e}")
        return []

def get_crew_schedule_summary(filter_date: str = None):
    """Get summary counts of crew schedule statuses"""
    data = get_crew_schedule(filter_date)
    summary = {'SL': 0, 'CSL': 0, 'SBY': 0, 'OSBY': 0}
    for record in data:
        status = record.get('status_type', '')
        if status in summary:
            summary[status] += 1
    return summary


# ==================== STANDBY RECORDS TABLE ====================

def upsert_standby_records(records: list):
    """Upsert standby records from Crew Schedule CSV
    Uses crew_id + status_type + start_date as unique key
    """
    client = get_client()
    if not client or not records:
        return None
    
    try:
        # Clear existing data before insert for full refresh
        client.table('standby_records').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Insert in batches
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            client.table('standby_records').insert(batch).execute()
        
        return len(records)
    except Exception as e:
        print(f"Error upserting standby records: {e}")
        return None

def get_standby_records(filter_date: str = None):
    """Get standby records, filtered by date range
    
    Filter logic: filter_date >= start_date AND filter_date <= end_date
    This ensures multi-day duties appear for each day they cover
    """
    client = get_client()
    if not client:
        return []
    
    try:
        query = client.table('standby_records').select('*')
        
        if filter_date:
            # Filter: start_date <= filter_date AND end_date >= filter_date
            query = query.lte('start_date', filter_date).gte('end_date', filter_date)
        
        return _fetch_all(query)
    except Exception as e:
        print(f"Error getting standby records: {e}")
        return []

def get_standby_summary(filter_date: str = None):
    """Get summary counts of standby statuses filtered by date range"""
    data = get_standby_records(filter_date)
    summary = {'SL': 0, 'CSL': 0, 'SBY': 0, 'OSBY': 0}
    for record in data:
        status = record.get('status_type', '')
        if status in summary:
            summary[status] += 1
    return summary


# ==================== UTILITY FUNCTIONS ====================

def check_connection():
    """Check if Supabase connection is working"""
    global _init_error
    
    client = get_client()
    if not client:
        return False, _init_error or "Supabase credentials not configured"
    
    try:
        # Try to query flights table
        result = client.table('flights').select('id').limit(1).execute()
        return True, "Connected successfully"
    except Exception as e:
        return False, str(e)

def get_connection_status():
    """Get detailed connection status for debugging"""
    return {
        'supabase_available': SUPABASE_AVAILABLE,
        'url_configured': bool(SUPABASE_URL),
        'key_configured': bool(SUPABASE_KEY),
        'client_initialized': supabase is not None,
        'init_error': _init_error
    }

def clear_all_data():
    """Clear all data from all tables"""
    client = get_client()
    if not client:
        return False
    
    tables = ['flights', 'ac_utilization', 'rolling_hours', 'crew_schedule']
    for table in tables:
        try:
            client.table(table).delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
    return True


# ==================== AIMS STAGING TABLES ====================

def upsert_fact_actuals(records: list):
    """Upsert flight actuals from AIMS API"""
    client = get_client()
    if not client or not records:
        return None
    
    try:
        # Upsert with conflict on flight_date + flight_no
        result = client.table('fact_actuals').upsert(
            records,
            on_conflict='flight_date,flight_no'
        ).execute()
        return len(records)
    except Exception as e:
        print(f"Error upserting fact_actuals: {e}")
        # Try insert as fallback
        try:
            for i in range(0, len(records), 100):
                batch = records[i:i+100]
                client.table('fact_actuals').insert(batch).execute()
            return len(records)
        except:
            return None

def upsert_dim_crew(records: list):
    """Upsert crew master data from AIMS API"""
    client = get_client()
    if not client or not records:
        return None
    
    try:
        result = client.table('dim_crew').upsert(
            records,
            on_conflict='crew_id'
        ).execute()
        return len(records)
    except Exception as e:
        print(f"Error upserting dim_crew: {e}")
        return None

def insert_fact_leg_members(records: list):
    """Insert leg members from FetchLegMembersPerDay"""
    client = get_client()
    if not client or not records:
        return None
    
    try:
        # Insert in batches
        for i in range(0, len(records), 100):
            batch = records[i:i+100]
            client.table('fact_leg_members').insert(batch).execute()
        return len(records)
    except Exception as e:
        print(f"Error inserting fact_leg_members: {e}")
        return None

def get_fact_leg_members(filter_date: str = None):
    """Get leg members, optionally filtered by date"""
    client = get_client()
    if not client:
        return []
    
    try:
        query = client.table('fact_leg_members').select('*')
        if filter_date:
            query = query.eq('leg_date', filter_date)
        
        return _fetch_all(query)
    except Exception as e:
        print(f"Error getting fact_leg_members: {e}")
        return []

def insert_etl_log(log_data: dict):
    """Insert ETL job run log"""
    client = get_client()
    if not client:
        return None
    
    try:
        result = client.table('etl_log').insert(log_data).execute()
        return result.data
    except Exception as e:
        print(f"Error inserting etl_log: {e}")
        return None

def get_etl_logs(limit: int = 10):
    """Get recent ETL logs"""
    client = get_client()
    if not client:
        return []
    
    try:
        result = client.table('etl_log').select('*').order('start_time', desc=True).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting etl_logs: {e}")
        return []

