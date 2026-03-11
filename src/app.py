"""IP Checker API service with MinIO backup."""

import json
import logging
import os
import threading
import time
from datetime import datetime

import boto3
import redis
import requests
from botocore.client import Config
from dotenv import load_dotenv
from flask import Flask, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

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
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")  # eg: "localhost:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")  # eg: "minioadmin"
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")  # eg: "minioadmin"
MINIO_BUCKET = os.getenv("MINIO_BUCKET")  # eg: "ip-backup"
BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL"))  # eg: 300

# Logging setup
logging.basicConfig(level=getattr(logging, LOG_LEVEL))

# Prometheus metrics
REQUEST_COUNT = Counter(
    "ip_checker_requests_total",
    "Total number of IP lookup requests",
)

CACHE_HITS = Counter(
    "ip_checker_cache_hits_total",
    "Number of cache hits",
)

CACHE_MISSES = Counter(
    "ip_checker_cache_misses_total",
    "Number of cache misses",
)

REQUEST_LATENCY = Histogram(
    "ip_checker_request_duration_seconds",
    "Time spent processing IP requests",
)

BACKUP_COUNT = Counter(
    "ip_checker_backups_total",
    "Number of successful MinIO backups",
)

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

def wait_for_minio(timeout=30):
    """Wait until MinIO is reachable."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            s3_client.list_buckets()
            logging.info("MinIO is reachable.")
            return True
        except Exception:
            logging.info("Waiting for MinIO to be ready...")
            time.sleep(2)
    raise RuntimeError("MinIO did not become ready in time.")

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

# Flask routes
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP"}), 200


@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "service": "IP Checker API",
            "endpoints": {
                "GET /health": "Service health check",
                "GET /ip/<ip>": "Get IP information (cached in Redis)",
                "POST /store": "Force save Redis cache to MinIO",
                "GET /": "API guide",
                "GET /metrics": "Prometheus metrics",
            },
            "example": "/ip/8.8.8.8",
        }
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/ip/<ip>", methods=["GET"])
def get_ip_info(ip):
    REQUEST_COUNT.inc()

    with REQUEST_LATENCY.time():
        cached_data = cache.get(ip)

        if cached_data:
            CACHE_HITS.inc()
            logging.info(f"Cache hit for IP: {ip}")
            return jsonify(json.loads(cached_data)), 200

        CACHE_MISSES.inc()
        logging.info(f"Cache miss for IP: {ip}, fetching from API")

        response = requests.get(IP_API_URL.format(ip), timeout=5)
        data = response.json()

        result = {
            "ip": ip,
            "country": data.get("country"),
            "countryCode": data.get("countryCode"),
            "city": data.get("city"),
            "isp": data.get("isp"),
        }

        cache.set(ip, json.dumps(result), ex=CACHE_TTL)
        logging.info(result)
        return jsonify(result), 200


@app.route("/store", methods=["POST"])
def store_now():
    try:
        save_cache_once()
        return jsonify({"status": "stored"}), 200
    except Exception as e:
        logging.error(f"Manual store failed: {e}")
        return jsonify({"error": str(e)}), 500


def save_cache_once():
    all_keys = cache.scan_iter("*")
    data_to_store = {}

    for key in all_keys:
        val = cache.get(key)
        if val:
            data_to_store[key.decode()] = json.loads(val)

    if not data_to_store:
        logging.info("No data in cache to save.")
        return

    filename = f"ip_cache_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"

    with open(filename, "w") as f:
        json.dump(data_to_store, f, indent=2)

    s3_client.upload_file(filename, MINIO_BUCKET, filename)
    os.remove(filename)

    BACKUP_COUNT.inc()
    logging.info(f"Uploaded {filename} to MinIO")


def save_cache_loop():
    while True:
        try:
            logging.info("Saving Redis cache to MinIO...")
            save_cache_once()
        except Exception as e:
            logging.error(f"Error saving cache to MinIO: {e}")

        time.sleep(BACKUP_INTERVAL)


# Start background thread
threading.Thread(target=save_cache_loop, daemon=True).start()

# Run Flask app
if __name__ == "__main__":
    wait_for_minio()
    ensure_bucket()
    app.run(host="0.0.0.0", port=FLASK_PORT)
