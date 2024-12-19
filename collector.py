from flask import Flask, request, jsonify
import os
import psycopg2
from datetime import datetime
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Конфигурация
LOG_FILES = ["/var/log/syslog", "/var/log/dmesg", "/var/log/auth.log", "/var/log/kern.log", "/var/log/dpkg.log"]
DB_SERVER_URL = "http://192.168.1.51:5000/logs"  
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "http://192.168.1.197:5000"}})

# Инициализация SocketIO
socketio = SocketIO(app, cors_allowed_origins="http://192.168.1.197:5000")

analyzed_logs = []
alerts = []

def get_db_connection():
    try:
        conn = psycopg2.connect(dbname="logs_db", user="postgres", password="1234", host="localhost", port="5432")
        return conn
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def analyze_log(log):
    suspicious_keywords = ["error", "unauthorized", "failed", "malware", "attack"]
    for keyword in suspicious_keywords:
        if keyword in log.lower():
            return True, f"Detected keyword: {keyword}"
    return False, None

def send_to_db(log, reason, timestamp):
    try:
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') 
        
        conn = get_db_connection()
        if conn is None:
            print("No DB connection, skipping log insertion.")
            return
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO suspicious_logs (log, reason, created_at) VALUES (%s, %s, %s)",
            (log, reason, timestamp_str)
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM suspicious_logs")
        total_logs = cursor.fetchone()[0]
        conn.close()

        print(f"Total logs in DB: {total_logs}")
        socketio.emit('update_log_count', {"count": total_logs}, broadcast=True)

    except Exception as e:
        print(f"Error sending log to DB: {e}")

def process_logs():
    global analyzed_logs, alerts
    for log_file in LOG_FILES:
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                for line in f:
                    is_suspicious, reason = analyze_log(line)
                    analyzed_logs.append(line)
                    if is_suspicious:
                        alerts.append({"log": line, "reason": reason})
                        timestamp = datetime.now()  
                        send_to_db(line, reason, timestamp)

@socketio.on('new_log')
def handle_new_log(data):
    print(f"New log received: {data}")
    emit('new_log', data, broadcast=True)

@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Unable to connect to database"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, log, reason, created_at FROM suspicious_logs ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    process_logs()
    socketio.run(app, host='0.0.0.0', port=5000)
