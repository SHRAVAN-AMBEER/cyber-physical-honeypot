"""
decoy_dashboard.py - Cyber-Physical Decoy Data Center Dashboard (NEW)
Presents a convincing, interactive "Data Center Monitoring" dashboard
powered by real DHT-11 sensor readings from the Raspberry Pi.

Every visitor IP is logged and triggers a Telegram alert.
Any "admin action" attempted triggers buzzer + LED.

Run on port 8080:  python decoy_dashboard.py
"""

import datetime
import json
import random
import threading
import time

from flask import Flask, render_template, jsonify, request

from decoy_alert import send_telegram_alert
from sensor_hub import setup_gpio, start_dht_thread, trigger_alarm_async, get_sensor_data

app = Flask(__name__)

# ── Start hardware ────────────────────────────────────────────────────────────
setup_gpio()
start_dht_thread()

# ── In-memory event log ───────────────────────────────────────────────────────
_events = []
_events_lock = threading.Lock()

def log_event(source, detail, severity="WARNING"):
    entry = {
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "source": source,
        "detail": detail,
        "severity": severity,
    }
    with _events_lock:
        _events.insert(0, entry)
        if len(_events) > 50:
            _events.pop()
    return entry

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    visitor_ip = request.remote_addr
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alert_msg = (
        f"👁️  DASHBOARD ACCESS DETECTED\n"
        f"Someone is viewing the Decoy Dashboard!\n\n"
        f"🕐 Time : {time_now}\n"
        f"🌍 IP   : {visitor_ip}"
    )
    send_telegram_alert(alert_msg)
    log_event(visitor_ip, "Dashboard accessed", "INFO")
    print(f"[DASHBOARD] Visitor from {visitor_ip}")

    return render_template('dashboard.html')


@app.route('/api/sensors')
def api_sensors():
    return jsonify(get_sensor_data())


@app.route('/api/events')
def api_events():
    with _events_lock:
        return jsonify(list(_events))


@app.route('/api/action', methods=['POST'])
def api_action():
    """Any admin action (shutdown, reboot, etc.) triggers the alarm."""
    visitor_ip = request.remote_addr
    action = request.json.get('action', 'unknown') if request.is_json else 'unknown'
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alert_msg = (
        f"🚨 DASHBOARD ATTACK ATTEMPT 🚨\n"
        f"Admin Action Triggered on Decoy!\n\n"
        f"🕐 Time  : {time_now}\n"
        f"🌍 IP    : {visitor_ip}\n"
        f"⚙️  Action: {action}\n\n"
        f"Buzzer + Red LED activated."
    )
    send_telegram_alert(alert_msg)
    trigger_alarm_async()
    log_event(visitor_ip, f"Admin action attempted: {action}", "CRITICAL")
    print(f"[ALARM] Admin action '{action}' from {visitor_ip}. Alarm triggered!")

    return jsonify({"status": "executing", "message": "Command queued..."})


if __name__ == '__main__':
    print("🖥️  Starting Decoy Data Center Dashboard on port 8080...")
    print("    Open http://<raspberry-pi-ip>:8080 to view\n")
    app.run(host='0.0.0.0', port=8080, debug=False)
