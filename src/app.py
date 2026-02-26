"""IP Checker API service with MinIO backup."""
from dotenv import load_dotenv
import os
import logging
import json
import threading
import time
from datetime import datetime

from flask import Flask, jsonify
import requests
import redis
import boto3
from botocore.client import Config

app = Flask(__name__)

# Load environment variables
load_dotenv()
IP_API_URL = os.getenv("IP_API_URL")
FLASK_PORT = int(os.getenv("FLASK_PORT"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_DB = int(os.getenv("REDIS_DB"))
CACHE_TTL = int(os.getenv("CACHE_TTL"))

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")      # eg: "localhost:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")  # eg: "minioadmin"
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")  # eg: "minioadmin"
MINIO_BUCKET = os.getenv("MINIO_BUCKET")          # eg: "ip-backup"
BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL")) # eg: 300

# Logging setup
logging.basicConfig(level=getattr(logging, LOG_LEVEL))

# Initialize Redis
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Initialize MinIO client
s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)

def ensure_bucket():
    """Ensure that the MinIO bucket exists."""
    try:
        existing = [b["Name"] for b in s3_client.list_buckets().get("Buckets", [])]
        if MINIO_BUCKET not in existing:
            logging.info(f"Bucket '{MINIO_BUCKET}' does not exist. Creating...")
            s3_client.create_bucket(Bucket=MINIO_BUCKET)
            logging.info(f"Bucket '{MINIO_BUCKET}' created successfully.")
        else:
            logging.info(f"Bucket '{MINIO_BUCKET}' already exists.")
    except Exception as e:
        logging.error(f"Error checking/creating bucket: {e}")

ensure_bucket()

# Flask routes
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP"}), 200

@app.route("/", methods=["GET"])
def index():
    return "Use /ip/<ip> to check an IP, e.g., /ip/8.8.8.8"

@app.route("/ip/<ip>", methods=["GET"])
def get_ip_info(ip):
    cached_data = cache.get(ip)
    if cached_data:
        logging.info(f"Cache hit for IP: {ip}")
        return jsonify(json.loads(cached_data)), 200

    logging.info(f"Cache miss for IP: {ip}, fetching from API")
    response = requests.get(IP_API_URL.format(ip), timeout=5)
    data = response.json()

    result = {
        "ip": ip,
        "country": data.get("country"),
        "countryCode": data.get("countryCode"),
        "city": data.get("city"),
        "isp": data.get("isp")
    }

    # Store in Redis cache
    cache.set(ip, json.dumps(result), ex=CACHE_TTL)
    logging.info(result)
    return jsonify(result), 200

def save_cache_loop():
    """Background loop to save Redis cache to MinIO every 5 minutes."""
    while True:
        try:
            logging.info("Saving Redis cache to MinIO...")
            all_keys = cache.scan_iter("*")
            data_to_store = {}
            for key in all_keys:
                val = cache.get(key)
                if val:
                    data_to_store[key.decode()] = json.loads(val)
            logging.info(f"Redis data: {data_to_store}")

            if data_to_store:
                filename = f"ip_cache_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
                with open(filename, "w") as f:
                    json.dump(data_to_store, f, indent=2)

                s3_client.upload_file(filename, MINIO_BUCKET, filename)
                logging.info(f"Uploaded {filename} to MinIO bucket {MINIO_BUCKET}")
                os.remove(filename)
            else:
                logging.info("No data in cache to save.")

        except Exception as e:
            logging.error(f"Error saving cache to MinIO: {e}")

        # Sleep before next backup
        time.sleep(300)

# Start background thread
threading.Thread(target=save_cache_loop, daemon=True).start()

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT)