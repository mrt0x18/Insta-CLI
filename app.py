import json
import sys
import re
import os
import time
import random
import logging
import threading
from instagrapi import Client
from colorama import init, Fore, Style
from datetime import datetime

# Optional desktop notifications (safe fallback)
try:
    from plyer import notification as sysnotif
    HAS_SYS_NOTIF = True
except Exception:
    HAS_SYS_NOTIF = False

init(autoreset=True)
logging.getLogger("instagrapi").setLevel(logging.CRITICAL)

cl = Client()

# ===== Visuals: Banner & Fake Connect =====
def banner():
    lines = [
        Fore.MAGENTA + "═════════════════════════════════════════════",
        Fore.CYAN + "      Instagram DM CLI  //  Merdo Edition",
        Fore.YELLOW + "      Coded by: Mertworkz",
        Fore.MAGENTA + "═════════════════════════════════════════════" + Style.RESET_ALL
    ]
    for l in lines:
        print(l)
        time.sleep(0.05)
    ascii = [
        Fore.CYAN + "   /\\/\\  _ __ ___  _ __   ___   ",
        Fore.CYAN + "  /    \\| '__/ _ \\| '_ \\ / _ \\  ",
        Fore.CYAN + " / /\\/\\ \\ | | (_) | | | | (_) | ",
        Fore.CYAN + " \\/    \\/_|  \\___/|_| |_|\\___/  " + Style.RESET_ALL
    ]
    for l in ascii:
        print(l)
        time.sleep(0.04)

def fake_connect():
    steps = [
        (Fore.CYAN,  "[*] init :: socket.bind -> 0x%X" % random.randint(0x1000, 0xFFFF)),
        (Fore.CYAN,  "[*] handshaking :: SYN -> ACK"),
        (Fore.CYAN,  "[*] negotiating :: cipher: neon-glitch-256"),
        (Fore.YELLOW,"[~] probing :: instagram.dm_gate"),
        (Fore.GREEN, "[+] link :: session #%s" % hex(random.randint(10000, 99999))),
        (Fore.CYAN,  "[*] route :: /dm/core"),
        (Fore.GREEN, "[+] status :: CONNECTED")
    ]
    for color, msg in steps:
        print(color + msg + Style.RESET_ALL)
        time.sleep(0.15)
    for i in range(3):
        jitter = random.uniform(12.3, 48.9)
        print(Fore.CYAN + f"[pkt] tx={i+1} jitter={jitter:.1f}ms integrity=OK" + Style.RESET_ALL)
        time.sleep(0.08)

# ===== Session Management =====
def ensure_login():
    global cl
    username = None
    password = None
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            cfg = json.load(f)
        username = cfg.get("username")
        password = cfg.get("password")
    username = os.getenv("IG_USERNAME", username)
    password = os.getenv("IG_PASSWORD", password)

    banner()
    fake_connect()
    if not username or not password:
        print(Fore.RED + "[!] Missing credentials. Provide config.json or IG_USERNAME/IG_PASSWORD env vars." + Style.RESET_ALL)
        return False
    try:
        if os.path.exists("session.json"):
            cl.load_settings("session.json")
        cl.login(username, password)
        cl.dump_settings("session.json")
        print(Fore.GREEN + "[+] Auth OK. Session cached." + Style.RESET_ALL)
        return True
    except Exception:
        try:
            print(Fore.YELLOW + "[~] Fallback login without cache..." + Style.RESET_ALL)
            cl.login(username, password)
            cl.dump_settings("session.json")
            print(Fore.GREEN + "[+] Auth OK. Session cached." + Style.RESET_ALL)
            return True
        except Exception as e:
            print(Fore.RED + "[!] Connection refused: " + str(e) + Style.RESET_ALL)
            return False

if not ensure_login():
    sys.exit(1)

# ===== Helpers: Text Formatting =====
def highlight_text(text):
    if not text:
        return ""
    text = re.sub(r"(@\w+)", Fore.CYAN + r"\1" + Style.RESET_ALL, text)
    text = re.sub(r"(https?://\S+)", Fore.GREEN + r"\1" + Style.RESET_ALL, text)
    return text

def truncate_text(text, limit=120):
    """Uzun mesajları listede kısaltır."""
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "...(truncated)"

# ===== Threads: Listing & Viewing =====
def list_threads():
    me = cl.account_info()
    threads = cl.direct_threads()
    print(Fore.MAGENTA + "\n--- Threads ---" + Style.RESET_ALL)
    unread_list = []

    for i, th in enumerate(threads, start=1):
        participants = ", ".join([u.username for u in th.users])
        if th.messages:
            last = sorted(th.messages, key=lambda m: m.timestamp)[-1]

            seen_status = Fore.RED + "[!]" + Style.RESET_ALL  # unread default
            if th.last_seen_at and me.pk in th.last_seen_at:
                seen_info = th.last_seen_at[me.pk]
                if hasattr(seen_info, "item_id") and last.id <= seen_info.item_id:
                    seen_status = Fore.GREEN + "[+]" + Style.RESET_ALL
                else:
                    unread_list.append((participants, getattr(last, "text", "")))
            else:
                unread_list.append((participants, getattr(last, "text", "")))

            if getattr(last, "text", None):
                short_text = truncate_text(last.text)
                content = f"{Fore.GREEN}Text{Style.RESET_ALL}: {highlight_text(short_text)}"
            elif getattr(last, "media", None):
                media_type = getattr(last.media, "media_type", None)
                if media_type == 1:
                    content = Fore.MAGENTA + "Photo" + Style.RESET_ALL
                elif media_type == 2:
                    content = Fore.YELLOW + "Video" + Style.RESET_ALL
                elif media_type == 13:
                    content = Fore.CYAN + "Reel/IGTV" + Style.RESET_ALL
                else:
                    content = Fore.RED + "Unsupported media" + Style.RESET_ALL
            else:
                content = Fore.RED + "Emoji" + Style.RESET_ALL
        else:
            content = Fore.RED + "No messages yet" + Style.RESET_ALL
            seen_status = ""

        print(f"{Fore.YELLOW}[{i}]{Style.RESET_ALL} {Fore.CYAN}{participants}{Style.RESET_ALL} | {content} {seen_status}")

    if unread_list:
        print(Fore.CYAN + "\n--- Unread Messages ---" + Style.RESET_ALL)
        for sender, msg in unread_list:
            msg_display = truncate_text(msg) if msg else "(media/none)"
            msg_display = highlight_text(msg_display)
            print(f"{Fore.YELLOW}{sender}{Style.RESET_ALL}: {Fore.CYAN}{msg_display}{Style.RESET_ALL}")
    else:
        print(Fore.GREEN + "\nAll messages read." + Style.RESET_ALL)

    # ==== Baseline: notifier sadece yeni item'ları bildirsin diye son item ID'leri kaydet
    try:
        for th in threads:
            if th.messages:
                last = sorted(th.messages, key=lambda m: m.timestamp)[-1]
                _baseline_last_item_per_thread[th.id] = last.id
    except Exception:
        pass

    return threads

def show_messages(thread):
    me = cl.account_info()
    all_users = list(thread.users)
    all_users.append(me)

    for msg in sorted(thread.messages, key=lambda m: m.timestamp):
        sender = next((u.username for u in all_users if u.pk == msg.user_id), str(msg.user_id))
        text = getattr(msg, "text", "")
        text = highlight_text(text)
        ts = datetime.fromtimestamp(msg.timestamp.timestamp()).strftime("%Y-%m-%d %H:%M")
        if text:
            print(f"{Fore.YELLOW}{sender}{Style.RESET_ALL} [{Fore.CYAN}{ts}{Style.RESET_ALL}]: {Fore.GREEN}{text}{Style.RESET_ALL}")
        elif getattr(msg, "media", None):
            media_type = getattr(msg.media, "media_type", None)
            if media_type == 1:
                print(f"{sender} [{ts}]: {Fore.MAGENTA}Photo{Style.RESET_ALL}")
            elif media_type == 2:
                print(f"{sender} [{ts}]: {Fore.YELLOW}Video{Style.RESET_ALL}")
            elif media_type == 13:
                print(f"{sender} [{ts}]: {Fore.CYAN}Reel/IGTV{Style.RESET_ALL}")
            else:
                print(f"{sender} [{ts}]: {Fore.RED}Emoji/Unsupported{Style.RESET_ALL}")
        else:
            print(f"{sender} [{ts}]: {Fore.RED}Emoji/Empty{Style.RESET_ALL}")

def view_thread(thread):
    print(Fore.CYAN + f"\n--- Chat with {', '.join([u.username for u in thread.users])} ---" + Style.RESET_ALL)
    print("Type message | refresh | exit | help")
    show_messages(thread)
    while True:
        text = input(Fore.CYAN + "root@merdo:/thread $ " + Style.RESET_ALL).strip()
        if text.lower() in ["exit", "logout"]:
            print(Fore.YELLOW + "Exiting chat mode..." + Style.RESET_ALL)
            break
        elif text.lower() == "refresh":
            try:
                thread = cl.direct_thread(thread.id)
                print(Fore.CYAN + "\n--- Refreshed Messages ---" + Style.RESET_ALL)
                show_messages(thread)
            except Exception as e:
                print(Fore.RED + "Refresh failed: " + str(e) + Style.RESET_ALL)
        elif text.lower() == "help":
            print("""
NAME
    chat - interactive DM thread

SYNOPSIS
    refresh   Reload messages
    exit      Leave chat mode
    help      Show this help
    <message> Send a message
""")
        elif text:
            try:
                cl.direct_send(text, thread_ids=[thread.id])
                thread = cl.direct_thread(thread.id)
                print(Fore.GREEN + "Message sent." + Style.RESET_ALL)
                show_messages(thread)
            except Exception as e:
                print(Fore.RED + "Message failed: " + str(e) + Style.RESET_ALL)

# ===== Robust username resolver (V1-only, no GQL) =====
def resolve_user_id(username):
    info = cl.user_info_by_username_v1(username)
    return info.pk

# ===== New Feature: Send by Username =====
def send_to_user(username, message):
    try:
        print(Fore.CYAN + f"[*] Resolving user '{username}'..." + Style.RESET_ALL)
        user_id = resolve_user_id(username)
        cl.direct_send(message, user_ids=[user_id])
        ack = random.randint(1000, 9999)
        latency = random.uniform(18.0, 63.0)
        print(Fore.GREEN + f"[+] Delivered :: ack={ack} latency={latency:.1f}ms -> @{username}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"[!] Failed to send message to {username}: {e}" + Style.RESET_ALL)

# ===== Notifier: selective background polling =====
NOTIFY_ENABLED = True             # 'notify on/off'
NOTIFY_INTERVAL = 20              # seconds
_baseline_last_item_per_thread = {}  # thread_id -> last_item_id when baseline set (via ls/sync)
_me_cache = {"pk": None, "username": None}

def _ensure_me():
    if _me_cache["pk"] is None:
        me = cl.account_info()
        _me_cache["pk"] = me.pk
        _me_cache["username"] = me.username

def _print_notif(line):
    # Minimal intrusion: newline + styled line, prompt akışını bozmadan
    print("\n" + line + Style.RESET_ALL)

def _desktop_notify(title, message):
    if HAS_SYS_NOTIF:
        try:
            sysnotif.notify(title=title, message=message, app_name="DM CLI", timeout=5)
        except Exception:
            pass

def sync_baseline():
    """Manuel baseline: mevcut son mesaj id'lerini kaydet, notifier sadece daha yenilerini bildirir."""
    try:
        threads = cl.direct_threads()
        for th in threads:
            if th.messages:
                last = sorted(th.messages, key=lambda m: m.timestamp)[-1]
                _baseline_last_item_per_thread[th.id] = last.id
        print(Fore.GREEN + "[+] Baseline synced. Yeni mesajlar bildirilecek." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"[!] Baseline sync failed: {e}" + Style.RESET_ALL)

def notifier_loop():
    _ensure_me()
    while True:
        try:
            if NOTIFY_ENABLED:
                threads = cl.direct_threads()
                for th in threads:
                    if not th.messages:
                        continue

                    last = sorted(th.messages, key=lambda m: m.timestamp)[-1]
                    base_id = _baseline_last_item_per_thread.get(th.id)

                    # Baseline yoksa bildirim üretme (önce ls/sync ile kur)
                    if base_id is None:
                        continue

                    # Yalnızca baseline'dan daha yeni item'larda bildirim üret
                    if last.id == base_id:
                        continue

                    # Kendi mesajını bildirme
                    if getattr(last, "user_id", None) == _me_cache["pk"]:
                        # Baseline'ı ileri sar (kendi gönderdiklerini de ilerletiyoruz ki bir sonraki geleni yakalayalım)
                        _baseline_last_item_per_thread[th.id] = last.id
                        continue

                    # Bildirim içeriği
                    participants = ", ".join([u.username for u in th.users])
                    sender_username = next((u.username for u in th.users if u.pk == last.user_id), f"id:{last.user_id}")

                    if getattr(last, "text", None):
                        payload = truncate_text(last.text, limit=100)
                        payload_disp = highlight_text(payload)
                        content = f"{Fore.GREEN}Text{Style.RESET_ALL}: {payload_disp}"
                        sys_msg_short = payload
                    elif getattr(last, "media", None):
                        mt = getattr(last.media, "media_type", None)
                        if mt == 1:
                            content = Fore.MAGENTA + "Photo" + Style.RESET_ALL
                            sys_msg_short = "Photo"
                        elif mt == 2:
                            content = Fore.YELLOW + "Video" + Style.RESET_ALL
                            sys_msg_short = "Video"
                        elif mt == 13:
                            content = Fore.CYAN + "Reel/IGTV" + Style.RESET_ALL
                            sys_msg_short = "Reel/IGTV"
                        else:
                            content = Fore.RED + "Emoji/Unsupported" + Style.RESET_ALL
                            sys_msg_short = "Emoji/Unsupported"
                    else:
                        content = Fore.RED + "Emoji/Empty" + Style.RESET_ALL
                        sys_msg_short = "Empty"

                    jitter = random.uniform(9.5, 44.0)
                    ack = random.randint(2000, 9999)
                    _print_notif(
                        Fore.MAGENTA +
                        f"[notif] rx ack={ack} jitter={jitter:.1f}ms :: @{sender_username} ➜ ({participants}) | {content}"
                    )

                    _desktop_notify("Instagram DM", f"@{sender_username}: {sys_msg_short}")

                    # Baseline'ı en yeni item'a ilerlet
                    _baseline_last_item_per_thread[th.id] = last.id

            time.sleep(NOTIFY_INTERVAL)
        except Exception as e:
            _print_notif(Fore.RED + f"[notif error] {e}")
            time.sleep(NOTIFY_INTERVAL)

# ===== Main Loop =====
def main():
    print(Fore.CYAN + "Welcome to DM CLI\n" + Style.RESET_ALL)
    print("Commands: ls | cat <num> | send <username> <message> | notify on/off | interval <sec> | sync | exit | help")

    # Start notifier in background
    t = threading.Thread(target=notifier_loop, daemon=True)
    t.start()

    ping_time = time.time()
    while True:
        if time.time() - ping_time > 45:
            print(Fore.CYAN + "[sys] heartbeat... OK" + Style.RESET_ALL)
            ping_time = time.time()

        cmd = input(Fore.CYAN + "root@merdo:~$ " + Style.RESET_ALL).strip()

        if cmd in ["list", "ls"]:
            list_threads()  # ls baseline'ı da otomatik günceller

        elif cmd.startswith("open ") or cmd.startswith("cat "):
            try:
                parts = cmd.split()
                if len(parts) < 2:
                    print(Fore.RED + "Usage: cat <num>" + Style.RESET_ALL)
                    continue
                num = int(parts[1])
                threads = cl.direct_threads()
                if 1 <= num <= len(threads):
                    view_thread(threads[num-1])
                else:
                    print(Fore.RED + "Invalid number." + Style.RESET_ALL)
            except ValueError:
                print(Fore.RED + "Invalid number format." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + "Error: " + str(e) + Style.RESET_ALL)

        elif cmd.startswith("send "):
            parts = cmd.split(" ", 2)
            if len(parts) < 3 or not parts[1] or not parts[2]:
                print(Fore.RED + "Usage: send <username> <message>" + Style.RESET_ALL)
            else:
                username, message = parts[1], parts[2]
                send_to_user(username, message)

        elif cmd.startswith("notify "):
            arg = cmd.split(" ", 1)[1].strip().lower() if len(cmd.split()) >= 2 else ""
            if arg in ["on", "enable", "true", "1"]:
                globals()["NOTIFY_ENABLED"] = True
                print(Fore.GREEN + "[+] Notifications enabled." + Style.RESET_ALL)
            elif arg in ["off", "disable", "false", "0"]:
                globals()["NOTIFY_ENABLED"] = False
                print(Fore.YELLOW + "[~] Notifications disabled." + Style.RESET_ALL)
            else:
                print(Fore.RED + "Usage: notify on|off" + Style.RESET_ALL)

        elif cmd.startswith("interval "):
            try:
                sec = int(cmd.split(" ", 1)[1].strip())
                if sec < 5:
                    print(Fore.RED + "[!] Minimum interval is 5s to avoid rate issues." + Style.RESET_ALL)
                else:
                    globals()["NOTIFY_INTERVAL"] = sec
                    print(Fore.GREEN + f"[+] Notification interval set to {sec}s." + Style.RESET_ALL)
            except Exception:
                print(Fore.RED + "Usage: interval <seconds>" + Style.RESET_ALL)

        elif cmd == "sync":
            sync_baseline()

        elif cmd == "help":
            print("""
NAME
    dm-cli - Instagram Direct Message CLI

SYNOPSIS
    ls                             Show DM threads (sets baseline)
    cat <num>                      Open a thread by number
    send <username> <msg>          Send a message directly to a user
    notify on|off                  Enable/disable background notifications
    interval <seconds>             Set notifier polling interval
    sync                           Manually set baseline from current state
    exit/logout                    Close the panel
    help                           Show this help

FLOW
    1) ls ile okunmamışları gör -> baseline set
    2) Arkada notifier sadece yeni gelenleri bildirir

EXAMPLES
    send mertworkz Selam bro, CLI'den yazıyorum!
    ls
    interval 15
    notify off
    sync
""")

        elif cmd in ["exit", "logout"]:
            print(Fore.YELLOW + "Session closed. Goodbye." + Style.RESET_ALL)
            break

        else:
            print(Fore.RED + "Unknown command. Type 'help' for options." + Style.RESET_ALL)

if __name__ == "__main__":
    main()

