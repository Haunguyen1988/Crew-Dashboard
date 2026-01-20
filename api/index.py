from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Crew Dashboard</title></head>
    <body style="background:#1a1a2e;color:#fff;font-family:Arial;padding:40px;text-align:center;">
        <h1 style="color:#3b82f6;">✈️ Crew Dashboard</h1>
        <p style="color:#22c55e;font-size:24px;">Flask is working on Vercel!</p>
        <p>Build successful. Ready to add full functionality.</p>
    </body>
    </html>
    '''

@app.route('/api/health')
def health():
    return {'status': 'ok'}
