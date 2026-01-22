"""
Vercel Serverless Function Handler for Crew Management Dashboard
Full Version with Supabase Integration
"""

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
import os
import sys
import re
import traceback

# Add parent directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Initialize Flask
app = Flask(__name__, template_folder=root_dir)
app.secret_key = os.environ.get('SECRET_KEY', 'crew-dashboard-2026')

# ==================== SAFE IMPORTS ====================
processor = None
db = None
supabase_connected = False

try:
    from data_processor import DataProcessor
    processor = DataProcessor(data_dir=root_dir)
    print("[OK] DataProcessor loaded")
except Exception as e:
    print(f"[WARN] DataProcessor failed: {e}")

# Check Supabase credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    try:
        import supabase_client as db
        supabase_connected, msg = db.check_connection()
        print(f"[SUPABASE] {msg}")
    except Exception as e:
        print(f"[WARN] Supabase failed: {e}")
        db = None
else:
    print("[INFO] Supabase credentials not set - using local files")


# ==================== DEFAULT DATA ====================
def get_default_data():
    return {
        'summary': {
            'total_aircraft': 0, 'total_flights': 0, 'total_crew': 0,
            'avg_flight_hours': 0, 'total_block_hours': 0, 'crew_rotation_count': 0,
            'crew_by_role': {'CP': 0, 'FO': 0, 'PU': 0, 'FA': 0}
        },
        'aircraft': [], 'crew_roles': {'CP': 0, 'FO': 0, 'PU': 0, 'FA': 0},
        'crew_rotations': [], 'available_dates': [], 'operating_crew': [],
        'utilization': {}, 'rolling_hours': [],
        'rolling_stats': {'normal': 0, 'warning': 0, 'critical': 0, 'total': 0},
        'crew_schedule': {'summary': {'SL': 0, 'CSL': 0, 'SBY': 0, 'OSBY': 0}}
    }


def load_local_data():
    """Load data from local CSV files"""
    if not processor:
        return get_default_data(), []
    try:
        processor.process_dayrep_csv()
        processor.process_sacutil_csv()
        processor.process_rolcrtot_csv()
        processor.process_crew_schedule_csv()
        return processor.calculate_metrics(None), processor.available_dates
    except Exception as e:
        print(f"[ERROR] Load local data: {e}")
        return get_default_data(), []


def load_supabase_data(filter_date=None):
    """Load data from Supabase"""
    if not db or not supabase_connected or not processor:
        return get_default_data(), []
    
    try:
        flights = db.get_flights(filter_date) or []
        available_dates = db.get_available_dates() or []
        
        if not flights:
            return get_default_data(), available_dates
        
        # Process flights
        processor.flights = flights
        processor.available_dates = available_dates
        processor.crew_to_regs.clear()
        processor.reg_flight_hours.clear()
        processor.reg_flight_count.clear()
        
        for flight in flights:
            try:
                reg = flight.get('reg', '')
                std, sta = flight.get('std', ''), flight.get('sta', '')
                crew_string = flight.get('crew', '')
                
                if std and sta and ':' in str(std) and ':' in str(sta):
                    std_min = int(str(std).split(':')[0]) * 60 + int(str(std).split(':')[1])
                    sta_min = int(str(sta).split(':')[0]) * 60 + int(str(sta).split(':')[1])
                    duration = sta_min - std_min
                    if duration < 0: duration += 24 * 60
                    processor.reg_flight_hours[reg] += duration / 60
                    processor.reg_flight_count[reg] += 1
                
                if crew_string:
                    for role, crew_id in re.findall(r'\(([A-Z]{2})\)\s*(\d+)', str(crew_string)):
                        processor.crew_to_regs[crew_id].add(reg)
                        processor.crew_roles[crew_id] = role
            except:
                continue
        
        metrics = processor.calculate_metrics(filter_date)
        
        # Add Supabase-specific data
        try:
            # 1. Rolling Hours
            all_rolling = db.get_rolling_hours() or []
            metrics['rolling_hours'] = all_rolling[:20]
            
            # Recalculate rolling_stats locally from the full list
            stats = {'normal': 0, 'warning': 0, 'critical': 0}
            for r in all_rolling:
                status = r.get('status', 'normal').lower()
                if status in stats:
                    stats[status] += 1
            metrics['rolling_stats'] = stats

            # 2. Crew Schedule Summary
            # Wrap in summary to match template expectation: data.crew_schedule.summary
            summary_data = db.get_crew_schedule_summary(filter_date) or {'SL': 0, 'CSL': 0, 'SBY': 0, 'OSBY': 0}
            metrics['crew_schedule'] = {'summary': summary_data}
        except Exception as e:
            print(f"Error processing Supabase data: {e}")
        
        return metrics, available_dates
    except Exception as e:
        print(f"[ERROR] Supabase load: {e}")
        return get_default_data(), []


# ==================== ROUTES ====================
@app.route('/')
def index():
    filter_date = request.args.get('date')
    data = get_default_data()
    available_dates = []
    
    try:
        if supabase_connected and db:
            metrics, available_dates = load_supabase_data(filter_date)
        else:
            metrics, available_dates = load_local_data()
        
        data = {
            'summary': metrics.get('summary', data['summary']),
            'aircraft': list(processor.reg_flight_hours.keys()) if processor else [],
            'crew_roles': metrics.get('crew_roles', data['crew_roles']),
            'crew_rotations': metrics.get('crew_rotations', []),
            'available_dates': available_dates,
            'operating_crew': metrics.get('operating_crew', []),
            'utilization': metrics.get('utilization', {}),
            'rolling_hours': metrics.get('rolling_hours', []),
            'rolling_stats': metrics.get('rolling_stats', data['rolling_stats']),
            'crew_schedule': metrics.get('crew_schedule', data['crew_schedule']),
            
            # Pass compliance lists
            'compliance_28d_all': metrics.get('compliance_28d_all', []),
            'compliance_28d_top20': metrics.get('compliance_28d_top20', []),
            'compliance_12m_all': metrics.get('compliance_12m_all', []),
            'compliance_12m_top20': metrics.get('compliance_12m_top20', [])
        }
    except Exception as e:
        print(f"[ERROR] Index: {e}")
        traceback.print_exc()
    
    try:
        return render_template('crew_dashboard.html', data=data, filter_date=filter_date, db_connected=supabase_connected)
    except Exception as e:
        return f"<h1>Template Error</h1><pre>{traceback.format_exc()}</pre>", 500


@app.route('/upload', methods=['POST'])
def upload_files():
    if not supabase_connected or not db:
        flash('Supabase not connected')
        return redirect(url_for('index'))
    
    try:
        if 'dayrep' in request.files and request.files['dayrep'].filename:
            content = request.files['dayrep'].read()
            count = processor.process_dayrep_csv(file_content=content, sync_db=False)
            res = db.insert_flights([{
                'date': f.get('date', ''), 'calendar_date': f.get('calendar_date', ''),
                'reg': f.get('reg', ''), 'flt': f.get('flt', ''),
                'dep': f.get('dep', ''), 'arr': f.get('arr', ''),
                'std': f.get('std', ''), 'sta': f.get('sta', ''),
                'crew': f.get('crew', '')
            } for f in processor.flights])
            if res is None: raise Exception("Failed to insert flights to DB. Check RLS policies.")

        if 'sacutil' in request.files and request.files['sacutil'].filename:
            content = request.files['sacutil'].read()
            processor.process_sacutil_csv(file_content=content, sync_db=False)
            util_data = []
            for date_str, ac_types in processor.ac_utilization_by_date.items():
                for ac_type, stats in ac_types.items():
                    util_data.append({
                        'date': date_str, 'ac_type': ac_type,
                        'dom_block': stats.get('dom_block', '00:00'),
                        'int_block': stats.get('int_block', '00:00'),
                        'total_block': stats.get('total_block', '00:00'),
                        'dom_cycles': int(stats.get('dom_cycles', 0) or 0),
                        'int_cycles': int(stats.get('int_cycles', 0) or 0),
                        'total_cycles': int(stats.get('total_cycles', 0) or 0),
                        'avg_util': stats.get('avg_util', '')
                    })
            if util_data:
                res = db.insert_ac_utilization(util_data)
                if res is None: raise Exception("Failed to insert AC util to DB.")
        
        if 'rolcrtot' in request.files and request.files['rolcrtot'].filename:
            content = request.files['rolcrtot'].read()
            processor.process_rolcrtot_csv(file_content=content, sync_db=False)
            hours_data = [{
                'crew_id': item.get('id', ''), 'name': item.get('name', ''),
                'seniority': item.get('seniority', ''),
                'block_28day': item.get('block_28day', '0:00'),
                'block_12month': item.get('block_12month', '0:00'),
                'hours_28day': item.get('hours_28day', 0),
                'hours_12month': item.get('hours_12month', 0),
                'percentage': item.get('percentage', 0),
                'percentage_12m': item.get('percentage_12m', 0),
                'status': item.get('status', 'normal'),
                'status_12m': item.get('status_12m', 'normal')
            } for item in processor.rolling_hours]
            if hours_data:
                res = db.insert_rolling_hours(hours_data)
                if res is None: raise Exception("Failed to insert rolling hours to DB.")
        
        if 'crew_schedule' in request.files and request.files['crew_schedule'].filename:
            content = request.files['crew_schedule'].read()
            processor.process_crew_schedule_csv(file_content=content, sync_db=False)
            schedule_data = []
            for date_str, counts in processor.crew_schedule_by_date.items():
                for status_type in ['SL', 'CSL', 'SBY', 'OSBY']:
                    for _ in range(counts.get(status_type, 0)):
                        schedule_data.append({'date': date_str, 'status_type': status_type})
            if schedule_data:
                res = db.insert_crew_schedule(schedule_data)
                if res is None: raise Exception("Failed to insert crew schedule to DB.")
        
        flash('Data uploaded successfully!')
    except Exception as e:
        flash(f'Upload error: {str(e)}')
    
    return redirect(url_for('index'))


@app.route('/api/status')
def api_status():
    return jsonify({
        'processor_loaded': processor is not None,
        'supabase_url_set': SUPABASE_URL is not None,
        'supabase_key_set': SUPABASE_KEY is not None,
        'supabase_connected': supabase_connected
    })


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})
