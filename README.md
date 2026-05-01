# 🏫 CBIT Exam Vault — Cyber-Physical Honeypot System

> A unified cyber-physical honeypot designed to detect and trap unauthorized access attempts on a simulated CBIT Examination Branch Data Center. Combines a high-fidelity decoy web portal with real-time physical alarms (buzzer + LED) and instant Telegram notifications.

---

## 📌 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [GPIO Pin Mapping](#gpio-pin-mapping)
- [Installation & Setup](#installation--setup)
- [How It Works](#how-it-works)
- [Web Portal Pages](#web-portal-pages)
- [Trigger Table](#trigger-table)
- [Project Structure](#project-structure)

---

## 📖 Overview

This project is a **cyber-physical honeypot** deployed on a Raspberry Pi. It simulates a sensitive institutional data center — the **CBIT Examination Branch Vault** — storing digital exam scripts. The goal is to:

- **Lure** unauthorized users into interacting with a convincing fake portal
- **Capture** credentials entered at the login and emergency override pages
- **Trigger** a real physical alarm (buzzer + LED) when an attacker takes destructive actions
- **Alert** the administrator in real time via Telegram with the attacker's IP, username, password, and action taken

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Raspberry Pi                           │
│                                                            │
│  ┌──────────────────┐     IPC via JSON flag                │
│  │  unified_server  │ ─────────────────────► hardware_trap │
│  │  (Flask :8080)   │                        (GPIO owner)  │
│  └────────┬─────────┘                        └────┬───────┘│
│           │ Telegram alerts                       │        │
│           ▼                                  Buzzer + LED  │
│     decoy_alert.py                                         │
│           │                                                │
│           ▼                                                │
│    Telegram Bot API                                        │
│                                                            │
│  Sensors: DHT-11 (Temp/Humidity) · MC-38 (Door Reed)      │
└────────────────────────────────────────────────────────────┘
```

---

## 🔧 Hardware Requirements

| Component | Specification | Purpose |
|---|---|---|
| Raspberry Pi | Model 3B / 4 (any model with GPIO) | Main compute unit |
| DHT-11 Sensor | Temperature & Humidity | Live telemetry on dashboard |
| MC-38 Magnetic Reed Switch | Door sensor | Physical break-in detection |
| Active Buzzer | 5V Active Buzzer Module | Audible alarm on attack |
| Red LED | 5mm, with 330Ω resistor | Visual alarm indicator |
| Jumper Wires | M-to-F / M-to-M | GPIO connections |
| Breadboard | Half/Full size | Component mounting |
| MicroSD Card | 8GB+ with Raspberry Pi OS | OS storage |

---

## 💻 Software Requirements

### System Dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv liblgpio-dev swig python3-libgpiod
```

### Python Libraries
```bash
pip install flask requests python-dotenv adafruit-circuitpython-dht gpiozero lgpio
```

### Full `requirements.txt`
```
flask
requests
python-dotenv
adafruit-circuitpython-dht
gpiozero
lgpio
```

### Environment Variables (`.env` file)
```env
BOT_TOKEN=your_telegram_bot_token_here
CHAT_ID=your_telegram_chat_id_here
```

---

## 📍 GPIO Pin Mapping (BCM Numbering)

| GPIO (BCM) | Component | Direction |
|---|---|---|
| GPIO 4 | DHT-11 Data Pin | Input |
| GPIO 17 | MC-38 Reed Switch | Input (Pull-Up) |
| GPIO 18 | Active Buzzer (+) | Output |
| GPIO 23 | Red LED (+) | Output |

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/SHRAVAN-AMBEER/cyber-physical-honeypot.git
cd cyber-physical-honeypot
```

### 2. Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Telegram
Create a `.env` file in the project root:
```bash
cp .env.example .env
nano .env
# Fill in your BOT_TOKEN and CHAT_ID
```

### 5. Run the System
```bash
bash start.sh
```

This launches:
- `hardware_trap.py` — Owns all GPIO pins, listens for alarm requests
- `unified_server.py` — Serves the honeypot web portal on port `8080`

---

## ⚙️ How It Works

### Physical Layer
- **DHT-11** continuously reads temperature & humidity, displayed live on the dashboard
- **MC-38 Reed Switch** detects physical door opening — instantly triggers buzzer + LED + Telegram alert

### Web Layer — IPC Mechanism
The web server **cannot access GPIO directly**. Instead:
1. `unified_server.py` writes an `alarm_requested: true` flag to `/tmp/honeypot_state.json`
2. `hardware_trap.py` polls this file every 500ms
3. When the flag is detected, it triggers the physical alarm and resets the flag

---

## 🌐 Web Portal Pages

| URL | Page | Purpose |
|---|---|---|
| `/` | CBIT Exam Vault Dashboard | Live telemetry display, security event log |
| `/login` | Secure Login | Credential trap — accepts anything, captures & logs |
| `/admin` | Admin Panel | High-fidelity trap with 6 destructive-looking vault controls |
| `/emergency` | System Status | Social engineering — warns exam scripts are at risk |

---

## ⚡ Trigger Table

| Attacker Action | Telegram Alert | Buzzer + LED |
|---|---|---|
| Visit Dashboard (`/`) | ✅ Info | ❌ |
| Visit System Status (`/emergency`) | ✅ Warning | ❌ |
| Submit Login Form | ✅ Critical + Credentials | ❌ |
| Reach Admin Panel (`/admin`) | ✅ Critical | ❌ |
| Click any Admin Control Button | ✅ Critical + Action Name | ✅ |
| Submit Emergency Override Form | ✅ Critical + Credentials | ✅ |
| Physical Door Opened (Reed Switch) | ✅ Critical + Sensor Data | ✅ |

---

## 📁 Project Structure

```
cyber-physical-honeypot/
├── unified_server.py       # Main Flask web honeypot
├── hardware_trap.py        # GPIO controller + alarm watcher
├── sensor_hub.py           # DHT-11 reader + IPC alarm bridge
├── decoy_alert.py          # Telegram notification helper
├── start.sh                # Launch script
├── requirements.txt        # Python dependencies
├── .env.example            # Template for credentials
└── templates/
    ├── dashboard.html      # NOC Monitor dashboard
    ├── login.html          # Credential trap page
    ├── admin.html          # Admin panel trap
    └── emergency.html      # Social engineering panic page
```

---

## 👨‍🎓 Project Info

- **Institution:** Chaitanya Bharathi Institute of Technology (CBIT), Hyderabad
- **Department:** Electronics & IoT
- **Subject:** Embedded Systems & IoT
- **Platform:** Raspberry Pi

---

*All interactions with this system are logged for research and educational purposes.*
