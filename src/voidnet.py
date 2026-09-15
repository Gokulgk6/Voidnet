#!/usr/bin/env python3
"""
VoidNet - SSH Deception & Monitoring Platform
"""

import os
import sys
import json
import time
import subprocess
import re
import csv
from collections import Counter, defaultdict
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
PROJECT_NAME = "VoidNet"
HOST = "192.168.56.105"
HONEYPOT_PORT = 22
WIDTH = 110

COWRIE_DIR = "/home/cowrie/cowrie"
COWRIE_JSON = f"{COWRIE_DIR}/var/log/cowrie/cowrie.json"
COWRIE_BIN = f"{COWRIE_DIR}/cowrie-env/bin/cowrie"
COWRIE_PID = f"{COWRIE_DIR}/var/run/cowrie.pid"
EXPORT_DIR = "/home/cowrie/voidnet_reports"

# ============================================================
# HACKER NEON COLORS & STYLES
# ============================================================
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

NEON_GREEN = "\033[38;5;46m"
NEON_CYAN = "\033[38;5;51m"
NEON_RED = "\033[38;5;196m"
NEON_YELLOW = "\033[38;5;226m"
NEON_MAGENTA = "\033[38;5;201m"
NEON_BLUE = "\033[38;5;33m"
GRAY = "\033[38;5;245m"
DARK_GRAY = "\033[38;5;238m"

def color(text, c):
    return f"{c}{text}{RESET}"

def bold_color(text, c):
    return f"{c}{BOLD}{text}{RESET}"

def dim_color(text, c):
    return f"{c}{DIM}{text}{RESET}"

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', str(text))

def pad(text, length):
    visual_len = len(strip_ansi(text))
    if visual_len >= length:
        return text
    return text + (" " * (length - visual_len))

def center(text, width):
    visual_len = len(strip_ansi(text))
    padding = max(0, width - visual_len)
    left = padding // 2
    right = padding - left
    return (" " * left) + text + (" " * right)

def clear():
    print("\033[2J\033[3J\033[H", end="")

def hide_cursor():
    print("\033[?25l", end="")

def show_cursor():
    print("\033[?25h", end="")

# ============================================================
# UI COMPONENTS
# ============================================================
def draw_box(title, lines, color_func=NEON_CYAN, width=WIDTH):
    title_str = f" {title} "
    left_pad = 2
    right_pad = width - 2 - len(title_str) - left_pad
    if right_pad < 0: right_pad = 0
    
    print(color("╔" + "═" * left_pad, color_func) + bold_color(title_str, color_func) + color("═" * right_pad + "╗", color_func))
    for line in lines:
        print(color("║", color_func) + pad(line, width - 2) + color("║", color_func))
    print(color("╚" + "═" * (width - 2) + "╝", color_func))

def draw_header():
    clear()
    print(color("╔" + "═" * (WIDTH - 2) + "╗", NEON_CYAN))
    
    logo_lines = [
        "██╗   ██╗ ██████╗ ██╗██████╗ ███╗   ██╗███████╗████████╗",
        "██║   ██║██╔═══██╗██║██╔══██╗████╗  ██║██╔════╝╚══██╔══╝",
        "██║   ██║██║   ██║██║██║  ██║██╔██╗ ██║█████╗     ██║   ",
        "╚██╗ ██╔╝██║   ██║██║██║  ██║██║╚██╗██║██╔══╝     ██║   ",
        " ╚████╔╝ ██████╔╝██║██████╗██║ ╚████║███████╗   ██║   ",
        "  ╚═══╝   ╚═════╝ ╚═╝╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   "
    ]
    
    for line in logo_lines:
        print(color("║", NEON_CYAN) + center(bold_color(line, NEON_GREEN), WIDTH - 2) + color("║", NEON_CYAN))
    
    print(color("║", NEON_CYAN) + center(bold_color("S S H   D E C E P T I O N   &   M O N I T O R I N G", NEON_CYAN), WIDTH - 2) + color("║", NEON_CYAN))
    print(color("╚" + "═" * (WIDTH - 2) + "╝", NEON_CYAN))
    print()

def section_header(title, symbol="◆"):
    print()
    print(bold_color(f"{symbol} {title}", NEON_MAGENTA))
    print(color("─" * WIDTH, DARK_GRAY))

def draw_progress_bar(value, max_val, width=25, bar_color=NEON_RED):
    if max_val == 0:
        percentage = 0
    else:
        percentage = min(100, int((value / max_val) * 100))
    
    filled = int((percentage / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{color(bar, bar_color)}] {percentage:3d}%"

# ============================================================
# CORE LOGIC
# ============================================================
def is_cowrie_running():
    try:
        result = subprocess.run(["pgrep", "-f", "twistd.*cowrie"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return True
        result2 = subprocess.run(["pgrep", "-f", "cowrie"], capture_output=True, text=True, timeout=2)
        if result2.returncode == 0 and result2.stdout.strip():
            return True
        if os.path.exists(COWRIE_PID):
            with open(COWRIE_PID, "r") as f:
                pid = f.read().strip()
            if os.path.exists(f"/proc/{pid}"):
                return True
    except Exception:
        pass
    return False

def control_cowrie(action):
    if not os.path.exists(COWRIE_BIN):
        return False, "Cowrie binary not found."
    
    try:
        subprocess.run([COWRIE_BIN, action], cwd=COWRIE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        time.sleep(2)
        return True, f"Cowrie {action}ed successfully."
    except Exception as e:
        return False, f"Failed to {action} Cowrie: {e}"

def load_events():
    events = []
    if not os.path.exists(COWRIE_JSON):
        return events
    try:
        with open(COWRIE_JSON, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    event = json.loads(line)
                    if isinstance(event, dict):
                        events.append(event)
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeError):
        pass
    return events

def get_advanced_stats():
    events = load_events()
    
    stats = {
        "total_events": len(events),
        "sessions": len([e for e in events if e.get("eventid") == "cowrie.session.closed"]),
        "login_success": len([e for e in events if e.get("eventid") == "cowrie.login.success"]),
        "login_failed": len([e for e in events if e.get("eventid") == "cowrie.login.failed"]),
        "commands": len([e for e in events if e.get("eventid") == "cowrie.command.input"]),
        "downloads": len([e for e in events if e.get("eventid") == "cowrie.session.file_download"]),
    }
    
    ips = [e.get("src_ip") for e in events if e.get("src_ip")]
    stats["top_ips"] = Counter(ips).most_common(10)
    usernames = [e.get("username") for e in events if e.get("username")]
    stats["top_usernames"] = Counter(usernames).most_common(10)
    passwords = [e.get("password") for e in events if e.get("password")]
    stats["top_passwords"] = Counter(passwords).most_common(10)
    commands = [e.get("input") for e in events if e.get("eventid") == "cowrie.command.input" and e.get("input")]
    stats["top_commands"] = Counter(commands).most_common(10)
    
    timeline = defaultdict(int)
    for event in events:
        ts = event.get("timestamp", "")
        if ts:
            hour = ts[:13]
            timeline[hour] += 1
    stats["timeline"] = dict(sorted(timeline.items())[-24:])
    
    unique_ips = len(set(ips))
    repeat_attackers = sum(1 for ip, count in Counter(ips).items() if count > 3)
    stats["unique_attackers"] = unique_ips
    stats["repeat_attackers"] = repeat_attackers
    
    threat_score = stats["login_failed"] * 1 + stats["commands"] * 2 + stats["downloads"] * 5 + repeat_attackers * 10
    
    if threat_score < 50: stats["threat_level"] = ("LOW", NEON_GREEN)
    elif threat_score < 150: stats["threat_level"] = ("MEDIUM", NEON_YELLOW)
    elif threat_score < 300: stats["threat_level"] = ("HIGH", NEON_RED)
    else: stats["threat_level"] = ("CRITICAL", NEON_RED)
    
    return stats

# ============================================================
# NEW FEATURES: EXPORT & CONTROL
# ============================================================
def export_data():
    clear()
    draw_header()
    section_header("DATA EXPORT CENTER")
    
    events = load_events()
    if not events:
        draw_box("EXPORT STATUS", [bold_color("No events found to export.", NEON_RED)], NEON_RED)
        input(color("\nPress ENTER to return...", GRAY))
        return

    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(EXPORT_DIR, f"voidnet_events_{timestamp}.csv")
    
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Event ID", "Source IP", "Username", "Password", "Command Input"])
            
            for e in events:
                writer.writerow([
                    e.get("timestamp", ""),
                    e.get("eventid", ""),
                    e.get("src_ip", ""),
                    e.get("username", ""),
                    e.get("password", ""),
                    e.get("input", "")
                ])
        
        draw_box("EXPORT SUCCESS", [
            f"  {bold_color('File Saved:', NEON_GREEN)} {csv_path}",
            f"  {bold_color('Total Records:', NEON_GREEN)} {len(events)}"
        ], NEON_GREEN)
    except Exception as ex:
        draw_box("EXPORT FAILED", [bold_color(f"Error: {ex}", NEON_RED)], NEON_RED)
        
    input(color("\nPress ENTER to return to Command Center...", GRAY))

def honeypot_control():
    clear()
    draw_header()
    section_header("HONEYPOT ENGINE CONTROL")
    
    is_running = is_cowrie_running()
    status_color = NEON_GREEN if is_running else NEON_RED
    status_text = "ACTIVE" if is_running else "INACTIVE"
    
    draw_box("CURRENT STATUS", [
        f"  {bold_color('Engine Status:', NEON_CYAN)} {bold_color(status_text, status_color)}",
        f"  {bold_color('Binary Path:', NEON_CYAN)} {COWRIE_BIN}"
    ], NEON_CYAN)
    
    print()
    print(f"  {bold_color('[1]', NEON_CYAN)} Start Honeypot Engine")
    print(f"  {bold_color('[2]', NEON_RED)} Stop Honeypot Engine")
    print(f"  {bold_color('[3]', NEON_YELLOW)} Restart Honeypot Engine")
    print(f"  {bold_color('[0]', GRAY)} Return to Menu")
    print()
    
    choice = input(bold_color("VOIDNET :: CONTROL > ", NEON_MAGENTA)).strip()
    
    if choice == "1":
        success, msg = control_cowrie("start")
    elif choice == "2":
        success, msg = control_cowrie("stop")
    elif choice == "3":
        control_cowrie("stop")
        time.sleep(1)
        success, msg = control_cowrie("start")
    else:
        return
        
    c = NEON_GREEN if success else NEON_RED
    draw_box("ACTION RESULT", [bold_color(f"  {msg}", c)], c)
    input(color("\nPress ENTER to continue...", GRAY))

# ============================================================
# VIEWS
# ============================================================
def enhanced_dashboard():
    draw_header()
    print(bold_color(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"), GRAY))
    section_header("SECURITY OPERATIONS CONSOLE")

    active = is_cowrie_running()
    stats = get_advanced_stats()
    threat_level, threat_color = stats["threat_level"]
    
    sys_rows = [
        pad(bold_color("VoidNet", NEON_CYAN), 18) + bold_color("● ACTIVE", NEON_GREEN),
        pad(bold_color("Cowrie", NEON_CYAN), 18) + (bold_color("● ACTIVE", NEON_GREEN) if active else bold_color("● INACTIVE", NEON_RED)),
        pad(bold_color("Environment", NEON_CYAN), 18) + bold_color("● ISOLATED", NEON_GREEN),
        pad(bold_color("Defense Mode", NEON_CYAN), 18) + bold_color("● ENABLED", NEON_GREEN),
    ]
    
    net_rows = [
        pad(bold_color("HONEYPOT PORT", NEON_CYAN), 18) + bold_color(str(HONEYPOT_PORT), NEON_YELLOW),
        pad(bold_color("HOST", NEON_CYAN), 18) + bold_color(HOST, NEON_GREEN),
        pad(bold_color("PROTOCOL", NEON_CYAN), 18) + bold_color("SSH", NEON_YELLOW),
        pad(bold_color("INTERFACE", NEON_CYAN), 18) + bold_color("HOST-ONLY", NEON_GREEN),
    ]
    
    threat_rows = [
        pad(bold_color("THREAT LEVEL", NEON_CYAN), 18) + bold_color(f"● {threat_level}", threat_color),
        pad(bold_color("UNIQUE ATTACKERS", NEON_CYAN), 18) + bold_color(str(stats["unique_attackers"]), NEON_YELLOW),
        pad(bold_color("REPEAT OFFENDERS", NEON_CYAN), 18) + bold_color(str(stats["repeat_attackers"]), NEON_RED),
        pad(bold_color("TOTAL ATTACKS", NEON_CYAN), 18) + bold_color(str(stats["total_events"]), NEON_RED),
    ]

    gap = 4
    box_w = (WIDTH - gap) // 3
    
    def make_box(title, rows, color_func=NEON_CYAN):
        lines = []
        title_str = f" {title} "
        left = 2
        right = box_w - 2 - len(title_str) - left
        if right < 0: right = 0
        lines.append(color("╔" + "═" * left, color_func) + bold_color(title_str, color_func) + color("═" * right + "╗", color_func))
        for row in rows:
            lines.append(color("║", color_func) + pad(row, box_w - 2) + color("║", color_func))
        lines.append(color("╚" + "═" * (box_w - 2) + "╝", color_func))
        return lines

    left = make_box("SYSTEM", sys_rows, NEON_CYAN)
    center_box = make_box("NETWORK", net_rows, NEON_GREEN)
    right = make_box("THREATS", threat_rows, NEON_RED)
    
    max_h = max(len(left), len(center_box), len(right))
    for i in range(max_h):
        l = left[i] if i < len(left) else " " * box_w
        c = center_box[i] if i < len(center_box) else " " * box_w
        r = right[i] if i < len(right) else " " * box_w
        print(l + (" " * gap) + c + (" " * gap) + r)

    # SINGLE ROW TELEMETRY - Clean and Error-Free
    print()
    sessions_str = f"{stats['sessions']:3d}"
    success_str = f"{stats['login_success']:3d}"
    failed_str = f"{stats['login_failed']:3d}"
    commands_str = f"{stats['commands']:3d}"
    downloads_str = f"{stats['downloads']:3d}"
    events_str = f"{stats['total_events']:3d}"
    
    tel_row = (
        f"  {bold_color('SESSIONS', NEON_CYAN)}: {bold_color(sessions_str, NEON_GREEN)}  │  "
        f"{bold_color('SUCCESS', NEON_GREEN)}: {bold_color(success_str, NEON_GREEN)}  │  "
        f"{bold_color('FAILED', NEON_RED)}: {bold_color(failed_str, NEON_RED)}  │  "
        f"{bold_color('COMMANDS', NEON_YELLOW)}: {bold_color(commands_str, NEON_YELLOW)}  │  "
        f"{bold_color('DOWNLOADS', NEON_MAGENTA)}: {bold_color(downloads_str, NEON_MAGENTA)}  │  "
        f"{bold_color('EVENTS', NEON_BLUE)}: {bold_color(events_str, NEON_BLUE)}"
    )
    draw_box("SECURITY TELEMETRY", [tel_row], NEON_BLUE)

    print()
    if stats["top_ips"]:
        attacker_rows = []
        for ip, count in stats["top_ips"][:5]:
            bar = draw_progress_bar(count, stats["top_ips"][0][1], width=25, bar_color=NEON_RED)
            attacker_rows.append(f"  {pad(ip, 18)} {bar}")
        draw_box("TOP ATTACKERS", attacker_rows, NEON_RED)

    proj_rows = [
        pad(bold_color("PROJECT", NEON_CYAN), 20) + ": VoidNet",
        pad(bold_color("PLATFORM", NEON_CYAN), 20) + ": Ubuntu Server (VirtualBox)",
        pad(bold_color("HONEYPOT", NEON_CYAN), 20) + ": Cowrie Enhanced",
        pad(bold_color("PURPOSE", NEON_CYAN), 20) + ": " + bold_color("Defensive Research", NEON_GREEN),
    ]
    print()
    draw_box("PROJECT INFO", proj_rows, NEON_CYAN)
    
    print()
    section_header("COMMAND CENTER")
    cmds = [
        ("1", "Dashboard", "Refresh overview", NEON_CYAN),
        ("2", "Live Monitor", "Real-time event stream", NEON_MAGENTA),
        ("3", "Attack Analytics", "Advanced threat analysis", NEON_GREEN),
        ("4", "Top Attackers", "Leaderboard & stats", NEON_RED),
        ("5", "Credentials", "Captured usernames/passwords", NEON_YELLOW),
        ("6", "Commands", "Attack command intelligence", NEON_BLUE),
        ("7", "Timeline", "Attack patterns over time", NEON_MAGENTA),
        ("8", "Export Data", "Save events to CSV report", NEON_CYAN),
        ("9", "Engine Control", "Start/Stop/Restart Cowrie", NEON_YELLOW),
        ("0", "Exit", "Shutdown interface", NEON_RED),
    ]
    for num, title, desc, c in cmds:
        print(f"  {bold_color(f'[{num}]', c):6} {pad(title, 24):26} {dim_color(desc, GRAY)}")
    print()

def attack_analytics():
    clear()
    draw_header()
    section_header("ADVANCED THREAT ANALYTICS")
    stats = get_advanced_stats()
    total_logins = stats['login_success'] + stats['login_failed']
    success_rate = f"{(stats['login_success'] / total_logins) * 100:.1f}%" if total_logins > 0 else "0%"
    
    summary_rows = [
        f"  {bold_color('Total Events', NEON_CYAN):25} {bold_color(str(stats['total_events']), NEON_GREEN)}",
        f"  {bold_color('Active Sessions', NEON_CYAN):25} {bold_color(str(stats['sessions']), NEON_GREEN)}",
        f"  {bold_color('Login Attempts', NEON_CYAN):25} {bold_color(str(total_logins), NEON_YELLOW)}",
        f"  {bold_color('Success Rate', NEON_CYAN):25} {bold_color(success_rate, NEON_GREEN)}",
        f"  {bold_color('Commands Executed', NEON_CYAN):25} {bold_color(str(stats['commands']), NEON_YELLOW)}",
        f"  {bold_color('File Downloads', NEON_CYAN):25} {bold_color(str(stats['downloads']), NEON_MAGENTA)}",
    ]
    draw_box("ATTACK SUMMARY", summary_rows, NEON_CYAN)
    
    print()
    if stats["timeline"]:
        print(bold_color("ATTACK TIMELINE (Last 24 Hours)", NEON_CYAN))
        print(color("─" * WIDTH, DARK_GRAY))
        for hour, count in list(stats["timeline"].items())[-10:]:
            bar = "█" * min(count, 50)
            print(f"  {hour:20} {color(bar, NEON_CYAN)} {bold_color(str(count), NEON_GREEN)}")
    input(color("\nPress ENTER to return to Command Center...", GRAY))

def top_attackers_view():
    clear()
    draw_header()
    section_header("TOP ATTACKERS LEADERBOARD")
    stats = get_advanced_stats()
    if stats["top_ips"]:
        rows = []
        max_count = stats["top_ips"][0][1]
        for rank, (ip, count) in enumerate(stats["top_ips"][:10], 1):
            percentage = (count / max_count) * 100
            bar = "█" * int(percentage / 3)
            medal = bold_color("1.", NEON_YELLOW) if rank == 1 else bold_color("2.", GRAY) if rank == 2 else bold_color("3.", NEON_RED) if rank == 3 else f"{rank}."
            rows.append(f"  {medal} {pad(ip, 18)} {color(bar, NEON_RED)} {bold_color(f'{count:4d}', NEON_GREEN)} attacks")
        draw_box("TOP 10 ATTACKERS", rows, NEON_RED)
    else:
        draw_box("NO DATA", [color("  No attackers detected yet.", GRAY)], NEON_CYAN)
    input(color("\nPress ENTER to return to Command Center...", GRAY))

def credentials_view():
    clear()
    draw_header()
    section_header("CAPTURED CREDENTIALS")
    stats = get_advanced_stats()
    print(bold_color("TOP USERNAMES", NEON_CYAN))
    print(color("─" * WIDTH, DARK_GRAY))
    if stats["top_usernames"]:
        for username, count in stats["top_usernames"][:10]:
            bar = "█" * min(count, 40)
            print(f"  {pad(username, 20)} {color(bar, NEON_CYAN)} {bold_color(str(count), NEON_GREEN)}")
    else: print(color("  No credentials captured yet.", GRAY))
    
    print()
    print(bold_color("TOP PASSWORDS", NEON_RED))
    print(color("─" * WIDTH, DARK_GRAY))
    if stats["top_passwords"]:
        for password, count in stats["top_passwords"][:10]:
            bar = "█" * min(count, 40)
            display_pass = password if len(password) <= 15 else password[:12] + "..."
            print(f"  {pad(display_pass, 20)} {color(bar, NEON_RED)} {bold_color(str(count), NEON_YELLOW)}")
    else: print(color("  No passwords captured yet.", GRAY))
    input(color("\nPress ENTER to return to Command Center...", GRAY))

def commands_view():
    clear()
    draw_header()
    section_header("COMMAND INTELLIGENCE")
    stats = get_advanced_stats()
    if stats["top_commands"]:
        rows = []
        max_count = stats["top_commands"][0][1]
        for cmd, count in stats["top_commands"][:15]:
            display_cmd = cmd if len(cmd) <= 40 else cmd[:37] + "..."
            bar = "█" * int((count / max_count) * 30)
            rows.append(f"  {pad(display_cmd, 42)} {color(bar, NEON_YELLOW)} {bold_color(str(count), NEON_GREEN)}")
        draw_box("TOP COMMANDS", rows, NEON_YELLOW)
    else:
        draw_box("NO DATA", [color("  No commands captured yet.", GRAY)], NEON_CYAN)
    input(color("\nPress ENTER to return to Command Center...", GRAY))

def timeline_view():
    clear()
    draw_header()
    section_header("ATTACK TIMELINE & PATTERNS")
    stats = get_advanced_stats()
    if stats["timeline"]:
        print(bold_color("EVENTS PER HOUR", NEON_CYAN))
        print(color("─" * WIDTH, DARK_GRAY))
        max_val = max(stats["timeline"].values())
        for hour, count in list(stats["timeline"].items())[-20:]:
            bar_len = int((count / max_val) * 50) if max_val > 0 else 0
            bar = "█" * bar_len
            hour_display = hour.replace("T", " ")
            print(f"  {hour_display:18} {color(bar, NEON_CYAN)} {bold_color(str(count), NEON_GREEN)}")
    else:
        draw_box("NO DATA", [color("  No timeline data available.", GRAY)], NEON_CYAN)
    input(color("\nPress ENTER to return to Command Center...", GRAY))

def live_monitor():
    clear()
    draw_box("LIVE MONITOR", [
        bold_color("REAL-TIME COWRIE SECURITY TELEMETRY", NEON_MAGENTA),
        color("Press Ctrl+C to stop monitoring and return to menu.", NEON_YELLOW)
    ], NEON_MAGENTA)
    print()
    
    if not os.path.exists(COWRIE_JSON):
        draw_box("STATUS", [bold_color("Cowrie JSON log not found.", NEON_RED)], NEON_RED)
        input(color("\nPress ENTER to return...", GRAY))
        return

    print(bold_color("● MONITORING ACTIVE", NEON_GREEN))
    print(color("─" * WIDTH, DARK_GRAY))
    
    try:
        with open(COWRIE_JSON, "r", encoding="utf-8") as log:
            log.seek(0, os.SEEK_END)
            while True:
                line = log.readline()
                if not line:
                    time.sleep(0.35)
                    continue
                line = line.strip()
                if not line: continue
                try: event = json.loads(line)
                except json.JSONDecodeError: continue
                
                eventid = str(event.get("eventid", "unknown"))
                src_ip = str(event.get("src_ip", "-"))
                ts = str(event.get("timestamp", "")).replace("T", " ").split(".")[0].replace("Z", "")
                
                if eventid == "cowrie.login.success": c, label = NEON_GREEN, "LOGIN SUCCESS"
                elif eventid == "cowrie.login.failed": c, label = NEON_RED, "LOGIN FAILED"
                elif eventid == "cowrie.command.input": c, label = NEON_YELLOW, "COMMAND"
                elif eventid == "cowrie.session.connect": c, label = NEON_CYAN, "SESSION OPEN"
                elif eventid == "cowrie.session.closed": c, label = NEON_BLUE, "SESSION CLOSED"
                else: c, label = GRAY, "EVENT"
                
                cmd = ""
                if eventid == "cowrie.command.input":
                    cmd = str(event.get("input", ""))
                    if len(cmd) > 30: cmd = cmd[:27] + "..."
                
                out = f"  {ts:19} {pad(bold_color(label, c), 16)} {pad(src_ip, 16)}"
                if cmd: out += f"  {bold_color('>', NEON_MAGENTA)} {color(cmd, NEON_YELLOW)}"
                print(out, flush=True)
                
    except KeyboardInterrupt:
        print()
        print(bold_color("● MONITORING STOPPED", NEON_YELLOW))
        time.sleep(0.8)
        return

def main_menu():
    while True:
        enhanced_dashboard()
        try:
            choice = input(bold_color("VOIDNET :: ", NEON_GREEN) + bold_color("SELECT OPTION > ", NEON_MAGENTA)).strip()
        except KeyboardInterrupt:
            print()
            print(bold_color("\nVoidNet is still running. Use option 0 to exit.", NEON_YELLOW))
            time.sleep(1)
            continue
            
        if choice == "1": continue
        elif choice == "2": live_monitor()
        elif choice == "3": attack_analytics()
        elif choice == "4": top_attackers_view()
        elif choice == "5": credentials_view()
        elif choice == "6": commands_view()
        elif choice == "7": timeline_view()
        elif choice == "8": export_data()
        elif choice == "9": honeypot_control()
        elif choice == "0":
            clear()
            draw_box("VOIDNET", [
                bold_color("SECURE CONSOLE SHUTDOWN", NEON_MAGENTA),
                color("Defensive monitoring interface closed.", GRAY)
            ], NEON_MAGENTA)
            print()
            return
        else:
            print()
            print(bold_color("Invalid selection.", NEON_RED))
            time.sleep(1)

def main():
    hide_cursor()
    clear()
    print(bold_color("Initializing VoidNet Security Console...", NEON_CYAN))
    time.sleep(0.5)
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        print(bold_color("Use option 0 to exit VoidNet.", NEON_YELLOW))
    finally:
        show_cursor()
        clear()

if __name__ == "__main__":
    main()
