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



# ==================== DATA LOADING HELPERS ====================

def ensure_data_loaded():
    """Ensure processor has data loaded (from Supabase or Local)"""
    if not processor:
        return

    if supabase_connected and db:
        try:
            # Refresh data from Supabase
            # This populates processor's internal state (flights, rolling_hours, etc.)
            processor.load_from_supabase()
        except Exception as e:
            print(f"[ERROR] Supabase load failed: {e}")
            # Fallback to local files if Supabase fails? 
            # On Vercel local files might not exist or be stale, but worth a try
            pass
    else:
        # Local mode - process files
        try:
            processor.process_dayrep_csv()
            processor.process_sacutil_csv()
            processor.process_rolcrtot_csv()
            processor.process_crew_schedule_csv()
        except Exception as e:
            print(f"[ERROR] Local load failed: {e}")



# ==================== ROUTES ====================
@app.route('/')
def index():
    filter_date = request.args.get('date')
    
    # Check flight trend flag (experimental)
    # processor.calculate_flight_trend = True 

    try:
        # Load/Refresh data
        ensure_data_loaded()
        
        # Get Dashboard Data (Directly from processor to match local consistency)
        if processor:
            data = processor.get_dashboard_data(filter_date)
            
            # Special handling for calculating specific stats if needed
            # (e.g. compliance rate is calculated in api_server.py but maybe not in get_dashboard_data?)
            # In api_server.py: 
            # compliance_stats = processor.calculate_rolling_28day_stats()
            # data['compliance_rate'] = compliance_stats.get('compliance_rate', 100)
            
            compliance_stats = processor.calculate_rolling_28day_stats()
            data['compliance_rate'] = compliance_stats.get('compliance_rate', 100)
            
        else:
            data = {} # Should not happen if initialized correctly
            
    except Exception as e:
        print(f"[ERROR] Index: {e}")
        traceback.print_exc()
        data = {} # Fallback
    
    # Determine AIMS status
    aims_enabled = False # Default to False for Vercel unless configured
    
    try:
        return render_template('crew_dashboard.html', 
                             data=data, 
                             filter_date=filter_date, 
                             db_connected=supabase_connected, 
                             aims_enabled=aims_enabled)
    except Exception as e:
        return f"<h1>Template Error</h1><pre>{traceback.format_exc()}</pre>", 500


@app.route('/upload', methods=['POST'])
def upload_files():
    if not supabase_connected or not db:
        flash('Supabase not connected')
        return redirect(url_for('index'))
    
    try:
        if 'dayrep' in request.files and request.files['dayrep'].filename:
            f = request.files['dayrep']
            content = f.read()
            # Use sync_db=True to let processor handle DB insertion
            res = processor.process_dayrep_csv(file_path=f.filename, file_content=content, sync_db=True)
            print(f"[UPLOAD] Processed dayrep: {res} records")

        if 'sacutil' in request.files and request.files['sacutil'].filename:
            f = request.files['sacutil']
            content = f.read()
            res = processor.process_sacutil_csv(file_path=f.filename, file_content=content, sync_db=True)
            print(f"[UPLOAD] Processed sacutil: {res} records")
        
        if 'rolcrtot' in request.files and request.files['rolcrtot'].filename:
            f = request.files['rolcrtot']
            content = f.read()
            res = processor.process_rolcrtot_csv(file_path=f.filename, file_content=content, sync_db=True)
            print(f"[UPLOAD] Processed rolcrtot: {res} records")
        
        if 'crew_schedule' in request.files and request.files['crew_schedule'].filename:
            f = request.files['crew_schedule']
            content = f.read()
            res = processor.process_crew_schedule_csv(file_path=f.filename, file_content=content, sync_db=True)
            print(f"[UPLOAD] Processed crew_schedule: {res} records")
        
        flash('Data uploaded and synced successfully!')
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        traceback.print_exc()
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
