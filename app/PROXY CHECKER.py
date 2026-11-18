import threading
import sys
import re
import os

try:
    import requests
except ImportError:
    print("[!] Python package 'requests' is missing.")
    print("    Install it with:  python3 -m pip install requests")
    sys.exit(1)

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:  # Linux/macOS without colorama: plain text still works
    class _Blank:
        def __getattr__(self, _name):
            return ""
    Fore = Style = _Blank()

    def init(*args, **kwargs):
        pass

# Colors aur Lock initialize
file_lock = threading.Lock()
stat_lock = threading.Lock()
url_lock = threading.Lock()

# Shared progress counters (for the bar)
checked_count = 0
active_count = 0
total_count = 0
BAR_MODE = False
OUTPUT_FILE = "active.txt"  # where actives get saved ("survivors.txt" in verify mode)

# Test endpoints - rotate between them so one site never rate-limits us
CHECK_URLS = [
    "http://checkip.amazonaws.com",
    "http://icanhazip.com",
    "http://api.ipify.org",
    "http://httpbin.org/ip",
    "http://httpbingo.org/ip",
    "http://ifconfig.me/ip",
]
url_index = 0

# How many different endpoints a proxy may try. Hunting uses 1 (fast);
# verify uses 3, so a good proxy is never deleted just because one site
# was slow, blocked, or rate-limited at that moment.
TRIES = 1

IP_RE = re.compile(r'\b\d{1,3}(?:\.\d{1,3}){3}\b')

logo = Fore.GREEN + '''
╔══════════════════════════════════════════════════════════════════════════════════════╗
║        ███╗   ███╗ ██████╗      ██╗     ███████╗ ██████╗ ██╗████████╗                ║
║        ████╗ ████║██╔════╝      ██║     ██╔════╝██╔════╝ ██║╚══██╔══╝                ║
║        ██╔████╔██║██║           ██║     █████╗  ██║  ███╗██║   ██║                   ║
║        ██║╚██╔╝██║██║           ██║     ██╔══╝  ██║   ██║██║   ██║                   ║
║        ██║ ╚═╝ ██║╚██████╗      ███████╗███████╗╚██████╔╝██║   ██║                   ║
║        ╚═╝     ╚═╝ ╚═════╝      ╚══════╝╚══════╝ ╚═════╝ ╚═╝   ╚═╝                   ║
║                                 MC LEGITS CHECKER                                    ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
'''

def next_check_url():
    """Give each proxy the next test endpoint in rotation."""
    global url_index
    with url_lock:
        u = CHECK_URLS[url_index % len(CHECK_URLS)]
        url_index += 1
        return u

def draw_bar():
    """Redraw the one-line progress bar (only in bar mode)."""
    if not BAR_MODE or total_count == 0:
        return
    done = checked_count
    frac = done / total_count
    width = 30
    filled = int(width * frac)
    bar = "#" * filled + "-" * (width - filled)
    pct = int(frac * 100)
    line = (f"{Fore.GREEN}[{bar}]{Fore.WHITE} {done}/{total_count} ({pct}%)"
            f"{Fore.CYAN} Active: {active_count}")
    sys.stdout.write("\r" + line + "   ")
    sys.stdout.flush()

def check_proxy(proxy):
    global checked_count, active_count
    proxy = proxy.strip()
    if not proxy:
        with stat_lock:
            checked_count += 1
            draw_bar()
        return

    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }

    is_active = False
    for attempt in range(max(1, TRIES)):
        try:
            # Rotating endpoint, 5 second timeout
            response = requests.get(next_check_url(), proxies=proxies, timeout=5)
            if response.status_code == 200 and IP_RE.search(response.text or ""):
                is_active = True
                break
        except Exception:
            pass

    if is_active:
        with file_lock:
            with open(OUTPUT_FILE, "a") as f:
                f.write(proxy + "\n")
        with stat_lock:
            active_count += 1
        if not BAR_MODE:
            print(f"{Fore.CYAN}[+]{Fore.GREEN} Active  {Fore.WHITE}-> {proxy}")
    else:
        # Agar dead hai toh bas print karega
        if not BAR_MODE:
            print(f"{Fore.RED}[-]{Fore.YELLOW} Dead    {Fore.WHITE}-> {proxy}")

    with stat_lock:
        checked_count += 1
        draw_bar()

def run_threads(proxies):
    threads = []
    # Ek baar mein 50 proxies check karega (Speed fast karne ke liye)
    max_threads = 50

    for p in proxies:
        t = threading.Thread(target=check_proxy, args=(p,))
        t.daemon = True  # Taaki main program ke saath threads manage hon
        threads.append(t)
        t.start()

        # Threads limit control
        if len(threads) >= max_threads:
            for t in threads:
                t.join()
            threads = []

    # Jo bache huye threads hain unka wait karna
    for t in threads:
        t.join()

def bar_mode_run(file_path, bar, verify=False):
    """Non-interactive mode: python "PROXY CHECKER.py" <file> bar [verify]
       Shows a live progress bar instead of per-proxy lines.
       verify: leaves active.txt untouched, saves survivors to survivors.txt"""
    global BAR_MODE, total_count, OUTPUT_FILE, TRIES
    if not os.path.exists(file_path):
        print(f"[!] File not found: {file_path}")
        return
    with open(file_path, "r") as f:
        proxies = f.read().splitlines()
    if not proxies:
        print("[!] File is empty!")
        return

    OUTPUT_FILE = "survivors.txt" if verify else "active.txt"
    TRIES = 3 if verify else 1
    BAR_MODE = bar
    total_count = len(proxies)
    print(f"Checking {total_count} proxies (50 threads at a time)...")
    if verify:
        print("Verify mode: each proxy gets up to 3 different endpoints.")
    run_threads(proxies)
    sys.stdout.write("\n")
    print("-" * 60)
    print(f"Checked: {checked_count} | Active: {active_count} | Dead: {checked_count - active_count}")
    if verify:
        print("Survivors saved to survivors.txt (active.txt untouched)")
    else:
        print("Active proxies saved to active.txt")

def use_data_dir():
    """When run directly (double-click), use prox\\data for active.txt etc."""
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(os.path.dirname(here), "data")
    if os.path.isdir(data):
        os.chdir(data)


def main():
    # Arg mode (used by PROXY finder / _hunt.ps1): no prompts, optional bar
    args = sys.argv[1:]
    if args:
        bar_mode_run(args[0], bar=("bar" in args or "--bar" in args), verify=("verify" in args))
        return

    use_data_dir()
    os.system('cls' if os.name == 'nt' else 'clear') # Screen saaf karne ke liye
    print(logo)

    file_path = input(f"{Fore.BLUE}Proxies file ka naam (e.g. proxies.txt): ").strip()

    if not os.path.exists(file_path):
        print(f"{Fore.RED}\n[!] Error: '{file_path}' file nahi mili! Check karo file name sahi hai?")
        input("\nEnter dabao band karne ke liye...")
        return

    with open(file_path, "r") as f:
        proxies = f.read().splitlines()

    if not proxies:
        print(f"{Fore.RED}\n[!] File khali hai!")
        input("\nEnter dabao band karne ke liye...")
        return

    print(f"{Fore.MAGENTA}\nTotal Proxies Loaded: {len(proxies)}")
    print(f"{Fore.WHITE}Checking started... Thora sabar karein.\n" + "-"*60)

    run_threads(proxies)

    print("-"*60)
    print(f"\n{Fore.GREEN}[FINISH] Checking complete!")
    print(f"{Fore.CYAN}Active proxies 'active.txt' mein save ho gayi hain.")

    # Ye line program ko foran band hone se rokegi
    input(f"\n{Fore.YELLOW}Press ENTER to exit...")

if __name__ == "__main__":
    main()
