"""
sensor_hub.py — Hardware state for Cyber-Physical Decoy System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN: Only hardware_trap.py owns GPIO. It writes state to a
shared JSON file (/tmp/honeypot_state.json) every 3 seconds.
decoy_server.py and decoy_dashboard.py READ from that file.
This avoids all GPIO conflicts between processes.

GPIO wiring (BCM numbering):
  DHT-11 DATA  → GPIO 4   (Physical Pin 7)
  MC-38 Switch → GPIO 17  (Physical Pin 11) ← ⚠️ NOT GPIO14 (that's UART)
  Buzzer   (+) → GPIO 18  (Physical Pin 12)  (−) → GND
  Red LED  (+) → GPIO 23  (Physical Pin 16)  via 330Ω → GND
  3.3V         → Physical Pin 1  (DHT-11 VCC)
  GND          → Physical Pin 6 / 9 / 14
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import os
import time
import threading
import random

# Shared state file — written by hardware_trap, read by server/dashboard
STATE_FILE = "/tmp/honeypot_state.json"

# ── Pin numbers (BCM) ────────────────────────────────────────────────────────
DHT_DATA_PIN    = 4    # GPIO 4  — DHT-11 data
DOOR_SENSOR_PIN = 17   # GPIO 17 — MC-38 (⚠️ GPIO14 is UART — do NOT use)
BUZZER_PIN      = 18   # GPIO 18 — Active buzzer
RED_LED_PIN     = 23   # GPIO 23 — Red LED

# ── Default in-process state (used only by hardware_trap process) ────────────
_lock  = threading.Lock()
_state = {
    "temperature"  : 24.5,
    "humidity"     : 58.0,
    "door_open"    : False,
    "alarm_active" : False,
    "last_updated" : time.strftime("%Y-%m-%d %H:%M:%S"),
}

# ── GPIO / DHT detection ─────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except (ImportError, RuntimeError):
    GPIO = None
    RUNNING_ON_PI = False

# DHT device created lazily inside _dht_worker — not at import time
_dht_device = None


# ── State I/O ────────────────────────────────────────────────────────────────
def _write_state():
    """Persist current state to JSON so other processes can read it."""
    with _lock:
        data = dict(_state)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def get_sensor_data():
    """
    Returns sensor state.
    - In hardware_trap process: reads from in-memory _state.
    - In server/dashboard processes: reads from the shared JSON file.
    """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    with _lock:
        return dict(_state)


def _set(**kw):
    with _lock:
        _state.update(kw)
        _state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_state()


# ── GPIO Setup (called once from hardware_trap.py only) ─────────────────────
_gpio_ready = False

def init():
    global _gpio_ready
    if _gpio_ready:
        return
    if not RUNNING_ON_PI:
        _gpio_ready = True
        print("⚠️  Simulation mode — no real GPIO")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # MC-38 on GPIO 17 with pull-up
    # Door CLOSED → switch closed → pin LOW
    # Door OPENED → switch opens → pin HIGH (pull-up wins)
    GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Buzzer and LED — outputs, start LOW (off)
    GPIO.setup(BUZZER_PIN,  GPIO.OUT)
    GPIO.setup(RED_LED_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN,  GPIO.LOW)
    GPIO.output(RED_LED_PIN, GPIO.LOW)

    _gpio_ready = True
    print(f"✅ GPIO ready — Door: BCM{DOOR_SENSOR_PIN} | "
          f"Buzzer: BCM{BUZZER_PIN} | LED: BCM{RED_LED_PIN}")


# ── Alarm ────────────────────────────────────────────────────────────────────
def _alarm_worker():
    _set(alarm_active=True)
    print("🔴 ALARM ON  — Buzzer HIGH, LED HIGH")
    if RUNNING_ON_PI:
        GPIO.output(BUZZER_PIN,  GPIO.HIGH)
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
    time.sleep(10)
    if RUNNING_ON_PI:
        GPIO.output(BUZZER_PIN,  GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.LOW)
    _set(alarm_active=False)
    print("🟢 ALARM OFF — Buzzer LOW, LED LOW")


def trigger_alarm_async():
    threading.Thread(target=_alarm_worker, daemon=True, name="AlarmThread").start()


# ── DHT-11 polling (hardware_trap process only) ──────────────────────────────
def _dht_worker():
    global _dht_device
    if RUNNING_ON_PI:
        try:
            import board
            import adafruit_dht
            _dht_device = adafruit_dht.DHT11(board.D4)
            print("✅ DHT-11 device initialised on GPIO 4")
        except Exception as e:
            print(f"❌ DHT-11 init failed: {e}")
            _dht_device = None

    while True:
        if RUNNING_ON_PI and _dht_device:
            try:
                t = _dht_device.temperature
                h = _dht_device.humidity
                if t is not None and h is not None:
                    _set(temperature=round(float(t), 1),
                         humidity=round(float(h), 1))
                    print(f"🌡️  {t:.1f}°C  💧{h:.1f}%")
            except RuntimeError:
                pass   # DHT-11 occasional misread — normal, just skip
            except Exception as e:
                print(f"⚠️  DHT error: {e}")
        else:
            # Simulation
            with _lock:
                t = _state["temperature"]
                h = _state["humidity"]
            _set(
                temperature=round(t + random.uniform(-0.2, 0.2), 1),
                humidity=round(max(30.0, min(95.0, h + random.uniform(-0.5, 0.5))), 1),
            )
        time.sleep(3)


def start_dht_thread():
    threading.Thread(target=_dht_worker, daemon=True, name="DHTThread").start()
    print("🌡️  DHT-11 polling thread started")


# ── Door pin helper ───────────────────────────────────────────────────────────
def read_door_pin():
    if RUNNING_ON_PI:
        return bool(GPIO.input(DOOR_SENSOR_PIN))
    return False


# ── Cleanup ───────────────────────────────────────────────────────────────────
def cleanup():
    if RUNNING_ON_PI:
        GPIO.output(BUZZER_PIN,  GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.LOW)
        GPIO.cleanup()
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("GPIO cleaned up.")
