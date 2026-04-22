"""
sensor_hub.py — Hardware state for Cyber-Physical Decoy System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uses gpiozero (pre-installed, works on all Pi OS versions including Bookworm).
RPi.GPIO is NOT used here — it has known edge-detection bugs on Bookworm.

GPIO wiring (BCM numbering):
  DHT-11 DATA  → GPIO 4   (Physical Pin 7)
  MC-38 Switch → GPIO 17  (Physical Pin 11)  other wire → GND
  Buzzer   (+) → GPIO 18  (Physical Pin 12)  (−) → GND
  Red LED  (+) → GPIO 23  (Physical Pin 16)  via 330Ω → GND
  3.3V         → Physical Pin 1  (DHT-11 VCC)
  GND          → Physical Pin 6 / 9

Only hardware_trap.py calls init() and start_dht_thread().
Server and dashboard just call get_sensor_data() which reads a shared JSON file.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import os
import time
import threading
import random

STATE_FILE = "/tmp/honeypot_state.json"

# ── Pin numbers (BCM) ─────────────────────────────────────────────────────────
DHT_DATA_PIN    = 4
DOOR_SENSOR_PIN = 17
BUZZER_PIN      = 18
RED_LED_PIN     = 23

# ── In-process state (hardware_trap only) ─────────────────────────────────────
_lock  = threading.Lock()
_state = {
    "temperature"  : 24.5,
    "humidity"     : 58.0,
    "door_open"    : False,
    "alarm_active" : False,
    "last_updated" : time.strftime("%Y-%m-%d %H:%M:%S"),
}

# ── gpiozero device handles (set inside init()) ───────────────────────────────
_buzzer  = None
_led     = None
_dht_dev = None

# ── Detect if running on Pi ───────────────────────────────────────────────────
try:
    from gpiozero import LED as GZLED, Button as GZButton, Device
    from gpiozero.pins.lgpio import LGPIOFactory
    Device.pin_factory = LGPIOFactory()   # use lgpio backend (best on Bookworm)
    RUNNING_ON_PI = True
except Exception:
    try:
        from gpiozero import LED as GZLED, Button as GZButton
        RUNNING_ON_PI = True
    except Exception:
        RUNNING_ON_PI = False


# ── State helpers ─────────────────────────────────────────────────────────────
def _write_state():
    with _lock:
        data = dict(_state)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _set(**kw):
    with _lock:
        _state.update(kw)
        _state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_state()


def get_sensor_data():
    """Read from shared JSON (all processes) or fallback to in-memory state."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    with _lock:
        return dict(_state)


# ── GPIO Init (hardware_trap.py only) ─────────────────────────────────────────
_gpio_ready = False


def init():
    global _gpio_ready, _buzzer, _led
    if _gpio_ready:
        return

    if not RUNNING_ON_PI:
        _gpio_ready = True
        print("⚠️  Simulation mode — no real GPIO")
        return

    try:
        _buzzer = GZLED(BUZZER_PIN)    # active buzzer acts like LED (on/off)
        _led    = GZLED(RED_LED_PIN)
        _buzzer.off()
        _led.off()
        _gpio_ready = True
        print(f"✅ gpiozero ready — Buzzer: BCM{BUZZER_PIN} | LED: BCM{RED_LED_PIN}")
    except Exception as e:
        print(f"❌ GPIO init error: {e}")


def get_door_button():
    """
    Returns a gpiozero Button for the MC-38 door sensor.
    Called from hardware_trap.py to attach when_released callback.

    MC-38 is Normally Closed (NC):
      Door CLOSED → magnet holds switch shut  → circuit complete → pin LOW  → button 'pressed'
      Door OPENED → magnet moves away         → circuit breaks   → pin HIGH → button 'released'
    So 'when_released' fires when the door opens.
    """
    if not RUNNING_ON_PI:
        return None
    try:
        btn = GZButton(DOOR_SENSOR_PIN, pull_up=True, bounce_time=0.3)
        print(f"✅ Door sensor ready — MC-38 on BCM{DOOR_SENSOR_PIN} (Physical Pin 11)")
        return btn
    except Exception as e:
        print(f"❌ Door sensor init error: {e}")
        return None


# ── Alarm: Buzzer + LED ───────────────────────────────────────────────────────
def _alarm_worker():
    _set(alarm_active=True)
    print("🔴 ALARM ON  — Buzzer HIGH, LED HIGH")
    if RUNNING_ON_PI and _buzzer and _led:
        _buzzer.on()
        _led.on()
    time.sleep(10)
    if RUNNING_ON_PI and _buzzer and _led:
        _buzzer.off()
        _led.off()
    _set(alarm_active=False)
    print("🟢 ALARM OFF — Buzzer LOW, LED LOW")


def trigger_alarm_async():
    threading.Thread(target=_alarm_worker, daemon=True, name="AlarmThread").start()


# ── DHT-11 polling (hardware_trap process only) ───────────────────────────────
def _dht_worker():
    global _dht_dev
    if RUNNING_ON_PI:
        try:
            import board
            import adafruit_dht
            _dht_dev = adafruit_dht.DHT11(board.D4)
            print("✅ DHT-11 ready on GPIO 4")
        except Exception as e:
            print(f"❌ DHT-11 init failed: {e}")
            _dht_dev = None

    while True:
        if RUNNING_ON_PI and _dht_dev:
            try:
                t = _dht_dev.temperature
                h = _dht_dev.humidity
                if t is not None and h is not None:
                    _set(temperature=round(float(t), 1),
                         humidity=round(float(h), 1))
                    print(f"🌡️  {t:.1f}°C  💧{h:.1f}%")
            except RuntimeError:
                pass   # occasional misread is normal for DHT-11
            except Exception as e:
                print(f"⚠️  DHT error: {e}")
        else:
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


# ── Cleanup ───────────────────────────────────────────────────────────────────
def cleanup():
    if RUNNING_ON_PI:
        if _buzzer:
            _buzzer.off()
            _buzzer.close()
        if _led:
            _led.off()
            _led.close()
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("✅ Cleanup done.")
