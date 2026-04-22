"""
sensor_hub.py - Shared hardware state module for the Cyber-Physical Decoy System.
All other modules import from here to read DHT-11 data and control GPIO outputs.

Raspberry Pi GPIO Connections:
  DHT-11 Data Pin  → GPIO 4  (Physical Pin 7)
  MC-38 Door Switch → GPIO 14 (Physical Pin 8)  [other leg to GND]
  Active Buzzer (+) → GPIO 18 (Physical Pin 12) [(-) to GND]
  Red LED (+ anode) → GPIO 23 (Physical Pin 16) [via 330Ω resistor to GND]
  3.3V              → Physical Pin 1             [DHT-11 VCC]
  GND               → Physical Pin 6             [common ground]
"""

import time
import threading

# ── Try to import real GPIO libs; fall back to mock for development on PC ──
try:
    import Adafruit_DHT
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except (ImportError, RuntimeError):
    RUNNING_ON_PI = False
    print("⚠️  GPIO/DHT libs not found – running in SIMULATION mode.")

# ── Pin Configuration ────────────────────────────────────────────────────────
DHT_SENSOR_TYPE  = 11          # DHT-11
DHT_DATA_PIN     = 4           # GPIO 4
DOOR_SENSOR_PIN  = 14          # GPIO 14  (MC-38)
BUZZER_PIN       = 18          # GPIO 18  (Active Buzzer)
RED_LED_PIN      = 23          # GPIO 23  (Red LED)

# ── Shared sensor state (thread-safe) ───────────────────────────────────────
_lock = threading.Lock()
_state = {
    "temperature": 24.5,
    "humidity": 58.0,
    "door_open": False,
    "alarm_active": False,
    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
}


def get_sensor_data():
    """Return a copy of the current sensor state (thread-safe)."""
    with _lock:
        return dict(_state)


def _update_state(**kwargs):
    with _lock:
        _state.update(kwargs)
        _state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")


# ── GPIO Setup ───────────────────────────────────────────────────────────────
def setup_gpio():
    if not RUNNING_ON_PI:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUZZER_PIN,      GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(RED_LED_PIN,     GPIO.OUT, initial=GPIO.LOW)


def trigger_alarm():
    """Activate buzzer + red LED for 10 seconds."""
    _update_state(alarm_active=True)
    print("🚨 ALARM TRIGGERED — Buzzer ON, Red LED ON")
    if RUNNING_ON_PI:
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
    time.sleep(10)
    if RUNNING_ON_PI:
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.LOW)
    _update_state(alarm_active=False)
    print("✅ Alarm cleared.")


def trigger_alarm_async():
    """Run alarm in a background thread so it doesn't block."""
    t = threading.Thread(target=trigger_alarm, daemon=True)
    t.start()


# ── DHT-11 Polling Loop ──────────────────────────────────────────────────────
def _dht_loop():
    import random
    while True:
        if RUNNING_ON_PI:
            humidity, temperature = Adafruit_DHT.read_retry(
                Adafruit_DHT.DHT11, DHT_DATA_PIN
            )
            if humidity is not None and temperature is not None:
                _update_state(temperature=round(temperature, 1),
                              humidity=round(humidity, 1))
        else:
            # Simulate realistic fluctuations in dev/test mode
            with _lock:
                base_t = _state["temperature"]
                base_h = _state["humidity"]
            _update_state(
                temperature=round(base_t + random.uniform(-0.3, 0.3), 1),
                humidity=round(max(30, min(90, base_h + random.uniform(-1, 1))), 1),
            )
        time.sleep(3)


def start_dht_thread():
    t = threading.Thread(target=_dht_loop, daemon=True)
    t.start()
    print("🌡️  DHT-11 polling thread started.")
