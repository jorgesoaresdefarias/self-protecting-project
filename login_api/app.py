from flask import Flask, request, jsonify, render_template
import requests
import os

app = Flask(__name__)

users = {
    "admin": "123",
    "user": "abc"
}

RECAPTCHA_SECRET = os.getenv("SECRET_KEY")
RECAPTCHA_SITE = os.getenv("SITE_KEY")
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

@app.route("/")
def index():
    return render_template("site.html", site_key=RECAPTCHA_SITE)
    
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    client_ip = request.remote_addr

    # Consulta ao sistema gerenciador
    response = requests.post("http://mape_manager:5001/evaluate", json={
        "ip": client_ip,
        "username": username
    })
    decision = response.json()
    action = decision.get("action")
    show_captcha = decision.get("show_captcha", False)

    if action == "block":
        return jsonify({"message": "IP bloqueado", "show_captcha": False}), 403

    if action == "captcha":
        captcha_token = data.get("captcha_token")
        if not captcha_token:
            return jsonify({"message": "CAPTCHA necessário", "show_captcha": True}), 401
        if not verify_captcha(captcha_token):
            return jsonify({"message": "CAPTCHA inválido", "show_captcha": True}), 401

    if action == "2fa":
        code = data.get("2fa_code")
        if code != "0000":
            return jsonify({"message": "2FA necessário. Use código '0000'.", "show_captcha": show_captcha}), 401

    # Autenticação
    if username in users and users[username] == password:
        requests.post("http://mape_manager:5001/register_attempt", json={
            "ip": client_ip,
            "username": username,
            "success": True
        })
        return jsonify({"message": "Login bem-sucedido", "show_captcha": False}), 200
    else:
        requests.post("http://mape_manager:5001/register_attempt", json={
            "ip": client_ip,
            "username": username,
            "success": False
        })
        return jsonify({"message": "Login falhou", "show_captcha": show_captcha}), 401

def verify_captcha(token):
    print('entrou')
    print(token)
    import requests
    if not token:
        print("Captcha token vazio!")
        return False

    payload = {
        'secret': RECAPTCHA_SECRET,
        'response': token
    }
    r = requests.post(RECAPTCHA_VERIFY_URL, data=payload)
    result = r.json()
    return result.get("success", False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)