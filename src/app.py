"""IP Checker API service."""
from dotenv import load_dotenv
import os
import logging

from flask import Flask, jsonify
import requests

app = Flask(__name__)

# env
load_dotenv()
IP_API_URL = os.getenv("IP_API_URL")
FLASK_PORT = int(os.getenv("FLASK_PORT"))
LOG_LEVEL = os.getenv("LOG_LEVEL")

logging.basicConfig(level=getattr(logging, LOG_LEVEL))

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
    response = requests.get(IP_API_URL.format(ip), timeout=5)
    data = response.json()

    result = {
        "ip": ip,
        "country": data.get("country"),
        "countryCode": data.get("countryCode"),
        "city": data.get("city"),
        "isp": data.get("isp")
    }

    logging.info(result)
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT)
