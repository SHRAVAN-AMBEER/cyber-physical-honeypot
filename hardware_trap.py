"""
hardware_trap.py - Physical Security Monitor (UPDATED)
Monitors the MC-38 magnetic door sensor on the decoy cardboard data center.
When the door is opened:
  1. Triggers the Active Buzzer (GPIO 18)
  2. Turns on the Red LED   (GPIO 23)
  3. Sends a Telegram alert to your phone

Depends on: sensor_hub.py, decoy_alert.py
"""

import time
from signal import pause

from sensor_hub import (
    setup_gpio,
    start_dht_thread,
    trigger_alarm_async,
    get_sensor_data,
    RUNNING_ON_PI,
    DOOR_SENSOR_PIN,
)
from decoy_alert import send_telegram_alert

# ── Setup ────────────────────────────────────────────────────────────────────
setup_gpio()
start_dht_thread()


def handle_door_open():
    """Called the instant the MC-38 circuit breaks (door opened)."""
    data = get_sensor_data()
    time_now = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{time_now}] ⚠️  SENSOR TRIPPED: Decoy data center door opened!")

    # Build Telegram alert
    alert_msg = (
        f"🚨 PHYSICAL BREACH DETECTED 🚨\n"
        f"The Decoy Data Center was opened!\n\n"
        f"🕐 Time : {time_now}\n"
        f"🌡️  Temp : {data['temperature']} °C\n"
        f"💧 Humidity: {data['humidity']} %\n\n"
        f"Buzzer + Red LED activated automatically."
    )
    send_telegram_alert(alert_msg)

    # Trigger buzzer + LED (non-blocking)
    trigger_alarm_async()


# ── Door Sensor via GPIO interrupts ─────────────────────────────────────────
if RUNNING_ON_PI:
    import RPi.GPIO as GPIO

    def _door_callback(channel):
        # MC-38 is normally closed (LOW). When opened → goes HIGH (pull-up)
        if GPIO.input(DOOR_SENSOR_PIN) == GPIO.HIGH:
            handle_door_open()

    GPIO.add_event_detect(
        DOOR_SENSOR_PIN,
        GPIO.RISING,
        callback=_door_callback,
        bouncetime=500,
    )
    print("🛡️  Physical Security Armed — MC-38 door sensor active.")
    print("    GPIO 14 | Buzzer GPIO 18 | Red LED GPIO 23")
    print("    Waiting for intrusion... (Ctrl+C to stop)\n")
    pause()

else:
    # ── Simulation mode: press ENTER to fake a door-open event ──────────────
    print("🛡️  [SIMULATION] Physical Security Armed.")
    print("    Press ENTER to simulate a door-open event. Ctrl+C to quit.\n")
    try:
        while True:
            input()
            handle_door_open()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")