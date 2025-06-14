from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)

# Estado do sistema
attempts_by_ip = defaultdict(list)
blocked_ips = {}
state_by_ip = defaultdict(lambda: {"captcha": False, "2fa": False})

# Parâmetros do sistema
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
BLOCK_TIME_SECONDS = 300

# =============================
# MAPE FUNCTIONS
# =============================

# 🟩 M: Monitoramento
def monitor(ip, success):
    timestamp = datetime.now()
    if not success:
        attempts_by_ip[ip].append(timestamp)
    else:
        attempts_by_ip[ip] = []
        state_by_ip[ip] = {"captcha": False, "2fa": False}


# 🟨 A: Análise
def analyze(ip):
    now = datetime.now()

    # Remove bloqueios expirados
    if ip in blocked_ips and blocked_ips[ip] < now:
        del blocked_ips[ip]

    if ip in blocked_ips:
        return "block", len(attempts_by_ip[ip])

    # Filtra tentativas recentes
    recent_attempts = [t for t in attempts_by_ip[ip] if (now - t).total_seconds() <= WINDOW_SECONDS]
    attempts_by_ip[ip] = recent_attempts
    return recent_attempts


# 🟧 P: Planejamento
def plan(ip, recent_attempts):
    num_attempts = len(recent_attempts)
    now = datetime.now()

    if num_attempts >= 7:
        blocked_ips[ip] = now + timedelta(seconds=BLOCK_TIME_SECONDS)
        return {"action": "block", "debug": "Blocked due to too many attempts", "num_attempts": num_attempts}

    elif num_attempts >= 6:
        state_by_ip[ip]["2fa"] = True
        return {"action": "2fa", "debug": "2FA required", "num_attempts": num_attempts}

    elif num_attempts >= 3:
        state_by_ip[ip]["captcha"] = True
        return {"action": "captcha", "show_captcha": True, "debug": "Captcha triggered", "num_attempts": num_attempts}

    else:
        return {"action": "allow", "show_captcha": False, "debug": "Access allowed", "num_attempts": num_attempts}


# 🟥 E: Execução (aqui usada para responder com o plano já decidido)
def execute(response):
    return jsonify(response)


# =============================
# FLASK ROUTES
# =============================

@app.route("/register_attempt", methods=["POST"])
def handle_monitor():
    data = request.json
    ip = data.get("ip")
    success = data.get("success")
    monitor(ip, success)
    return jsonify({"status": "ok"})


@app.route("/evaluate", methods=["POST"])
def handle_analyze_and_plan():
    data = request.json
    ip = data.get("ip")

    analysis = analyze(ip)
    if isinstance(analysis, tuple) and analysis[0] == "block":
        return execute({
            "action": "block",
            "debug": "IP is currently blocked",
            "num_attempts": analysis[1]
        })

    plan_response = plan(ip, analysis)
    return execute(plan_response)


# =============================
# MAIN
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
