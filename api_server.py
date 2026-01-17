"""
Flask API Server for Crew Management Dashboard
Provides REST API endpoints for dashboard data and CSV upload
"""

from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from data_processor import get_processor, refresh_data, DataProcessor

app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== API ENDPOINTS ====================

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get all dashboard data. Optional ?date=DD/MM/YY for filtering by specific date"""
    processor = get_processor()
    # Get optional date filter from query parameter
    filter_date = request.args.get('date', None)
    data = processor.get_dashboard_data(filter_date)
    return jsonify(data)


@app.route('/api/aircraft', methods=['GET'])
def get_aircraft():
    """Get aircraft list with flight hours"""
    processor = get_processor()
    data = processor.get_dashboard_data()
    return jsonify({
        'total': data['summary']['total_aircraft'],
        'avg_flight_hours': data['summary']['avg_flight_hours'],
        'aircraft': data['aircraft']
    })


@app.route('/api/crew', methods=['GET'])
def get_crew():
    """Get crew statistics"""
    processor = get_processor()
    data = processor.get_dashboard_data()
    return jsonify({
        'total': data['summary']['total_crew'],
        'by_role': data['crew_roles']
    })


@app.route('/api/crew/multi-reg', methods=['GET'])
def get_multi_reg_crew():
    """Get crew flying on multiple aircraft registrations"""
    processor = get_processor()
    data = processor.get_dashboard_data()
    return jsonify({
        'count': data['summary']['multi_reg_count'],
        'crew': data['multi_reg_crew']
    })


@app.route('/api/utilization', methods=['GET'])
def get_utilization():
    """Get aircraft utilization data"""
    processor = get_processor()
    data = processor.get_dashboard_data()
    return jsonify(data['utilization'])


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get summary KPIs"""
    processor = get_processor()
    data = processor.get_dashboard_data()
    return jsonify(data['summary'])


# ==================== FILE UPLOAD ENDPOINTS ====================

@app.route('/api/upload/dayrep', methods=['POST'])
def upload_dayrep():
    """Upload DayRepReport CSV file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'DayRepReport.csv')
        file.save(filepath)
        
        # Process the new file
        processor = get_processor()
        try:
            flights = processor.process_dayrep_csv(filepath)
            data = processor.get_dashboard_data()
            return jsonify({
                'success': True,
                'message': f'Processed {flights} flights',
                'summary': data['summary']
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400


@app.route('/api/upload/sacutil', methods=['POST'])
def upload_sacutil():
    """Upload SacutilReport CSV file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'SacutilReport.csv')
        file.save(filepath)
        
        # Process the new file
        processor = get_processor()
        try:
            count = processor.process_sacutil_csv(filepath)
            data = processor.get_dashboard_data()
            return jsonify({
                'success': True,
                'message': f'Processed {count} aircraft types',
                'utilization': data['utilization']
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400


@app.route('/api/upload/rolcrtot', methods=['POST'])
def upload_rolcrtot():
    """Upload RolCrTotReport CSV file - Rolling block hours"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'RolCrTotReport.csv')
        file.save(filepath)
        
        # Process the new file
        processor = get_processor()
        try:
            count = processor.process_rolcrtot_csv(filepath)
            data = processor.get_dashboard_data()
            return jsonify({
                'success': True,
                'message': f'Processed {count} crew rolling hours records',
                'rolling_stats': data['rolling_stats']
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400


@app.route('/api/upload/crew_schedule', methods=['POST'])
def upload_crew_schedule():
    """Upload Crew Schedule CSV file - Standby, sick-call, fatigue"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'CrewSchedule.csv')
        file.save(filepath)
        
        # Process the new file
        processor = get_processor()
        try:
            count = processor.process_crew_schedule_csv(filepath)
            data = processor.get_dashboard_data()
            return jsonify({
                'success': True,
                'message': f'Processed {count} crew schedule records',
                'crew_schedule_summary': data['crew_schedule']['summary']
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Refresh data from uploaded files"""
    try:
        data = refresh_data()
        return jsonify({
            'success': True,
            'message': 'Data refreshed',
            'summary': data['summary']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== STATIC FILE SERVING ====================

@app.route('/')
def index():
    """Serve the dashboard"""
    return send_from_directory('.', 'crew_dashboard.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)


# ==================== API DOCUMENTATION ====================

@app.route('/api')
def api_docs():
    """API Documentation"""
    docs = """
    <html>
    <head>
        <title>Crew Dashboard API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #1e3a5f; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #1e3a5f; color: white; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
            .method { font-weight: bold; }
            .get { color: #22c55e; }
            .post { color: #3b82f6; }
        </style>
    </head>
    <body>
        <h1>🛫 Crew Dashboard API</h1>
        <p>REST API for Crew Management Dashboard</p>
        
        <h2>Endpoints</h2>
        <table>
            <tr>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Description</th>
            </tr>
            <tr>
                <td><span class="method get">GET</span></td>
                <td><code>/api/dashboard</code></td>
                <td>Get all dashboard data</td>
            </tr>
            <tr>
                <td><span class="method get">GET</span></td>
                <td><code>/api/summary</code></td>
                <td>Get summary KPIs only</td>
            </tr>
            <tr>
                <td><span class="method get">GET</span></td>
                <td><code>/api/aircraft</code></td>
                <td>Get aircraft list with flight hours</td>
            </tr>
            <tr>
                <td><span class="method get">GET</span></td>
                <td><code>/api/crew</code></td>
                <td>Get crew statistics by role</td>
            </tr>
            <tr>
                <td><span class="method get">GET</span></td>
                <td><code>/api/crew/multi-reg</code></td>
                <td>Get crew flying on 2+ REGs</td>
            </tr>
            <tr>
                <td><span class="method get">GET</span></td>
                <td><code>/api/utilization</code></td>
                <td>Get aircraft utilization data</td>
            </tr>
            <tr>
                <td><span class="method post">POST</span></td>
                <td><code>/api/upload/dayrep</code></td>
                <td>Upload DayRepReport CSV</td>
            </tr>
            <tr>
                <td><span class="method post">POST</span></td>
                <td><code>/api/upload/sacutil</code></td>
                <td>Upload SacutilReport CSV</td>
            </tr>
            <tr>
                <td><span class="method post">POST</span></td>
                <td><code>/api/upload/rolcrtot</code></td>
                <td>Upload RolCrTotReport CSV (Rolling block hours)</td>
            </tr>
            <tr>
                <td><span class="method post">POST</span></td>
                <td><code>/api/upload/crew_schedule</code></td>
                <td>Upload Crew Schedule CSV (Standby/Sick-call/Fatigue)</td>
            </tr>
            <tr>
                <td><span class="method post">POST</span></td>
                <td><code>/api/refresh</code></td>
                <td>Refresh data from files</td>
            </tr>
        </table>
        
        <h2>Quick Start</h2>
        <p>Open <a href="/">Dashboard</a> or test API with:</p>
        <pre><code>curl http://localhost:5000/api/summary</code></pre>
    </body>
    </html>
    """
    return docs


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("Crew Management Dashboard API Server")
    print("=" * 60)
    print(f"\nStarting server on port {port}...")
    print(f"Dashboard: http://localhost:{port}")
    print(f"API Docs:  http://localhost:{port}/api")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'True').lower() == 'true')
