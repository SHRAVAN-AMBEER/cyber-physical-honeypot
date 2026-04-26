"""
social_trap.py - Standalone Social Engineering Web Trap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs on port 5050. Completely isolated — does NOT import
sensor_hub.py or touch any GPIO pins. Safe to run alongside
hardware_trap.py with zero conflicts.

When an attacker submits the fake login form:
  → Telegram alert with their IP + credentials
  → 503 error returned to fool them
"""

import datetime
from flask import Flask, request, render_template_string
from decoy_alert import send_telegram_alert

app = Flask(__name__)

FAKE_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EMERGENCY OVERRIDE — DataCore Systems</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap');
  *{margin:0;padding:0;box-sizing:border-box;}
  :root{
    --red:#ff1a1a;--red2:#cc0000;--red-dim:rgba(255,26,26,0.15);
    --bg:#0a0e1a;--bg2:#0f1423;--bg3:#141928;
    --text:#c8d8e8;--muted:#4a6070;--mono:'Share Tech Mono',monospace;
  }
  body{
    font-family:var(--mono);background:var(--bg);color:var(--text);
    min-height:100vh;display:flex;flex-direction:column;align-items:center;
    overflow-x:hidden;
  }

  /* grid background */
  body::before{
    content:'';position:fixed;inset:0;
    background-image:
      linear-gradient(rgba(255,26,26,0.04) 1px,transparent 1px),
      linear-gradient(90deg,rgba(255,26,26,0.04) 1px,transparent 1px);
    background-size:40px 40px;pointer-events:none;
  }

  /* ── Top Warning Banner ── */
  .banner{
    width:100%;background:var(--red2);color:#fff;
    text-align:center;padding:14px;font-size:18px;font-weight:bold;
    letter-spacing:3px;
    animation:banner-blink 0.5s step-start infinite;
    border-bottom:3px solid var(--red);
    text-shadow:0 0 20px #fff;
    position:sticky;top:0;z-index:100;
  }
  @keyframes banner-blink{0%,100%{background:var(--red2);box-shadow:0 0 30px var(--red);}50%{background:#4a0000;box-shadow:none;}}

  /* ── Sub banner ── */
  .sub-banner{
    width:100%;background:rgba(180,0,0,0.1);border-bottom:1px solid rgba(255,26,26,0.3);
    padding:8px;text-align:center;font-size:12px;color:var(--red);letter-spacing:2px;
    animation:sub-blink 1.2s ease-in-out infinite;
  }
  @keyframes sub-blink{0%,100%{opacity:1;}50%{opacity:0.4;}}

  /* ── Main container ── */
  .container{
    width:100%;max-width:700px;padding:30px 20px;
    display:flex;flex-direction:column;gap:20px;
  }

  /* ── Telemetry box ── */
  .telemetry-box{
    background:var(--bg2);border:1px solid rgba(255,26,26,0.35);
    border-radius:8px;padding:20px;
    box-shadow:0 0 25px rgba(255,26,26,0.1),inset 0 0 20px rgba(255,26,26,0.03);
  }
  .telemetry-header{
    display:flex;justify-content:space-between;align-items:center;
    margin-bottom:16px;border-bottom:1px solid rgba(255,26,26,0.2);padding-bottom:10px;
  }
  .telemetry-title{font-size:11px;letter-spacing:2px;color:var(--muted);}
  .telemetry-live{
    font-size:10px;color:var(--red);letter-spacing:1px;
    animation:sub-blink 1s infinite;
  }
  .telemetry-row{
    display:flex;justify-content:space-between;align-items:center;
    padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);
  }
  .telemetry-row:last-child{border:none;}
  .t-label{font-size:12px;color:var(--muted);}
  .t-value{font-size:22px;font-weight:bold;letter-spacing:1px;}
  .t-val-red{color:var(--red);text-shadow:0 0 10px var(--red);}
  .t-val-orange{color:#ff8800;text-shadow:0 0 10px #ff8800;}
  .t-status{
    font-size:10px;padding:3px 10px;border-radius:3px;letter-spacing:1px;font-weight:bold;
  }
  .st-critical{background:rgba(255,26,26,0.2);color:var(--red);border:1px solid var(--red);animation:sub-blink 0.8s infinite;}
  .st-warn{background:rgba(255,136,0,0.15);color:#ff8800;border:1px solid #ff8800;}

  /* progress bar */
  .t-bar-wrap{height:5px;background:rgba(255,255,255,0.06);border-radius:3px;margin-top:12px;overflow:hidden;}
  .t-bar{height:100%;border-radius:3px;transition:width 0.5s ease;}
  .t-bar-red{background:linear-gradient(90deg,#cc0000,var(--red));}
  .t-bar-orange{background:linear-gradient(90deg,#cc6600,#ff8800);}

  /* ── Risk badge ── */
  .risk-badge{
    background:rgba(255,26,26,0.1);border:1px solid var(--red);
    border-radius:6px;padding:12px 16px;
    display:flex;align-items:center;gap:10px;
    animation:risk-pulse 1.5s ease-in-out infinite;
  }
  @keyframes risk-pulse{0%,100%{box-shadow:0 0 10px rgba(255,26,26,0.2);}50%{box-shadow:0 0 25px rgba(255,26,26,0.5);}}
  .risk-icon{font-size:22px;}
  .risk-text{font-size:12px;line-height:1.6;color:#ffaaaa;letter-spacing:1px;}
  .risk-text strong{color:var(--red);display:block;font-size:13px;margin-bottom:2px;}

  /* ── Info block ── */
  .info-block{
    background:var(--bg3);border:1px solid rgba(255,255,255,0.06);
    border-radius:8px;padding:18px;font-size:12px;line-height:1.9;
    color:#8aaabb;letter-spacing:0.5px;
  }
  .info-block .hl{color:#ffaaaa;}
  .info-block .sys{color:#5588aa;font-size:11px;}

  /* ── Login form ── */
  .login-card{
    background:var(--bg2);border:1px solid rgba(255,26,26,0.3);
    border-radius:10px;padding:28px;
    box-shadow:0 0 40px rgba(255,26,26,0.08);
  }
  .login-title{
    font-size:11px;letter-spacing:2px;color:var(--muted);
    margin-bottom:20px;padding-bottom:12px;
    border-bottom:1px solid rgba(255,26,26,0.2);
    display:flex;align-items:center;gap:8px;
  }
  .login-title::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--red);box-shadow:0 0 6px var(--red);display:inline-block;animation:sub-blink 0.8s infinite;}
  label{display:block;font-size:10px;letter-spacing:2px;color:var(--muted);margin-bottom:6px;margin-top:14px;}
  input[type=text],input[type=password]{
    width:100%;padding:12px 14px;
    background:rgba(0,0,0,0.4);
    border:1px solid rgba(255,26,26,0.25);border-radius:6px;
    color:var(--text);font-family:var(--mono);font-size:14px;
    outline:none;transition:all 0.2s;letter-spacing:1px;
  }
  input:focus{border-color:var(--red);box-shadow:0 0 0 2px rgba(255,26,26,0.15);}
  input::placeholder{color:var(--muted);}
  .submit-btn{
    width:100%;margin-top:22px;padding:14px;
    background:linear-gradient(135deg,#8b0000,var(--red2));
    border:1px solid var(--red);border-radius:6px;
    color:#fff;font-family:var(--mono);font-size:13px;
    font-weight:bold;letter-spacing:2px;cursor:pointer;
    transition:all 0.2s;
    box-shadow:0 0 20px rgba(255,26,26,0.3);
    animation:btn-pulse 2s ease-in-out infinite;
  }
  @keyframes btn-pulse{0%,100%{box-shadow:0 0 15px rgba(255,26,26,0.3);}50%{box-shadow:0 0 35px rgba(255,26,26,0.7);}}
  .submit-btn:hover{background:linear-gradient(135deg,var(--red2),var(--red));transform:translateY(-1px);}
  .auth-note{margin-top:10px;font-size:10px;color:var(--muted);text-align:center;letter-spacing:1px;}

  /* ── Footer ── */
  .footer{
    font-size:10px;color:var(--muted);text-align:center;
    padding:20px 0 30px;letter-spacing:1px;line-height:1.8;
  }

  /* ── Countdown timer ── */
  .countdown{
    text-align:center;background:rgba(255,26,26,0.07);
    border:1px solid rgba(255,26,26,0.2);border-radius:6px;padding:12px;
    font-size:13px;color:var(--red);letter-spacing:2px;
  }
  .countdown-val{font-size:28px;font-weight:bold;display:block;
    text-shadow:0 0 15px var(--red);}
</style>
</head>
<body>

<!-- Warning Banner -->
<div class="banner">⚠ &nbsp; CLIMATE CONTROL OFFLINE &nbsp; ⚠</div>
<div class="sub-banner">AUTOMATED DEHUMIDIFICATION SYSTEM FAILURE — IMMEDIATE HUMAN INTERVENTION REQUIRED</div>

<div class="container">

  <!-- Live Telemetry -->
  <div class="telemetry-box">
    <div class="telemetry-header">
      <span class="telemetry-title">LIVE ENVIRONMENTAL TELEMETRY — RACK ROOM B</span>
      <span class="telemetry-live">● LIVE</span>
    </div>

    <div class="telemetry-row">
      <span class="t-label">AMBIENT TEMPERATURE</span>
      <span class="t-value t-val-orange" id="temp-display">38.5°C</span>
      <span class="t-status st-warn">WARNING</span>
    </div>
    <div class="t-bar-wrap"><div class="t-bar t-bar-orange" id="temp-bar" style="width:77%"></div></div>

    <div class="telemetry-row" style="margin-top:14px">
      <span class="t-label">RELATIVE HUMIDITY</span>
      <span class="t-value t-val-red" id="hum-display">89.4%</span>
      <span class="t-status st-critical">CRITICAL</span>
    </div>
    <div class="t-bar-wrap"><div class="t-bar t-bar-red" id="hum-bar" style="width:89%"></div></div>
  </div>

  <!-- Risk Alert -->
  <div class="risk-badge">
    <span class="risk-icon">💧</span>
    <div class="risk-text">
      <strong>RISK OF HARDWARE CONDENSATION: CRITICAL</strong>
      Humidity levels above 85% cause irreversible condensation damage to server components.
      Current level 89.4% — exceeds safety threshold by 4.4 points.
    </div>
  </div>

  <!-- Countdown -->
  <div class="countdown">
    ESTIMATED TIME TO HARDWARE DAMAGE
    <span class="countdown-val" id="countdown">07:43</span>
    MINUTES REMAINING BEFORE CRITICAL THRESHOLD BREACH
  </div>

  <!-- Info Block -->
  <div class="info-block">
    <span class="sys">[SYS] 04:17:32 UTC — INCIDENT ID: DC-B-2025-04-22-0049</span><br><br>
    The <span class="hl">automated dehumidification subsystem</span> for Rack Room B has gone offline
    following a firmware update conflict at 03:41 UTC. All three redundant
    dehumidifier units (DH-B1, DH-B2, DH-B3) are unresponsive.<br><br>
    <span class="hl">Manual Administrator Authentication</span> is required to engage the
    emergency manual override and force-restart the climate control units
    before condensation damage occurs to the primary server infrastructure.<br><br>
    <span class="sys">This override requires Level-4 Admin credentials. All access is logged and audited.</span>
  </div>

  <!-- Login Form -->
  <div class="login-card">
    <div class="login-title">MANUAL ADMINISTRATOR AUTHENTICATION REQUIRED</div>
    <form method="POST" action="/" id="override-form">
      <label for="admin-id">ADMIN ID</label>
      <input type="text" id="admin-id" name="username" placeholder="admin@datacore.internal" required autocomplete="off">
      <label for="passphrase">OVERRIDE PASSPHRASE</label>
      <input type="password" id="passphrase" name="password" placeholder="••••••••••••••••" required autocomplete="off">
      <button class="submit-btn" type="submit" id="override-btn">
        ⚡ ENGAGE MANUAL OVERRIDE
      </button>
      <div class="auth-note">All authentication attempts are cryptographically logged · DataCore Audit v3.1</div>
    </form>
  </div>

  <div class="footer">
    DataCore Systems Inc. · Emergency Response Portal · Rack Room B · Node US-EAST-04<br>
    TLS 1.3 Encrypted · ISO 27001:2022 · NIST SP 800-53
  </div>

</div><!-- /container -->

<script>
// ── Live telemetry fluctuation ────────────────────────────────────────────────
let temp = 38.5;
let hum  = 89.4;

function rand(min, max){ return Math.random()*(max-min)+min; }

function updateTelemetry(){
  temp = Math.max(37.0, Math.min(42.0, temp + rand(-0.3, 0.4)));
  hum  = Math.max(87.0, Math.min(95.0, hum  + rand(-0.2, 0.5)));

  document.getElementById('temp-display').textContent = temp.toFixed(1) + '°C';
  document.getElementById('hum-display').textContent  = hum.toFixed(1) + '%';

  // bar widths: temp 0–50°C range, hum 0–100%
  document.getElementById('temp-bar').style.width = Math.min(100,(temp/50)*100).toFixed(1)+'%';
  document.getElementById('hum-bar').style.width  = hum.toFixed(1)+'%';
}
setInterval(updateTelemetry, 1800);

// ── Countdown timer ───────────────────────────────────────────────────────────
let totalSeconds = 7*60 + 43;
function updateCountdown(){
  if(totalSeconds <= 0){
    document.getElementById('countdown').textContent = '00:00';
    return;
  }
  totalSeconds--;
  const m = String(Math.floor(totalSeconds/60)).padStart(2,'0');
  const s = String(totalSeconds % 60).padStart(2,'0');
  document.getElementById('countdown').textContent = m+':'+s;
}
setInterval(updateCountdown, 1000);

// ── Button loading state on submit ────────────────────────────────────────────
document.getElementById('override-form').addEventListener('submit', function(){
  const btn = document.getElementById('override-btn');
  btn.textContent = '⏳ AUTHENTICATING...';
  btn.disabled = true;
});
</script>
</body>
</html>"""


@app.route('/', methods=['GET', 'POST'])
def honeypot_login():
    if request.method == 'POST':
        hacker_ip      = request.remote_addr
        attempted_user = request.form.get('username', '')
        attempted_pass = request.form.get('password', '')
        time_now       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        alert_msg = (
            f"🎣 SOCIAL ENGINEERING TRAP SPRUNG 🎣\n\n"
            f"Attacker panicked at the fake humidity warning!\n\n"
            f"🕐 Time     : {time_now}\n"
            f"🌍 IP       : {hacker_ip}\n"
            f"👤 Username : {attempted_user}\n"
            f"🔑 Password : {attempted_pass}"
        )
        send_telegram_alert(alert_msg)
        print(f"[TRAP SPRUNG] 🎣 Attacker {hacker_ip} submitted: {attempted_user} / {attempted_pass}")

        return "<h1>Error 503: Subsystem Unreachable. Connection Terminated.</h1>", 503

    visitor_ip = request.remote_addr
    print(f"[VISIT] {visitor_ip} viewed the social engineering trap")
    return render_template_string(FAKE_PAGE_HTML)


if __name__ == '__main__':
    print("🕸️  Starting Standalone Social Engineering Trap on port 5050...")
    print("    Open http://<pi-ip>:5050 to view")
    app.run(host='0.0.0.0', port=5050, debug=False)
