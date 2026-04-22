"""
hardware_trap.py — Physical Intrusion Monitor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reads the MC-38 Magnetic Reed Switch in real-time using RPi.GPIO edge
detection.  When the cardboard "data center" door is opened:
  1. Immediately turns Buzzer ON  (GPIO 18)
  2. Immediately turns Red LED ON (GPIO 23)
  3. Sends a Telegram alert with live temp & humidity from DHT-11
  4. Keeps alarm on for 10 seconds, then auto-clears

MC-38 wiring:
  Wire A → GPIO 14 (BCM)  [Physical Pin 8]
  Wire B → GND            [Physical Pin 9]
  (Internal PUD_UP is used — no external resistor needed)

Run:  python3 hardware_trap.py
"""

import time
import signal
import sys

import sensor_hub
from sensor_hub import (
    RUNNING_ON_PI,
    DOOR_SENSOR_PIN,
    read_door_pin,
    get_sensor_data,
    trigger_alarm_async,
    cleanup,
)
from decoy_alert import send_telegram_alert


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Initialise GPIO and DHT-11 (only this file should call init)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
sensor_hub.init()
sensor_hub.start_dht_thread()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Door-open handler (called by GPIO interrupt or simulation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def handle_door_open():
    data     = get_sensor_data()
    time_now = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*50}")
    print(f"[{time_now}] ⚠️  DOOR OPENED — PHYSICAL BREACH!")
    print(f"  Temp    : {data['temperature']} °C")
    print(f"  Humidity: {data['humidity']} %")
    print(f"{'='*50}\n")

    # 1. Fire the physical alarm (buzzer + LED) immediately
    trigger_alarm_async()

    # 2. Send Telegram alert
    alert_msg = (
        f"🚨 PHYSICAL BREACH DETECTED 🚨\n"
        f"Decoy Data Center door was OPENED!\n\n"
        f"🕐 Time     : {time_now}\n"
        f"🌡️  Temp     : {data['temperature']} °C\n"
        f"💧 Humidity : {data['humidity']} %\n\n"
        f"🔊 Buzzer ON  |  🔴 Red LED ON\n"
        f"Alarm will auto-clear in 10 seconds."
    )
    send_telegram_alert(alert_msg)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GPIO Edge Detection (real hardware path)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if RUNNING_ON_PI:
    import RPi.GPIO as GPIO

    def _door_isr(channel):
        """
        Interrupt Service Routine — fires on RISING edge of GPIO 14.
        MC-38 with PUD_UP:
          Door CLOSED → pin LOW (magnet holds switch shut)
          Door OPENED → pin HIGH (magnet removed, switch opens, pull-up wins)
        Double-check the pin is still HIGH to filter noise.
        """
        time.sleep(0.05)                        # 50 ms debounce
        if GPIO.input(DOOR_SENSOR_PIN) == GPIO.HIGH:
            handle_door_open()

    # Register interrupt on RISING edge with 300 ms hardware debounce
    GPIO.add_event_detect(
        DOOR_SENSOR_PIN,
        GPIO.RISING,
        callback=_door_isr,
        bouncetime=300,
    )

    # ── Graceful shutdown on Ctrl+C ──────────────────────────────────────────
    def _shutdown(sig, frame):
        print("\n🛑 Shutting down — cleaning up GPIO…")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ── Startup self-test: blink LED + short beep to confirm wiring ──────────
    print("\n🔧 Self-test: LED and Buzzer will fire for 1 second…")
    GPIO.output(sensor_hub.BUZZER_PIN,  GPIO.HIGH)
    GPIO.output(sensor_hub.RED_LED_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(sensor_hub.BUZZER_PIN,  GPIO.LOW)
    GPIO.output(sensor_hub.RED_LED_PIN, GPIO.LOW)
    print("✅ Self-test done — if you heard the buzzer and saw the LED, wiring is correct.\n")

    # ── Live door status loop ────────────────────────────────────────────────
    print("🛡️  Physical Security ARMED")
    print(f"    MC-38  : BCM GPIO {DOOR_SENSOR_PIN}  (Physical Pin 8)")
    print(f"    Buzzer : BCM GPIO {sensor_hub.BUZZER_PIN}  (Physical Pin 12)")
    print(f"    Red LED: BCM GPIO {sensor_hub.RED_LED_PIN}  (Physical Pin 16)")
    print("    Waiting for door event… (Ctrl+C to stop)\n")

    try:
        while True:
            # Print live door status every 5 s so you can see the pin value
            door_state = "OPEN ⚠️" if read_door_pin() else "CLOSED ✅"
            data = get_sensor_data()
            print(f"[{time.strftime('%H:%M:%S')}] "
                  f"Door: {door_state:<12} | "
                  f"Temp: {data['temperature']}°C | "
                  f"Humidity: {data['humidity']}%")
            time.sleep(5)
    except KeyboardInterrupt:
        _shutdown(None, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Simulation mode (running on Windows/PC — no real GPIO)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
else:
    print("\n🛡️  [SIMULATION MODE] Physical Security Armed.")
    print("    Press ENTER to simulate a door-open event.")
    print("    Press Ctrl+C to quit.\n")
    try:
        while True:
            input(">>> Press ENTER to trigger door-open event: ")
            handle_door_open()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")