from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB_CONFIG = {
    'dbname': 'logs_db',
    'user': 'postgres',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

def get_db_connection():
    try:
        logger.debug("Attempting to connect to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("Database connection successful")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        logger.debug("Received request for logs")
        last_id = request.args.get('last_id', 0, type=int)
        logger.debug(f"Last ID parameter: {last_id}")

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем наличие данных в таблице
        cursor.execute("SELECT COUNT(*) FROM suspicious_logs")
        count = cursor.fetchone()[0]
        logger.debug(f"Total records in database: {count}")
        
        query = """
            SELECT id, log, reason, created_at 
            FROM suspicious_logs 
            WHERE id > %s 
            ORDER BY created_at DESC
        """
        cursor.execute(query, (last_id,))
        rows = cursor.fetchall()
        logger.debug(f"Fetched {len(rows)} rows from database")

        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "log": row[1],
                "reason": row[2],
                "created_at": row[3].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        logger.debug(f"Returning {len(logs)} logs")
        return jsonify(logs)

    except psycopg2.Error as e:
        logger.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/logs", methods=["POST"])
def add_log():
    try:
        data = request.get_json()
        logger.debug(f"Received log data: {data}")
        
        if not data or "log" not in data or "reason" not in data:
            return jsonify({"error": "Invalid data"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        created_at = datetime.now() if "created_at" not in data else datetime.strptime(data["created_at"], '%Y-%m-%d %H:%M:%S')
        
        cursor.execute(
            "INSERT INTO suspicious_logs (log, reason, created_at) VALUES (%s, %s, %s) RETURNING id",
            (data["log"], data["reason"], created_at)
        )
        
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.debug(f"Successfully inserted log with id: {new_id}")
        return jsonify({"status": "success", "id": new_id}), 200
        
    except Exception as e:
        logger.error(f"Error adding log: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Проверяем подключение к БД при запуске
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Проверяем существование таблицы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suspicious_logs (
                id SERIAL PRIMARY KEY,
                log TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database connection test successful, table verified")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

    app.run(host='0.0.0.0', port=5000, debug=True)
