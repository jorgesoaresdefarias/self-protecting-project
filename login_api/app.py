from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv
import smtplib
import random
from email.mime.text import MIMEText
load_dotenv()

app = Flask(__name__)

# Usuários com senha e e-mail
users = {
    "admin": {"password": "123", "email": "jsfj@cin.ufpe.br"},
    "user": {"password": "abc", "email": "user@email.com"}
}

RECAPTCHA_SECRET = os.getenv("SECRET_KEY")
RECAPTCHA_SITE = os.getenv("SITE_KEY")
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

# Armazenamento temporário dos códigos 2FA por IP
twofa_codes = {}

def send_2fa_email(recipient_email, ip):
    code = str(random.randint(100000, 999999))
    twofa_codes[ip] = code  # Salva código temporariamente por IP

    subject = "Seu código de verificação"
    body = f"Seu código de verificação é: {code}"

    # Constrói o e-mail corretamente como MIME
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = recipient_email

    with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())

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
        if not code:
            user_email = users.get(username, {}).get("email")
            if not user_email:
                return jsonify({"message": "Usuário sem e-mail cadastrado"}), 400
            send_2fa_email(user_email, client_ip)
            return jsonify({"message": "Código 2FA enviado por e-mail.", "require_2fa_code": True}), 401

        expected_code = twofa_codes.get(client_ip)
        if code != expected_code:
            return jsonify({"message": "Código 2FA inválido", "require_2fa_code": True}), 401

    # Autenticação
    if username in users and users[username]["password"] == password:
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
    print("entrou")
    print(token)
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
