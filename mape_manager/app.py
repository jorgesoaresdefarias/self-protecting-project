from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)

attempts_by_ip = defaultdict(list)
blocked_ips = {}
state_by_ip = defaultdict(lambda: {"captcha": False, "2fa": False})

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
BLOCK_TIME_SECONDS = 300

@app.route("/register_attempt", methods=["POST"])
def monitor():
    data = request.json
    ip = data.get("ip")
    success = data.get("success")
    timestamp = datetime.now()

    if not success:
        attempts_by_ip[ip].append(timestamp)
    else:
        attempts_by_ip[ip] = []
        state_by_ip[ip] = {"captcha": False, "2fa": False}

    return jsonify({"status": "ok"})

@app.route("/evaluate", methods=["POST"])
@app.route("/evaluate", methods=["POST"])
def analyze_and_plan():
    data = request.json
    ip = data.get("ip")
    now = datetime.now()

    if ip in blocked_ips and blocked_ips[ip] < now:
        del blocked_ips[ip]

    if ip in blocked_ips:
        return jsonify({"action": "block", "debug": "IP is currently blocked", "num_attempts": len(attempts_by_ip[ip])})

    recent_attempts = [t for t in attempts_by_ip[ip] if (now - t).total_seconds() <= WINDOW_SECONDS]
    attempts_by_ip[ip] = recent_attempts
    num_attempts = len(recent_attempts)

    if num_attempts >= 7:
        blocked_ips[ip] = now + timedelta(seconds=BLOCK_TIME_SECONDS)
        return jsonify({"action": "block", "debug": "Blocked due to too many attempts", "num_attempts": num_attempts})
    elif num_attempts >= 6:
        state_by_ip[ip]["2fa"] = True
        return jsonify({"action": "2fa", "debug": "2FA required", "num_attempts": num_attempts})
    elif num_attempts >= 3:
        state_by_ip[ip]["captcha"] = True
        return jsonify({"action": "captcha", "show_captcha": True, "debug": "Captcha triggered", "num_attempts": num_attempts})
    else:
        return jsonify({"action": "allow", "show_captcha": False, "debug": "Access allowed", "num_attempts": num_attempts})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)