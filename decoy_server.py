from flask import Flask, request, render_template_string
from decoy_alert import send_telegram_alert  # Importing your alert brain!
import datetime

app = Flask(__name__)

# This is the fake HTML page the "hacker" will see
FAKE_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Industrial Smart Monitor - Login</title>
    <style>
        body { font-family: Arial; background-color: #f4f4f4; text-align: center; padding-top: 100px; }
        .login-box { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); display: inline-block; }
        input { display: block; margin: 10px auto; padding: 10px; width: 80%; }
        button { background-color: #b30000; color: white; padding: 10px 20px; border: none; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>⚠️ Secured Industrial Subsystem</h2>
        <p>Enter Admin Credentials to access temperature controls.</p>
        <form method="POST" action="/">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">System Login</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def honeypot_login():
    if request.method == 'POST':
        # THE TRAP IS SPRUNG! Someone tried to log in.
        hacker_ip = request.remote_addr
        attempted_user = request.form.get('username')
        attempted_pass = request.form.get('password')
        time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Formulate the alert message to send to your phone
        alert_msg = f"🚨 CYBER ALERT 🚨\n" \
                    f"Unauthorized Web Login Attempt!\n" \
                    f"Time: {time_now}\n" \
                    f"IP Address: {hacker_ip}\n" \
                    f"Tried Username: {attempted_user}\n" \
                    f"Tried Password: {attempted_pass}"
        
        # Send the text to your phone
        send_telegram_alert(alert_msg)
        print(f"Intrusion logged from {hacker_ip}. Alert sent!")

        # Give the hacker a fake error page so they don't realize it's a trap
        return "<h1>Error 503: Database Connection Timeout. Please try again later.</h1>", 503

    # If it's a normal visit (GET request), show them the fake login page
    return render_template_string(FAKE_PAGE_HTML)

if __name__ == '__main__':
    # Run the server so anyone on your Wi-Fi can see it
    print("Starting Cyber-Physical Decoy Web Server...")
    app.run(host='0.0.0.0', port=5000)