# 🏛️ EduCore Exam Vault — Cyber-Physical Honeypot System

A unified cyber-physical honeypot deployed on a Raspberry Pi that simulates a secure institutional examination data center. Combines a high-fidelity 4-page deceptive web portal with real-time physical GPIO alarms (buzzer + LED) and instant Telegram notifications to detect, log, and trap unauthorized access attempts.

---

##  Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [How It Works](#how-it-works)
- [Web Portal Pages](#web-portal-pages)
- [Trigger Table](#trigger-table)
- [Hardware Requirements](#hardware-requirements)
- [GPIO Pin Mapping](#gpio-pin-mapping)
- [Software Requirements](#software-requirements)
- [Installation & Setup](#installation--setup)
- [Project Structure](#project-structure)
- [Simulating an Attack](#simulating-an-attack)

---

##  Overview

This project is a **cyber-physical honeypot** deployed on a Raspberry Pi. It simulates a sensitive institutional data center — the **EduCore Exam Vault** — that stores digital exam scripts. The system consists of two tightly integrated layers:

- **Physical Layer** — real IoT sensors (DHT-11, MC-38) and actuators (buzzer, LED) connected via GPIO
- **Cyber Layer** — a convincing 4-page Flask web portal that lures, traps, and logs attackers

Any unauthorized interaction — from visiting pages to clicking simulated admin controls — triggers **real-time Telegram notifications** and/or **physical GPIO alarms**.

---

##  System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi                             │
│                                                                 │
│  ┌─────────────────────────┐    IPC via JSON flag (500ms poll)  │
│  │   unified_server.py     │ ──────────────────► hardware_trap  │
│  │   Flask :8080           │   /tmp/honeypot_state.json         │
│  │   4 web trap pages      │                    │               │
│  │   Telegram alerts       │               GPIO owner           │
│  └──────────┬──────────────┘          Buzzer · LED · Reed       │
│             │                                                   │
│     decoy_alert.py                                              │
│             │                                                   │
│             ▼                                                   │
│      Telegram Bot API ──────────────► Admin's Phone             │
│                                                                 │
│  Sensors: DHT-11 (GPIO 4) · MC-38 Reed Switch (GPIO 17)        │
│  Alarms:  Active Buzzer (GPIO 18) · Red LED (GPIO 23)          │
└─────────────────────────────────────────────────────────────────┘
```

### Two-Process Design

The system runs as **two separate processes** launched by `start.sh`:

| Process | File | Role |
|---|---|---|
| **Process 1** | `unified_server.py` | Flask web server on port 8080. Handles all web trap logic, sends Telegram alerts, writes IPC alarm flag to JSON |
| **Process 2** | `hardware_trap.py` | Sole owner of all GPIO pins. Polls JSON flag every 500ms, fires buzzer+LED when requested. Also monitors MC-38 for physical breach |

### IPC Mechanism (Web → GPIO)

The web process **cannot access GPIO directly**. Communication works via a shared JSON file:

```
unified_server.py  ──writes──►  /tmp/honeypot_state.json  {"alarm_requested": true}
                                         │
hardware_trap.py   ──polls every 500ms──►┘
                   ──on flag detected──► GPIO Buzzer + LED ON → flag reset to false
```

> End-to-end latency: **< 500ms** from web trigger to physical alarm.

---

##  How It Works

### Cyber Layer
1. Attacker discovers the portal at `http://<pi-ip>:8080/`
2. They see a convincing NOC dashboard showing **live temperature & humidity** from the real DHT-11 sensor
3. They navigate to `/login`, enter any credentials → captured and sent to Telegram → **redirected to `/admin`**
4. The admin panel has 6 realistic-looking vault control buttons — clicking **any** triggers the physical alarm
5. `/emergency` presents a fake "VAULT TEMP CRITICAL" panic scenario, pressuring them to enter override credentials

### Physical Layer
- **DHT-11** (GPIO 4): reads temperature & humidity every 3s → displayed live on dashboard
- **MC-38** (GPIO 17): detects physical door opening → immediate CRITICAL alarm + Telegram
- **Buzzer** (GPIO 18): sounds on attack actions
- **LED** (GPIO 23): lights up alongside buzzer

---

##  Web Portal Pages

| URL | Page Name | Purpose | Alarm? |
|---|---|---|---|
| `/` | EduCore Exam Vault Dashboard | Live NOC monitor — DHT-11 data, vault server status, security event log | ❌ Telegram only |
| `/login` | Secure Login | Credential trap — accepts **any** credentials, logs them, redirects to `/admin` | ❌ Telegram only |
| `/admin` | Admin Panel | 6 trap control buttons — each fires buzzer + LED + Telegram on click | ✅ On button click |
| `/emergency` | System Status | Social engineering panic page — fake vault cooling failure, override form submission fires alarm | ✅ On form submit |

### Admin Panel — 6 Trap Buttons

| Button | Label | Sub-label |
|---|---|---|
| 🔴 | Seal Exam Vault | Force-lock all digital storage units |
| 🔄 | Verify Script Integrity | Run MD5 checksum on all PDF scripts |
| 🛡️ | Lock Archive Access | Disable external network access to archives |
| 📋 | Export Exam Audit Trail | Generate signed examiner log report |
| 🔑 | Reset Examiner Access | Force rotation of all faculty keys |
| 🗑️ | Purge Cached Scripts | Clear local cache from memory banks |

---

##  Trigger Table

| Attacker Action | Telegram Alert | Severity | Buzzer + LED |
|---|---|---|---|
| Visit Dashboard (`/`) | ✅ | INFO | ❌ |
| Visit System Status (`/emergency`) | ✅ | WARNING | ❌ |
| Submit Login Form (`/login POST`) | ✅ + credentials captured | CRITICAL | ❌ |
| Reach Admin Panel (`/admin`) | ✅ | CRITICAL | ❌ |
| Click any Admin Control Button | ✅ + action name captured | CRITICAL | ✅ |
| Submit Emergency Override Form | ✅ + credentials captured | CRITICAL | ✅ |
| Physical Door Opened (MC-38) | ✅ + sensor data | CRITICAL | ✅ |

---

## 🔧 Hardware Requirements

| # | Component | Specification | Purpose |
|---|---|---|---|
| 1 | **Raspberry Pi** | Model 3B+ or 4 (1GB+ RAM) | Central compute unit |
| 2 | **MicroSD Card** | 16GB Class 10, Raspberry Pi OS | OS + project storage |
| 3 | **DHT-11 Sensor** | 3.5V–5V, ±2°C accuracy | Live temperature & humidity telemetry |
| 4 | **MC-38 Reed Switch** | Normally Closed (NC), magnetic | Physical door breach detection |
| 5 | **Active Buzzer** | 5V active, ~85dB | Audible alarm |
| 6 | **Red LED** | 5mm, 20mA max | Visual alarm indicator |
| 7 | **Resistor** | 330Ω, 1/4W | LED current limiter |
| 8 | **Breadboard** | Half/full size solderless | Component mounting |
| 9 | **Jumper Wires** | M-to-F and M-to-M | GPIO connections |
| 10 | **Power Supply** | 5V/2.5A Micro-USB (Pi 3B) or USB-C (Pi 4) | Power |
| 11 | **Network** | Wi-Fi or Ethernet | Web server + Telegram |

---

## 📍 GPIO Pin Mapping (BCM Numbering)

| BCM GPIO | Physical Pin | Component | Direction | Notes |
|---|---|---|---|---|
| **GPIO 4** | Pin 7 | DHT-11 Data | Input | Single-wire protocol |
| **GPIO 17** | Pin 11 | MC-38 Reed Switch | Input | Pull-up enabled; LOW = door open |
| **GPIO 18** | Pin 12 | Active Buzzer (+) | Output | HIGH = ON |
| **GPIO 23** | Pin 16 | Red LED (via 330Ω) | Output | HIGH = ON |
| 3.3V / 5V | Pin 1, 2, 4 | VCC for sensors | Power | DHT-11: 3.3V; Buzzer: 5V |
| GND | Pin 6, 9, 14 | Ground | Ground | Common reference |

---

## 💻 Software Requirements

### System Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv liblgpio-dev swig python3-libgpiod git
```

### Python Libraries
```bash
pip install flask requests python-dotenv adafruit-circuitpython-dht gpiozero lgpio
```

| Library | Purpose |
|---|---|
| `flask` | Web framework — serves all 4 honeypot pages on port 8080 |
| `requests` | HTTP client — sends Telegram Bot API notifications |
| `python-dotenv` | Loads `BOT_TOKEN` and `CHAT_ID` from `.env` file securely |
| `adafruit-circuitpython-dht` | DHT-11 sensor driver for GPIO 4 |
| `gpiozero` | High-level GPIO control for buzzer, LED, reed switch |
| `lgpio` | Low-level GPIO backend for gpiozero on newer Pi OS |

### Environment Variables (`.env`)
```env
BOT_TOKEN=your_telegram_bot_token_here
CHAT_ID=your_telegram_chat_id_here
```

> ⚠️ The `.env` file is listed in `.gitignore` — **never commit it to GitHub**. Use `.env.example` as a template.

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/SHRAVAN-AMBEER/cyber-physical-honeypot.git
cd cyber-physical-honeypot
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Telegram
```bash
cp .env.example .env
nano .env
# Fill in BOT_TOKEN and CHAT_ID
```

### 5. Run the System
```bash
bash start.sh
```

This starts **two processes**:
- `hardware_trap.py` — takes ownership of all GPIO pins
- `unified_server.py` — starts web server on port 8080

### 6. Access the Portal
Open any browser on the same network:
```
http://<your-pi-ip>:8080/
```

---

## 📁 Project Structure

```
cyber-physical-honeypot/
├── unified_server.py       # Flask web app: 4 routes, trap logic, Telegram, IPC flag
├── hardware_trap.py        # GPIO owner: buzzer, LED, MC-38, 500ms alarm watcher
├── sensor_hub.py           # DHT-11 reader: get_sensor_data() + request_alarm()
├── decoy_alert.py          # Telegram Bot API message sender
├── start.sh                # Bash launcher for both processes
├── requirements.txt        # Python dependencies
├── .env.example            # Template for Telegram credentials
└── templates/
    ├── dashboard.html      # EduCore NOC dashboard (live sensor data)
    ├── login.html          # Credential capture login page
    ├── admin.html          # Admin panel trap (6 vault control buttons)
    └── emergency.html      # Social engineering panic page
```

---

## 🎯 Simulating an Attack

Test from **any device on the same network**:

| Step | Action | What Happens |
|---|---|---|
| 1 | Open `http://<pi-ip>:8080/` | Telegram: Dashboard visit (INFO) |
| 2 | Click **Secure Login** in navbar | Visit the login page |
| 3 | Enter **any username/password** and submit | Telegram: Credentials captured (CRITICAL) → redirected to Admin Panel |
| 4 | You're now on the Admin Panel | Telegram: Admin panel accessed (CRITICAL) |
| 5 | Click any vault control button (e.g. "Seal Exam Vault") | 🚨 Buzzer + LED + Telegram: Action triggered (CRITICAL) |
| 6 | Visit `http://<pi-ip>:8080/emergency` | Telegram: System Status viewed (WARNING) |
| 7 | Submit the override form | 🚨 Buzzer + LED + Telegram: Override attempted (CRITICAL) |
| 8 | Open the physical enclosure (MC-38) | 🚨 Buzzer + LED + Telegram: Physical breach (CRITICAL) |

---

## 👨‍🎓 Project Info

- **Institution:** Chaitanya Bharathi Institute of Technology (CBIT), Hyderabad
- **Department:** Information Technology
- **Subject:** Embedded Systems & IoT (ESIOT)
- **Platform:** Raspberry Pi 3B / 4
- **Academic Year:** 2025–2026

---

*All interactions with this system are logged for research and educational purposes.*
