"""
decoy_server.py - Cyber Honeypot Login Trap (UPDATED)
Presents a fake "Industrial Smart Monitor" login page.
Any login attempt → Telegram alert + buzzer + red LED.

Routes:
  GET  /           → Fake login page (honeypot)
  POST /           → Capture credentials, trigger alarm, return 503
  GET  /api/sensors → Live DHT-11 JSON (used by dashboard)
"""

import datetime
import json
from flask import Flask, request, render_template_string, jsonify

from decoy_alert import send_telegram_alert
from sensor_hub import setup_gpio, start_dht_thread, trigger_alarm_async, get_sensor_data

app = Flask(__name__)

# ── Start hardware on import ─────────────────────────────────────────────────
setup_gpio()
start_dht_thread()

# ── Honeypot HTML ────────────────────────────────────────────────────────────
FAKE_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>DataCore Systems — Secure Access Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0e1a;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .bg-grid {
            position: fixed; inset: 0;
            background-image:
                linear-gradient(rgba(0,200,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,200,255,0.03) 1px, transparent 1px);
            background-size: 40px 40px;
        }
        .card {
            position: relative;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(0,200,255,0.2);
            border-radius: 16px;
            padding: 48px 40px;
            width: 440px;
            backdrop-filter: blur(20px);
            box-shadow: 0 0 60px rgba(0,200,255,0.08), 0 0 0 1px rgba(0,200,255,0.1);
        }
        .logo { text-align: center; margin-bottom: 8px; }
        .logo-icon {
            width: 56px; height: 56px;
            background: linear-gradient(135deg, #00c8ff, #0066ff);
            border-radius: 14px;
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 26px; margin-bottom: 12px;
            box-shadow: 0 0 20px rgba(0,200,255,0.4);
        }
        h1 { color: #e0f4ff; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }
        .subtitle { color: #5a8aaa; font-size: 13px; margin-top: 4px; }
        .divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0,200,255,0.3), transparent);
            margin: 24px 0;
        }
        .sys-status {
            display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap;
        }
        .badge {
            font-size: 11px; padding: 4px 10px; border-radius: 20px;
            display: flex; align-items: center; gap: 5px; font-weight: 600;
        }
        .badge-green { background: rgba(0,255,120,0.1); color: #00ff78; border: 1px solid rgba(0,255,120,0.3); }
        .badge-yellow { background: rgba(255,200,0,0.1); color: #ffc800; border: 1px solid rgba(255,200,0,0.3); }
        .dot { width: 6px; height: 6px; border-radius: 50%; }
        .dot-green { background: #00ff78; box-shadow: 0 0 6px #00ff78; animation: pulse 1.5s infinite; }
        .dot-yellow { background: #ffc800; }
        @keyframes pulse { 0%, 100% { opacity:1; } 50% { opacity:0.4; } }
        label { color: #8aafcc; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 6px; }
        input {
            width: 100%; padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(0,200,255,0.2);
            border-radius: 8px; color: #e0f4ff; font-size: 14px;
            outline: none; transition: all 0.2s;
            margin-bottom: 16px;
        }
        input:focus { border-color: rgba(0,200,255,0.6); box-shadow: 0 0 0 3px rgba(0,200,255,0.1); }
        input::placeholder { color: #3a5a6a; }
        button {
            width: 100%; padding: 13px;
            background: linear-gradient(135deg, #0066ff, #00c8ff);
            border: none; border-radius: 8px;
            color: white; font-size: 14px; font-weight: 700;
            cursor: pointer; letter-spacing: 0.5px;
            transition: all 0.2s;
            box-shadow: 0 4px 20px rgba(0,150,255,0.3);
        }
        button:hover { transform: translateY(-1px); box-shadow: 0 6px 25px rgba(0,150,255,0.5); }
        .footer { text-align: center; margin-top: 20px; color: #2a4a5a; font-size: 11px; }
        .warning-banner {
            background: rgba(255,60,60,0.08);
            border: 1px solid rgba(255,60,60,0.2);
            border-radius: 8px; padding: 10px 14px;
            color: #ff6060; font-size: 12px;
            margin-bottom: 20px; display: flex; align-items: center; gap: 8px;
        }
    </style>
</head>
<body>
<div class="bg-grid"></div>
<div class="card">
    <div class="logo">
        <div class="logo-icon">🏢</div>
        <h1>DataCore Systems</h1>
        <p class="subtitle">Enterprise Infrastructure Management</p>
    </div>
    <div class="divider"></div>
    <div class="sys-status">
        <span class="badge badge-green"><span class="dot dot-green"></span>SYSTEMS ONLINE</span>
        <span class="badge badge-yellow"><span class="dot dot-yellow"></span>RESTRICTED ACCESS</span>
    </div>
    <div class="warning-banner">
        ⚠️ Unauthorized access attempts are logged and prosecuted.
    </div>
    <form method="POST" action="/">
        <label for="username">Administrator ID</label>
        <input type="text" id="username" name="username" placeholder="admin@datacore.internal" required autocomplete="off">
        <label for="password">Access Passphrase</label>
        <input type="password" id="password" name="password" placeholder="••••••••••••" required autocomplete="off">
        <button type="submit" id="login-btn">🔐 Authenticate & Enter</button>
    </form>
    <div class="footer">DataCore v4.2.1 · TLS 1.3 · ISO 27001 Certified</div>
</div>
</body>
</html>
"""


@app.route('/', methods=['GET', 'POST'])
def honeypot_login():
    if request.method == 'POST':
        hacker_ip   = request.remote_addr
        attempted_user = request.form.get('username', '')
        attempted_pass = request.form.get('password', '')
        time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        alert_msg = (
            f"🚨 CYBER ALERT 🚨\n"
            f"Web Honeypot Login Attempt!\n\n"
            f"🕐 Time    : {time_now}\n"
            f"🌍 IP      : {hacker_ip}\n"
            f"👤 Username: {attempted_user}\n"
            f"🔑 Password: {attempted_pass}\n\n"
            f"Buzzer + Red LED activated."
        )
        send_telegram_alert(alert_msg)
        trigger_alarm_async()
        print(f"[HONEYPOT] Intrusion from {hacker_ip} logged. Alarm triggered.")

        return "<h1>Error 503: Database Connection Timeout. Please try again later.</h1>", 503

    return render_template_string(FAKE_PAGE_HTML)


@app.route('/api/sensors')
def api_sensors():
    """Live sensor JSON — consumed by the decoy dashboard."""
    return jsonify(get_sensor_data())


if __name__ == '__main__':
    print("🕸️  Starting Cyber-Physical Decoy Web Honeypot on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)