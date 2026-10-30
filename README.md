# VoidNet

**SSH deception and monitoring platform built on Cowrie, Python, and Ubuntu.**

VoidNet turns a standard Cowrie SSH honeypot into an analyst-friendly monitoring console. It parses Cowrie JSON event logs to surface authentication attempts, captured credentials, executed commands, and session timelines in a single terminal interface.

<p>
<img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Ubuntu-E95420?style=flat-square&logo=ubuntu&logoColor=white" />
<img src="https://img.shields.io/badge/Cowrie-2C5364?style=flat-square&logo=gnubash&logoColor=white" />
<img src="https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black" />
<img src="https://img.shields.io/badge/VirtualBox-183A61?style=flat-square&logo=virtualbox&logoColor=white" />
</p>

---

## Overview

VoidNet is an educational blue-team / threat-monitoring project. An SSH honeypot is exposed inside an isolated lab network, and VoidNet reads the resulting Cowrie events to reconstruct attacker activity. It is intended for defensive research, not for production deployment.

## Features

- **Authentication monitoring** — tracks login attempts, successes, and failures.
- **Credential capture** — records usernames and passwords submitted to the honeypot.
- **Command analysis** — lists commands executed by intruders during sessions.
- **Session timelines** — groups events by session for chronological review.
- **Reporting** — exports summarized findings to `~/voidnet_reports` for further analysis.
- **Terminal UI** — colorized, readable console output for fast triage.

## Architecture

```text
        Attacker
           |
           v
   +-----------------+        logs        +-------------------+
   |  Cowrie honeypot | -----------------> | cowrie.json       |
   |  (port 22)       |                    | (JSON events)     |
   +-----------------+                     +---------+---------+
                                                     |
                                                     v
                                          +---------------------+
                                          | VoidNet (Python)    |
                                          | parse / aggregate   |
                                          +----------+----------+
                                                     |
                                          +----------v----------+
                                          | CLI reports / export|
                                          +---------------------+
```

Administrative SSH access is kept on a separate port (for example `22222`) so the honeypot on port `22` remains isolated.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3 |
| Honeypot | Cowrie |
| Operating System | Ubuntu Linux |
| Virtualization | VirtualBox |
| Log Format | JSON |
| Service Management | systemd, authbind |

## Project Structure

```text
Voidnet/
├── src/
│   └── voidnet.py        # monitoring console and report generator
├── screenshots/          # execution screenshots
├── README.md
├── LICENSE
└── .gitignore
```

## Getting Started

### Prerequisites

- Ubuntu virtual machine (VirtualBox or similar)
- Python 3
- Cowrie installed under `/home/cowrie/cowrie`
- `authbind` for binding to the privileged SSH port

### Configure Cowrie

1. Install Cowrie and confirm it writes JSON logs to
   `/home/cowrie/cowrie/var/log/cowrie/cowrie.json`.
2. Run the honeypot on port `22` and keep administrative access on a separate port.
3. Start Cowrie through its `systemd` service.

### Run VoidNet

```bash
cd /home/cowrie/cowrie
python3 /path/to/Voidnet/src/voidnet.py
```

VoidNet reads the Cowrie JSON log, aggregates events, and prints the monitoring summary. Exported reports are written to `~/voidnet_reports`.

## Disclaimer

This project is provided for **educational and defensive security research only**. Deploy it exclusively in an isolated lab environment that you own or are explicitly authorized to test. Never expose a honeypot on a network you do not control.

## Author

**Gokulakrishnan G** — Cybersecurity Analyst
[GitHub](https://github.com/Gokulgk6) · [LinkedIn](https://linkedin.com/in/gokulgk64)
