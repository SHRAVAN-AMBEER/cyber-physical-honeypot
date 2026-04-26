"""
unified_server.py - Single Flask app serving all honeypot pages
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Routes:
  GET  /              → NOC Dashboard (live DHT-11 data)
  GET  /login         → Fake enterprise login page
  POST /login         → Capture credentials → Telegram + alarm
  GET  /emergency     → Social engineering panic page
  POST /emergency     → Capture credentials → Telegram
  GET  /api/sensors   → Live sensor JSON
  GET  /api/events    → Security events log JSON
  POST /api/action    → Admin action trap → Telegram + alarm

Run on port 8080. Only one process to manage.
"""

import datetime
import json
import threading

from flask import Flask, render_template, request, jsonify
from decoy_alert import send_telegram_alert
from sensor_hub import request_alarm, get_sensor_data

app = Flask(__name__)

# ── Shared event log ──────────────────────────────────────────────────────────
_events = []
_events_lock = threading.Lock()

def log_event(source, detail, severity="WARNING"):
    entry = {
        "time"    : datetime.datetime.now().strftime("%H:%M:%S"),
        "source"  : source,
        "detail"  : detail,
        "severity": severity,
    }
    with _events_lock:
        _events.insert(0, entry)
        if len(_events) > 100:
            _events.pop()
    return entry

def _alert_and_alarm(msg, source, detail, severity="WARNING", alarm=False):
    """Send Telegram in background + optionally trigger physical alarm."""
    def _run():
        send_telegram_alert(msg)
        if alarm:
            request_alarm()
    threading.Thread(target=_run, daemon=True).start()
    log_event(source, detail, severity)


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    ip       = request.remote_addr
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _alert_and_alarm(
        f"👁️  DASHBOARD ACCESSED\n\n🕐 Time : {time_now}\n🌍 IP   : {ip}",
        ip, "Dashboard accessed", "INFO"
    )
    print(f"[VISIT] {ip} → Dashboard")
    return render_template('dashboard.html')


# ── Login honeypot ────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip   = request.remote_addr
        user = request.form.get('username', '')
        pwd  = request.form.get('password', '')
        now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _alert_and_alarm(
            f"🚨 LOGIN TRAP SPRUNG 🚨\n\n🕐 Time    : {now}\n🌍 IP      : {ip}\n👤 Username: {user}\n🔑 Password: {pwd}\n\nBuzzer + LED activated.",
            ip, f"Login attempt: {user}", "CRITICAL", alarm=True
        )
        print(f"[TRAP] Login from {ip} — {user} / {pwd}")
        return "<h1>Error 503: Database Connection Timeout. Please try again later.</h1>", 503

    print(f"[VISIT] {request.remote_addr} → Login page")
    return render_template('login.html')


# ── Social engineering emergency page ─────────────────────────────────────────
@app.route('/emergency', methods=['GET', 'POST'])
def emergency():
    if request.method == 'POST':
        ip   = request.remote_addr
        user = request.form.get('username', '')
        pwd  = request.form.get('password', '')
        now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _alert_and_alarm(
            f"🎣 SOCIAL ENGINEERING TRAP SPRUNG 🎣\n\nAttacker panicked at fake humidity warning!\n\n🕐 Time     : {now}\n🌍 IP       : {ip}\n👤 Username : {user}\n🔑 Password : {pwd}",
            ip, f"Emergency override attempt: {user}", "CRITICAL"
        )
        print(f"[TRAP] Emergency override from {ip} — {user} / {pwd}")
        return "<h1>Error 503: Subsystem Unreachable. Connection Terminated.</h1>", 503

    print(f"[VISIT] {request.remote_addr} → Emergency page")
    return render_template('emergency.html')


# ── API ───────────────────────────────────────────────────────────────────────
@app.route('/api/sensors')
def api_sensors():
    return jsonify(get_sensor_data())


@app.route('/api/events')
def api_events():
    with _events_lock:
        return jsonify(list(_events))


@app.route('/api/action', methods=['POST'])
def api_action():
    ip     = request.remote_addr
    action = request.json.get('action', 'unknown') if request.is_json else 'unknown'
    now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _alert_and_alarm(
        f"🚨 ADMIN ACTION ATTEMPT 🚨\n\n🕐 Time  : {now}\n🌍 IP    : {ip}\n⚙️  Action: {action}\n\nBuzzer + LED activated.",
        ip, f"Admin action: {action}", "CRITICAL", alarm=True
    )
    print(f"[ALARM] Admin action '{action}' from {ip}")
    return jsonify({"status": "executing", "message": "Command queued..."})


if __name__ == '__main__':
    print("🖥️  Starting Unified Honeypot Server on port 8080...")
    print("    http://<pi-ip>:8080/           → NOC Dashboard")
    print("    http://<pi-ip>:8080/login      → Login Trap")
    print("    http://<pi-ip>:8080/emergency  → Social Engineering Trap\n")
    app.run(host='0.0.0.0', port=8080, debug=False)
