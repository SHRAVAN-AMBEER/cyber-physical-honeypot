#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  start.sh — Launch all Cyber-Physical Honeypot scripts
#  Usage:  bash start.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cd "$(dirname "$0")"   # always run from the project folder

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   🛡️  Cyber-Physical Honeypot — Starting         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Hardware trap (GPIO owner — must start first) ──
echo "[1/4] Starting hardware_trap.py  (Door sensor, Buzzer, LED)..."
venv/bin/python3 hardware_trap.py &
TRAP_PID=$!
sleep 2          # give GPIO time to initialise before others start

# ── 2. Honeypot login server ──────────────────────────
echo "[2/4] Starting decoy_server.py   (Honeypot login — port 5000)..."
venv/bin/python3 decoy_server.py &
SERVER_PID=$!
sleep 1

# ── 3. Decoy dashboard ────────────────────────────────
echo "[3/4] Starting decoy_dashboard.py (Dashboard — port 8080)..."
venv/bin/python3 decoy_dashboard.py &
DASH_PID=$!
sleep 1

# ── 4. Social engineering trap ────────────────────────
echo "[4/4] Starting social_trap.py     (Emergency Override Trap — port 5050)..."
venv/bin/python3 social_trap.py &
SOCIAL_PID=$!
sleep 1

# ── Status ────────────────────────────────────────────
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ All systems running!                         ║"
echo "║                                                  ║"
echo "║  🌐 Dashboard      : http://$PI_IP:8080 ║"
echo "║  🕸️  Honeypot login : http://$PI_IP:5000 ║"
echo "║  🎣 Social trap    : http://$PI_IP:5050 ║"
echo "║                                                  ║"
echo "║  Press Ctrl+C to stop everything                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Wait and handle Ctrl+C cleanly ───────────────────
trap "echo ''; echo '🛑 Stopping all processes...'; kill $TRAP_PID $SERVER_PID $DASH_PID $SOCIAL_PID 2>/dev/null; echo '✅ All stopped.'; exit 0" SIGINT SIGTERM

wait
