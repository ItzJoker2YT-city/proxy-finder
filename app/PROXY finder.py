# ============================================================
#  PROXY FINDER
#  Asks how many ACTIVE proxies you want, then hunts fresh ones
#  (_hunt.ps1 on Windows, _hunt.py on Linux/macOS) + verifies them
#  with PROXY CHECKER.py until active.txt has that many.
# ============================================================

import os
import subprocess
import sys

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

# Folder layout:
#   prox\            <- PROXY finder.bat / PROXY finder.sh live here
#   prox\app\        <- these scripts
#   prox\data\       <- active.txt, tested.txt, new.txt, sources.txt ...
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
PS1_PATH = os.path.join(APP_DIR, "_hunt.ps1")
HUNT_PY = os.path.join(APP_DIR, "_hunt.py")
# Windows uses the PowerShell engine; Linux/macOS use the Python one.
USE_PS1 = os.name == "nt" and os.path.exists(PS1_PATH)

logo = Fore.GREEN + r'''
 _____ _____ _____ _____         _____ _____
|  __ \|  ___/  __ \  _  |       |  _  /  ___|
| |  \/| |_  | /  \/ | | |_   _  | | | \ `--.
| | __ |  _|| |   | | | |\ \ / / | | | |`--. \
| |_\ \| |  | \/\ /\ \_/ / V V / \ \_/ /\__/ /
 \____/\_|   \____/ \___/ \_/\_/   \___/\____/
       FINDER  ->  hunt + check for you
''' + Style.RESET_ALL


def load_active(folder):
    """Return unique active proxies from active.txt (order kept)."""
    path = os.path.join(folder, "active.txt")
    if not os.path.exists(path):
        return []
    seen = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            p = line.strip()
            if p and p not in seen:
                seen.append(p)
    return seen


def wait_any_key():
    """Keep the window open until the user presses a key / Enter."""
    print(f"{Fore.YELLOW}\nPress any key to close...")
    try:
        import msvcrt
    except ImportError:
        # Linux / macOS: no getch, Enter does the job
        try:
            input()
        except Exception:
            pass
        return
    try:
        if sys.stdin.isatty():
            msvcrt.getch()  # real console: literally any key closes
        else:
            input()  # no console (piped/IDE run): wait on stdin instead
    except Exception:
        pass  # no console available - just exit quietly


def run_hunt(target=None, verify=False):
    """Run the hunt engine for this OS (PowerShell on Windows, Python elsewhere)."""
    if USE_PS1:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1_PATH]
        if verify:
            cmd.append("-VerifyActive")
        else:
            cmd += ["-TargetCount", str(target), "-Quiet"]
    else:
        cmd = [sys.executable, HUNT_PY]
        if verify:
            cmd.append("--verify")
        else:
            cmd += ["--target", str(target), "--quiet"]
    subprocess.run(cmd)


def check_deps():
    """requests is required by PROXY CHECKER.py (colorama is optional)."""
    try:
        import requests  # noqa: F401
        return True
    except ImportError:
        print(f"{Fore.RED}[!] Python package 'requests' is missing.")
        print(f"{Fore.WHITE}Install it with:")
        print(f"    {sys.executable} -m pip install requests")
        return False


def verify_mode():
    """Re-test every proxy in active.txt and remove the dead ones."""
    have = load_active(DATA_DIR)
    before = len(have)
    if before == 0:
        print(f"{Fore.RED}\n[!] active.txt is empty - nothing to verify.")
        return

    print(f"{Fore.MAGENTA}\nChecking your {before} active proxies...")
    print(f"{Fore.WHITE}Dead ones will be removed. This can take a few minutes.")
    print(f"{Fore.WHITE}" + "-" * 60)
    run_hunt(verify=True)

    have = load_active(DATA_DIR)
    removed = before - len(have)
    if removed <= 0:
        print(f"{Fore.GREEN}\n[VERIFY] All {len(have)} proxies still alive - nothing removed.")
    else:
        print(f"{Fore.GREEN}\n[VERIFY] {len(have)} alive, {removed} dead removed.")
    print(f"{Fore.GREEN}TOTAL ACTIVE PROXIES: {len(have)}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.chdir(DATA_DIR)  # data files (active.txt etc.) live in prox\data
    os.system('cls' if os.name == 'nt' else 'clear')
    print(logo)

    if not check_deps():
        wait_any_key()
        return

    raw = input(f"{Fore.BLUE}How many MORE active proxies do you want? (e.g. 20, or 'v' = clean dead): {Style.RESET_ALL}").strip()

    if raw.lower() in ("v", "verify", "clean"):
        verify_mode()
        wait_any_key()
        return

    try:
        target = int(raw)
    except ValueError:
        print(f"{Fore.RED}\n[!] '{raw}' is not a number!")
        input(f"\n{Fore.YELLOW}Press ENTER to exit...")
        return
    if target <= 0:
        print(f"{Fore.RED}\n[!] Enter a number bigger than 0!")
        input(f"\n{Fore.YELLOW}Press ENTER to exit...")
        return

    have = load_active(DATA_DIR)
    before = set(have)  # snapshot so we can show ONLY new finds later
    start = len(have)
    goal = start + target  # what you type = how many NEW actives to add
    print(f"{Fore.MAGENTA}\nYou already have: {start} active proxies")
    print(f"{Fore.CYAN}[*] Hunting and checking {target} MORE... goal: {goal} total")
    print(f"{Fore.WHITE}" + "-" * 60)

    run_hunt(target=goal)

    have = load_active(DATA_DIR)
    new_found = [p for p in have if p not in before]
    print(f"{Fore.WHITE}" + "-" * 60)
    gained = len(new_found)
    if gained >= target:
        print(f"{Fore.GREEN}[DONE] Added {gained} new actives! "
              f"You now have {len(have)} total (goal was {goal}).")
    else:
        print(f"{Fore.YELLOW}[!] Public sources ran dry: added {gained} of the {target} "
              f"you asked for ({len(have)} total). Run me again later for fresh batches.")

    # Show ONLY the ones found in THIS run (full list stays in active.txt)
    print(f"{Fore.CYAN}\nNEW actives found this run ({gained}):")
    for p in new_found:
        print(f"{Fore.GREEN}  [+] {p}")

    # This run's haul also saved separately
    with open(os.path.join(DATA_DIR, "new.txt"), "w") as f:
        f.write("\n".join(new_found) + ("\n" if new_found else ""))

    print(f"{Fore.CYAN}\n(This run's list also saved to new.txt - full list: active.txt)")
    print(f"{Fore.GREEN}\nTOTAL ACTIVE PROXIES: {len(have)}")
    wait_any_key()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Stopped by user.")
        wait_any_key()
    except Exception:
        import traceback
        print(f"\n{Fore.RED}[!] Something went wrong:")
        traceback.print_exc()
        wait_any_key()
