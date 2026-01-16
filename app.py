from flask import Flask, jsonify
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

IP_API_URL = "http://ip-api.com/json/{}"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP"}), 200

@app.route("/", methods=["GET"])
def index():
    return "Use /ip/<ip> to check an IP, e.g., /ip/8.8.8.8"

@app.route("/ip/<ip>", methods=["GET"])
def get_ip_info(ip):
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
    app.run(host="0.0.0.0", port=5000)
