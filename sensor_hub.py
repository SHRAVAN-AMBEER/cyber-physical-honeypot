"""
sensor_hub.py — Shared GPIO/Sensor state for Cyber-Physical Decoy System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GPIO wiring:
  DHT-11 DATA  → GPIO 4   (Physical Pin 7)
  MC-38 Switch → GPIO 14  (Physical Pin 8)  ← other wire to GND
  Buzzer   (+) → GPIO 18  (Physical Pin 12) ← (−) to GND
  Red LED  (+) → GPIO 23  (Physical Pin 16) ← (−) via 330Ω to GND
  3.3V         → Physical Pin 1  (DHT-11 VCC)
  GND          → Physical Pin 6  (common ground)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: Call sensor_hub.init() ONCE at startup — from hardware_trap.py only.
           decoy_server.py and decoy_dashboard.py just read get_sensor_data().
"""

import time
import threading
import random

# ── GPIO library detection ────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    import board
    import adafruit_dht
    _dht_device = adafruit_dht.DHT11(board.D4)   # GPIO 4
    RUNNING_ON_PI = True
    print("✅ RPi.GPIO + adafruit_dht loaded — HARDWARE MODE")
except (ImportError, RuntimeError, NotImplementedError):
    RUNNING_ON_PI = False
    _dht_device = None
    print("⚠️  GPIO libs not found — running in SIMULATION mode (PC/dev)")

# ── Pin numbers (BCM numbering) ───────────────────────────────────────────────
DHT_DATA_PIN    = 4    # DHT-11 data
DOOR_SENSOR_PIN = 14   # MC-38 magnetic reed switch
BUZZER_PIN      = 18   # Active buzzer
RED_LED_PIN     = 23   # Red LED

# ── Shared state (read by dashboard + server via get_sensor_data()) ───────────
_lock  = threading.Lock()
_state = {
    "temperature"  : 24.5,
    "humidity"     : 58.0,
    "door_open"    : False,
    "alarm_active" : False,
    "last_updated" : time.strftime("%Y-%m-%d %H:%M:%S"),
}

_gpio_ready = False   # guards against double-init


def get_sensor_data():
    """Thread-safe snapshot of current sensor state."""
    with _lock:
        return dict(_state)


def _set(**kw):
    with _lock:
        _state.update(kw)
        _state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")


# ── GPIO Initialisation (call ONCE from hardware_trap.py) ────────────────────
def init():
    """Set up all GPIO pins. Must be called exactly once."""
    global _gpio_ready
    if _gpio_ready:
        return
    if not RUNNING_ON_PI:
        _gpio_ready = True
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # MC-38: input with internal pull-up.
    #   Door CLOSED  → magnet keeps switch CLOSED  → pin pulled LOW  (0)
    #   Door OPENED  → magnet moves away, switch opens → pin goes HIGH (1)
    GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Buzzer and LED: outputs, start LOW (off)
    GPIO.setup(BUZZER_PIN,  GPIO.OUT)
    GPIO.setup(RED_LED_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN,  GPIO.LOW)
    GPIO.output(RED_LED_PIN, GPIO.LOW)

    _gpio_ready = True
    print(f"✅ GPIO ready  — Door: BCM{DOOR_SENSOR_PIN} | "
          f"Buzzer: BCM{BUZZER_PIN} | LED: BCM{RED_LED_PIN}")


# ── Alarm: Buzzer + LED ───────────────────────────────────────────────────────
def _alarm_worker():
    """Runs in its own thread — keeps alarm on for 10 s then turns off."""
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
    print("🟢 ALARM OFF — Buzzer LOW,  LED LOW")


def trigger_alarm_async():
    """Start the alarm in a background thread (non-blocking)."""
    t = threading.Thread(target=_alarm_worker, daemon=True, name="AlarmThread")
    t.start()


# ── DHT-11 polling loop ───────────────────────────────────────────────────────
def _dht_worker():
    while True:
        if RUNNING_ON_PI:
            try:
                temperature = _dht_device.temperature
                humidity    = _dht_device.humidity
                if temperature is not None and humidity is not None:
                    _set(
                        temperature=round(float(temperature), 1),
                        humidity=round(float(humidity), 1),
                    )
                    print(f"🌡️  DHT-11: {temperature:.1f}°C  💧{humidity:.1f}%")
                else:
                    print("⚠️  DHT-11 read returned None — retrying…")
            except RuntimeError as e:
                # DHT sensors occasionally miss reads — safe to ignore
                print(f"⚠️  DHT-11 miss (normal): {e}")
            except Exception as e:
                print(f"⚠️  DHT-11 error: {e}")
        else:
            # Smooth simulation for PC dev/testing
            with _lock:
                t = _state["temperature"]
                h = _state["humidity"]
            _set(
                temperature=round(t + random.uniform(-0.2, 0.2), 1),
                humidity=round(max(30.0, min(95.0, h + random.uniform(-0.5, 0.5))), 1),
            )
        time.sleep(3)


def start_dht_thread():
    t = threading.Thread(target=_dht_worker, daemon=True, name="DHTThread")
    t.start()
    print("🌡️  DHT-11 polling thread started (every 3 s)")


# ── MC-38 door state helper (used by hardware_trap.py) ───────────────────────
def read_door_pin():
    """
    Returns True if door is OPEN (pin HIGH), False if CLOSED (pin LOW).
    In simulation mode always returns False.
    """
    if RUNNING_ON_PI:
        return bool(GPIO.input(DOOR_SENSOR_PIN))
    return False


def cleanup():
    """Call on exit to release GPIO resources."""
    if RUNNING_ON_PI:
        GPIO.output(BUZZER_PIN,  GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleaned up.")
