"""IP Checker API service."""
from dotenv import load_dotenv
import os
import logging
import json

from flask import Flask, jsonify
import requests
import redis

app = Flask(__name__)

# env
load_dotenv()
IP_API_URL = os.getenv("IP_API_URL")
FLASK_PORT = int(os.getenv("FLASK_PORT"))
LOG_LEVEL = os.getenv("LOG_LEVEL")

logging.basicConfig(level=getattr(logging, LOG_LEVEL))

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_DB = int(os.getenv("REDIS_DB"))
CACHE_TTL = int(os.getenv("CACHE_TTL"))

# Initialize Redis (Valkey)
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "UP"}), 200

@app.route("/", methods=["GET"])
def index():
    """Root endpoint with usage instructions."""
    return "Use /ip/<ip> to check an IP, e.g., /ip/8.8.8.8"

@app.route("/ip/<ip>", methods=["GET"])
def get_ip_info(ip):
    """Fetch IP information from ip-api.com."""
    
    # Check cache
    cached_data = cache.get(ip)
    if cached_data:
        logging.info(f"Cache hit for IP: {ip}")
        return jsonify(json.loads(cached_data)), 200

    # Cache miss —> fetch from API
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
    
    # Store in cache
    cache.set(ip, json.dumps(result), ex=CACHE_TTL)
    
    logging.info(result)
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT)
