***

# 🔮 Pondering Orb C2
> **A Custom, Database-Backed, and Resilient Command & Control (C2) Framework.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Linux](https://img.shields.io/badge/platform-linux-lightgrey.svg)](https://www.linux.org/)

Pondering Orb is a Red Team Command and Control infrastructure project developed for CDT. It moves away from automated, "noisy" frameworks in favor of a custom-built, stealth-first architecture focusing on **Operational Security (OpSec)**, **Relational Persistence**, and **Environment Independence**.

---

## 🏛️ Architecture & Philosophy

### 1. The Scrying Pool (SQL Backend & Listener)
Pondering Orb utilizes a relational database to manage its "eyes" across the network.
* **Asynchronous Tasking:** Queue commands for agents even when they are offline.
* **Permanent Logging:** Every command and result is stored for later analysis or reporting.
* **Encrypted Whispers:** Communication is secured via **AES-256 encryption**.

### 2. The Familiar (Compiled C++ Agent)
The agent is a (rather big) standalone binary.
* **Zero Dependencies:** Compiled with Nuitka, it requires no Python installation on the target machine.
* **Source Obfuscation:** Critical assets like C2 URLs and encryption keys are baked into machine code, complicating reverse engineering efforts.

### 3. The Anchoring Spell (Deep Persistence)
The agent is designed to survive administrative scrutiny and system reboots.
* **Self-Migration:** Automatically moves to a stealth directory (e.g., system documentation paths) upon first execution.
* **Systemd Integration:** Upgrades to a system service with **Systemd Timers** to beacon at intervals, avoiding a constant, suspicious process footprint.

---

## 📁 Project Structure
```text
.
├── server.py
├── agent.py               # Agent source code - Should be compiled with Nuitka
└── commands.py            # Terminal for queueing commands
└── requirements.txt       # Python Dependencies - To be Added
```

---

## 🛠️ Installation & Setup

### 1. Preparing the Server
```bash
# Clone the repository
git clone https://github.com/polrVortex/CDT-RedTeam-Assignment.git
cd CDT-RedTeam-Assignment

# Install dependencies
pip install -r requirements.txt

# Start the Scrying Pool (Listener) - Includes the database
python3 server.py
```

### 2. Forging the Agent
To ensure environment independence, compile the agent into a standalone binary:
```bash
# Install Nuitka and a C compiler (GCC/Clang)
pip install nuitka

# Compile into a single machine-code file
python3 -m nuitka --standalone --onefile --remove-output agent.py
```

---

## Operational Flow
1.  **Staging:** The operator inserts an encrypted command into the SQL database.
2.  **Beaconing:** The target’s Systemd Timer wakes the **Familiar**.
3.  **Migration:** If the Familiar is in a "temp" directory, it installs itself globally and hides.
4.  **Execution:** The agent fetches the task, decrypts it, executes, and sends back the result.
5.  **Rest:** The agent terminates, leaving no active process for a sysadmin to find.

---

## Educational Disclaimer
This software is provided for educational and research purposes within a controlled laboratory environment. **Unauthorized access to computer systems is illegal.** The author (polrVortex) assumes no responsibility for misuse of this tool. Use it only where you have explicit, written permission.