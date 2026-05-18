import os
from flask import Flask, request, jsonify, send_file, render_template
import werkzeug.utils
from kibiz_categorize import process_csv

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
        
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400
        
    valid_files = [f for f in files if f and f.filename.endswith('.csv')]
            
    if not valid_files:
        return jsonify({'error': 'Nur CSV-Dateien sind erlaubt'}), 400
        
    try:
        # Pass the file streams directly to the processing logic
        streams = [f.stream for f in valid_files]
        result = process_csv(streams)
        
        return jsonify({
            'success': True,
            'summary': result['summary'],
            'total_rows': result['total_rows'],
            'csv_summen': result['csv_summen'],
            'csv_kontrolle': result['csv_kontrolle']
        })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<type>')
def download_file(type):
    return "Download-Logik wurde ins Frontend verlagert, da die App zustandslos ist.", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
