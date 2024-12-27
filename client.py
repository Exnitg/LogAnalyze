from flask import Flask, jsonify, render_template, send_from_directory, request
import requests
from flask_cors import CORS
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        last_id = request.args.get('last_id', 0)
        logger.debug(f"Fetching logs with last_id={last_id}")
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'http://192.168.1.51:5000/logs?last_id={last_id}',
            headers=headers,
            timeout=10
        )
        
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        
        if response.status_code != 200:
            logger.error(f"Server returned error: {response.text}")
            return jsonify({"error": "Server error", "details": response.text}), 500
            
        data = response.json()
        logger.debug(f"Successfully received data: {data}")
        
        # Поскольку мы получаем список напрямую, просто передаем его дальше
        return jsonify(data), 200
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({"error": "Failed to fetch logs", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal error", "details": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    logger.info("Starting the client server...")
    app.run(host='0.0.0.0', port=5000)