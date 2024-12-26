from flask import Flask
import paramiko
import time
from datetime import datetime
import requests
import logging
from flask_cors import CORS
import threading
import signal
import sys
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LOG_FILES = ["/var/log/syslog", "/var/log/dmesg", "/var/log/auth.log", "/var/log/kern.log", "/var/log/dpkg.log"]
DB_SERVER_URL = "http://192.168.1.51:5000/logs"
REMOTE_HOST = "192.168.1.197"
REMOTE_USER = "client"
REMOTE_PASSWORD = "1234"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Настройка сессии с повторными попытками
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

def analyze_log(log):
    suspicious_keywords = ["error", "unauthorized", "failed", "malware", "attack"]
    for keyword in suspicious_keywords:
        if keyword in log.lower():
            logger.debug(f"Suspicious log detected with keyword: {keyword}")
            return True, f"Detected keyword: {keyword}"
    return False, None

def send_to_db(log, reason, timestamp):
    try:
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "log": log,
            "reason": reason,
            "created_at": timestamp_str
        }
        response = session.post(DB_SERVER_URL, json=data, timeout=10)
        response.raise_for_status()
        logger.debug(f"Log sent successfully: {data}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending log to DB: {e}")

def tail_log(log_file):
    while True:
        try:
            with paramiko.SSHClient() as client:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASSWORD)
                logger.debug(f"Connected to {REMOTE_HOST} for {log_file}")
                
                stdin, stdout, stderr = client.exec_command(f"tail -f {log_file}")
                while True:
                    line = stdout.readline()
                    if line:
                        log_line = line.strip()
                        logger.debug(f"Log line from {log_file}: {log_line}")

                        is_suspicious, reason = analyze_log(log_line)
                        if is_suspicious:
                            logger.debug(f"Suspicious log detected in {log_file}: {log_line}, reason: {reason}")
                            timestamp = datetime.now()
                            send_to_db(log_line, reason, timestamp)
                    else:
                        break
        except Exception as e:
            logger.error(f"Error in tail_log for {log_file}: {e}")
            time.sleep(5)  # Wait before retrying

def signal_handler(signum, frame):
    logger.info("Received signal to terminate. Closing connections...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.debug("Starting the log collection process...")
    threads = []
    for log_file in LOG_FILES:
        thread = threading.Thread(target=tail_log, args=(log_file,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()