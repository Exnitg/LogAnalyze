from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime
import socketio
import eventlet  # Для работы с eventlet
from flask_cors import CORS  # Импортируем CORS для поддержки междоменных запросов

# Конфигурация PostgreSQL
DB_CONFIG = {
    'dbname': 'logs_db',
    'user': 'postgres',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

app = Flask(__name__)

# Настройка CORS для Flask (необязательно, если только WebSocket используется)
CORS(app, resources={r"/*": {"origins": "http://192.168.1.197:5000"}})

# Настройка SocketIO с разрешением подключений только с определённого источника
sio = socketio.Server(cors_allowed_origins="http://192.168.1.197:5000", async_mode='eventlet')

# Подключаем SocketIO к Flask
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Подключение к базе данных
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suspicious_logs (
            id SERIAL PRIMARY KEY,
            log TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

# API для добавления логов
@app.route("/logs", methods=["POST"])
def add_log():
    data = request.get_json()
    if not data or "log" not in data or "reason" not in data:
        return jsonify({"error": "Invalid data"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Преобразуем строку даты в объект datetime
        if "created_at" in data:
            created_at = datetime.strptime(data["created_at"], '%Y-%m-%d %H:%M:%S')
        else:
            created_at = datetime.now()

        cursor.execute(
            "INSERT INTO suspicious_logs (log, reason, created_at) VALUES (%s, %s, %s)",
            (data["log"], data["reason"], created_at)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Отправляем новое сообщение через WebSocket
        sio.emit('new_log', {"log": data["log"], "reason": data["reason"], "created_at": created_at.isoformat()})

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API для получения логов
@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, log, reason, created_at FROM suspicious_logs")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    # Запускаем сервер через eventlet
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), app)
