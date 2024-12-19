from flask import Flask, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import requests
from flask_cors import CORS 

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "http://192.168.1.197:5000"}})

socketio = SocketIO(app, cors_allowed_origins="http://192.168.1.197:5000")

@socketio.on('new_log')
def handle_new_log(data):
    print(f"New log received: {data}")
    emit('new_log', data, broadcast=True)

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        response = requests.get('http://192.168.1.51:5000/logs') 
        response.raise_for_status()
        logs = response.json()
        return jsonify(logs), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
