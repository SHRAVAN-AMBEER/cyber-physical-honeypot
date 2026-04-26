#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  start.sh — Launch Cyber-Physical Honeypot
#  Usage:  bash start.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   🛡️  Cyber-Physical Honeypot — Starting         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Hardware trap (GPIO owner — must start first) ──
echo "[1/2] Starting hardware_trap.py  (Door, Buzzer, LED, DHT-11)..."
venv/bin/python3 hardware_trap.py &
TRAP_PID=$!
sleep 3    # give GPIO + DHT time to init

# ── 2. Unified web server ─────────────────────────────
echo "[2/2] Starting unified_server.py  (All web traps — port 8080)..."
venv/bin/python3 unified_server.py &
WEB_PID=$!
sleep 1

# ── Status ────────────────────────────────────────────
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ All systems running!                         ║"
echo "║                                                  ║"
echo "║  🌐 Dashboard  : http://$PI_IP:8080      ║"
echo "║  🔐 Login Trap : http://$PI_IP:8080/login║"
echo "║  ⚠️  Emergency  : http://$PI_IP:8080/emergency   ║"
echo "║                                                  ║"
echo "║  Press Ctrl+C to stop everything                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

trap "echo ''; echo '🛑 Stopping...'; kill $TRAP_PID $WEB_PID 2>/dev/null; echo '✅ Done.'; exit 0" SIGINT SIGTERM
wait
