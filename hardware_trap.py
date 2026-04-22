from gpiozero import Button
from decoy_alert import send_telegram_alert
from signal import pause
import time

# We will plug the magnetic sensor into GPIO Pin 14
door_sensor = Button(14)

def trigger_physical_alarm():
    """This function runs the moment the box is opened."""
    time_now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time_now}] ⚠️ SENSOR TRIPPED: Door opened!")
    
    # Send the alert to your phone
    send_telegram_alert("🚨 HARDWARE ALERT 🚨\nPhysical tampering detected!\nThe Decoy Box was opened.")

# The logic: A magnetic switch acts just like a button. 
# When the door opens, the magnet moves, the circuit breaks, and the "button" is released.
door_sensor.when_released = trigger_physical_alarm

print("🛡️ Physical Security Armed. Monitoring the Decoy Box...")
print("Waiting for triggers... (Press Ctrl+C to stop)")

# This keeps the script running endlessly in the background
pause()