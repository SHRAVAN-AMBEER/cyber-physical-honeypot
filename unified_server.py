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

from flask import Flask, render_template, request, jsonify, redirect, url_for
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
        f"👁️  CBIT DASHBOARD ACCESSED\n\n🕐 Time : {time_now}\n🌍 IP   : {ip}",
        ip, "CBIT Dashboard accessed", "INFO"
    )
    print(f"[VISIT] {ip} → Dashboard")
    return render_template('dashboard.html')


# ── Login honeypot ───────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip   = request.remote_addr
        user = request.form.get('username', 'admin')
        pwd  = request.form.get('password', '')
        now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Log credentials + send Telegram
        _alert_and_alarm(
            f"🚨 CBIT LOGIN CREDENTIALS CAPTURED 🚨\n\n🕐 Time    : {now}\n🌍 IP      : {ip}\n👤 Username: {user}\n🔑 Password: {pwd}\n\nAttacker redirected to CBIT Admin Panel trap.",
            ip, f"CBIT Login captured: {user}", "CRITICAL", alarm=False
        )
        print(f"[TRAP] Login from {ip} — {user} / {pwd} → redirecting to /admin")
        # Accept credentials and redirect to admin panel trap
        return redirect(url_for('admin_panel', user=user))

    print(f"[VISIT] {request.remote_addr} → Login page")
    return render_template('login.html')


# ── Admin panel (the real trap) ────────────────────────────────────────────────────
@app.route('/admin')
def admin_panel():
    ip   = request.remote_addr
    user = request.args.get('user', 'Administrator')
    now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _alert_and_alarm(
        f"🕓 ATTACKER REACHED CBIT ADMIN PANEL 🕓\n\n🕐 Time : {now}\n🌍 IP   : {ip}\n👤 User : {user}\n\nWaiting for them to press a vault control button...",
        ip, f"CBIT Admin panel accessed by {user}", "CRITICAL"
    )
    print(f"[ADMIN] {ip} ({user}) reached the admin panel trap")
    return render_template('admin.html')


# ── Social engineering emergency page ─────────────────────────────────────────
@app.route('/emergency', methods=['GET', 'POST'])
def emergency():
    if request.method == 'POST':
        ip   = request.remote_addr
        user = request.form.get('username', '')
        pwd  = request.form.get('password', '')
        now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _alert_and_alarm(
            f"🎣 CBIT MANUAL OVERRIDE ATTEMPTED 🎣\n\nAttacker submitted emergency override credentials for the Exam Vault!\n\n🕐 Time     : {now}\n🌍 IP       : {ip}\n👤 Username : {user}\n🔑 Password : {pwd}\n\n🔊 Buzzer ON | 🔴 LED ON",
            ip, f"CBIT Emergency override attempt: {user}", "CRITICAL", alarm=True
        )
        print(f"[TRAP] Emergency override from {ip} — {user} / {pwd}")
        return "<h1>Error 503: Subsystem Unreachable. Connection Terminated.</h1>", 503

    # GET — log the visit + Telegram only, no buzzer/LED
    ip  = request.remote_addr
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _alert_and_alarm(
        f"⚠️  CBIT SYSTEM STATUS PAGE ACCESSED\n\nSomeone is viewing the Emergency Exam Vault Status page!\n\n🕐 Time : {now}\n🌍 IP   : {ip}",
        ip, "CBIT System Status accessed", "WARNING", alarm=False
    )
    print(f"[VISIT] {ip} → Emergency/System Status page")
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
    data   = request.json if request.is_json else {}
    action = data.get('action', 'unknown')
    user   = data.get('user', 'unknown')
    now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _alert_and_alarm(
        f"🚨 CBIT VAULT ACTION TRIGGERED 🚨\n\n🕐 Time  : {now}\n🌍 IP    : {ip}\n👤 User  : {user}\n⚙️  Action: {action}\n\n🔊 Buzzer ON | 🔴 LED ON",
        ip, f"Vault action by {user}: {action}", "CRITICAL", alarm=True
    )
    print(f"[ALARM] 🚨 Admin action '{action}' by '{user}' from {ip}")
    return jsonify({"status": "executing", "message": "Command queued..."})


if __name__ == '__main__':
    print("🖥️  Starting CBIT Exam Vault Honeypot on port 8080...")
    print("    http://<pi-ip>:8080/           → CBIT Dashboard")
    print("    http://<pi-ip>:8080/login      → Login Trap → Admin Panel")
    print("    http://<pi-ip>:8080/emergency  → System Status Trap\n")
    app.run(host='0.0.0.0', port=8080, debug=False)
