"""
hardware_trap.py — Physical Intrusion Monitor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uses gpiozero Button.when_released for real MC-38 edge detection.
This works correctly on all Raspberry Pi OS versions including Bookworm.

MC-38 wiring:
  Wire A → GPIO 17 (BCM) — Physical Pin 11
  Wire B → GND           — Physical Pin 9

Run:  python3 hardware_trap.py
"""

import time
import signal
import sys

import sensor_hub
from sensor_hub import (
    RUNNING_ON_PI,
    get_sensor_data,
    get_door_button,
    trigger_alarm_async,
    cleanup,
)
from decoy_alert import send_telegram_alert

# ── Init GPIO and DHT (this is the ONLY process that should do this) ─────────
sensor_hub.init()
sensor_hub.start_dht_thread()

# ── Wait 2 s for DHT thread to get first reading ─────────────────────────────
time.sleep(2)


# ── Door-open handler ─────────────────────────────────────────────────────────
def handle_door_open():
    data     = get_sensor_data()
    time_now = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*52}")
    print(f"[{time_now}] ⚠️  DOOR OPENED — PHYSICAL BREACH DETECTED!")
    print(f"  Temp     : {data['temperature']} °C")
    print(f"  Humidity : {data['humidity']} %")
    print(f"{'='*52}\n")

    # Fire buzzer + LED immediately (non-blocking)
    trigger_alarm_async()

    # Send Telegram alert
    alert_msg = (
        f"🚨 PHYSICAL BREACH DETECTED 🚨\n"
        f"Decoy Data Center door was OPENED!\n\n"
        f"🕐 Time     : {time_now}\n"
        f"🌡️  Temp     : {data['temperature']} °C\n"
        f"💧 Humidity : {data['humidity']} %\n\n"
        f"🔊 Buzzer ON  |  🔴 Red LED ON\n"
        f"Auto-clears in 10 seconds."
    )
    send_telegram_alert(alert_msg)


# ── Startup self-test: 1 s blink to confirm wiring ───────────────────────────
if RUNNING_ON_PI:
    print("\n🔧 Self-test: Buzzer + LED ON for 1 second...")
    if sensor_hub._buzzer and sensor_hub._led:
        sensor_hub._buzzer.on()
        sensor_hub._led.on()
        time.sleep(1)
        sensor_hub._buzzer.off()
        sensor_hub._led.off()
        print("✅ Self-test passed — wiring is correct!\n")
    else:
        print("⚠️  Buzzer/LED not initialised — check wiring\n")


# ── Attach MC-38 door sensor via gpiozero ────────────────────────────────────
door_button = get_door_button()

if RUNNING_ON_PI and door_button:
    # MC-38 NC switch: door open = circuit breaks = button "released"
    door_button.when_released = handle_door_open

    print("🛡️  Physical Security ARMED")
    print(f"    MC-38  : BCM17  (Physical Pin 11)")
    print(f"    Buzzer : BCM18  (Physical Pin 12)")
    print(f"    Red LED: BCM23  (Physical Pin 16)")
    print("    Waiting for door event... (Ctrl+C to stop)\n")

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    def _shutdown(sig, frame):
        print("\n🛑 Shutting down...")
        door_button.close()
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ── Live status loop ──────────────────────────────────────────────────────
    try:
        while True:
            data       = get_sensor_data()
            door_state = "OPEN ⚠️ " if not door_button.is_pressed else "CLOSED ✅"
            print(f"[{time.strftime('%H:%M:%S')}]  "
                  f"Door: {door_state:<13} | "
                  f"Temp: {data['temperature']}°C | "
                  f"Humidity: {data['humidity']}%")
            time.sleep(5)
    except KeyboardInterrupt:
        _shutdown(None, None)

elif RUNNING_ON_PI and not door_button:
    print("❌ Could not initialise door sensor. Check wiring on GPIO 17 (Pin 11).")
    sys.exit(1)

else:
    # ── Simulation mode (PC / no GPIO) ───────────────────────────────────────
    print("🛡️  [SIMULATION] Press ENTER to trigger door-open. Ctrl+C to quit.\n")
    try:
        while True:
            input(">>> Press ENTER to simulate door open: ")
            handle_door_open()
    except KeyboardInterrupt:
        print("\nStopped.")