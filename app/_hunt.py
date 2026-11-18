#!/usr/bin/env python3
"""
_hunt.py - cross-platform twin of _hunt.ps1 (Linux / macOS / Ubuntu).

Same job as the PowerShell version:
  * pull fresh proxies from public lists (plus sources.txt discoveries)
  * test them with PROXY CHECKER.py in right-sized rounds
  * top active.txt up to the target count
  * verify mode: re-test actives and remove the dead ones

Usage:
  python3 app/_hunt.py --target 100
  python3 app/_hunt.py --target 100 --quiet
  python3 app/_hunt.py --fetch-only
  python3 app/_hunt.py --find-sources
  python3 app/_hunt.py --verify
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
ACTIVE = os.path.join(DATA_DIR, "active.txt")
TESTED = os.path.join(DATA_DIR, "tested.txt")
SOURCES_FILE = os.path.join(DATA_DIR, "sources.txt")
CHECKER = os.path.join(APP_DIR, "PROXY CHECKER.py")

PROXY_RE = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}")

# Same source pool as _hunt.ps1 (biggest / most reliable first)
BUILTIN_SOURCES = [
    ("ErcinDedeoglu", "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt"),
    ("zevtyardt", "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt"),
    ("proxy4parsing", "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt"),
    ("openproxylist", "https://api.openproxylist.xyz/http.txt"),
    ("r00tee", "https://raw.githubusercontent.com/r00tee/Proxy-List/main/Https.txt"),
    ("aslisk", "https://raw.githubusercontent.com/aslisk/proxyhttps/main/https.txt"),
    ("Ercin-https", "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt"),
    ("proxifly", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    ("proxifly-cdn", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"),
    ("monosans", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("TheSpeedX", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("ProxyScrape-v2", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=no&anonymity=all"),
    ("ProxyScrape-v4", "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text"),
    ("hideip.me", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt"),
    ("hideip-https", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/https.txt"),
    ("roosterkid", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt"),
    ("sunny9577", "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt"),
    ("sunny-proxies", "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"),
    ("mmpx12", "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"),
    ("jetkai", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"),
    ("proxyspace", "https://proxyspace.pro/http.txt"),
    ("ALIILAPRO", "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt"),
    ("prxchk", "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt"),
    ("KangProxy", "https://raw.githubusercontent.com/officialputuid/KangProxy/main/http/http.txt"),
    ("MuRongPIG", "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt"),
    ("vakhov-fresh", "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt"),
    ("spys.me", "https://spys.me/proxy.txt"),
    ("clarketm", "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"),
    ("opsxcq", "https://raw.githubusercontent.com/opsxcq/proxy-list/master/list.txt"),
    ("themiralay", "https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/data.txt"),
    ("ShiftyTR", "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"),
]


def first_line(exc):
    text = str(exc).strip()
    return text.splitlines()[0] if text else exc.__class__.__name__


def http_get(url, timeout=40):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (proxy-finder)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


# ---------------------------------------------------------------- data files
def read_list(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip()]


def write_list(path, items):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(items) + ("\n" if items else ""))


def read_active():
    seen = set()
    out = []
    for p in read_list(ACTIVE):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def get_active_count():
    return len(read_active())


def load_tested():
    return set(read_list(TESTED))


def seed_tested(tested):
    """Oldest seed batch should never be retested either (matches ps1)."""
    seed = []
    for p in read_list(os.path.join(DATA_DIR, "proxies50.txt")):
        if p not in tested:
            tested.add(p)
            seed.append(p)
    if seed:
        with open(TESTED, "a", encoding="utf-8") as f:
            f.write("\n".join(seed) + "\n")
    return seed


# ---------------------------------------------------------------- sources
def load_all_sources():
    sources = list(BUILTIN_SOURCES)
    seen = {u for _, u in sources}
    for line in read_list(SOURCES_FILE):
        if "|" not in line:
            continue
        name, url = line.split("|", 1)
        name, url = name.strip(), url.strip()
        if url.startswith("http") and url not in seen:
            seen.add(url)
            sources.append((name, url))
    return sources


def fetch_sources(sources, tested, master, master_set,
                  need_fresh=0, min_sources=0, fetch_all=False):
    """Download lists, keep only never-tested proxies. Returns sources used."""
    used = 0
    for name, url in sources:
        if not fetch_all and used >= min_sources and len(master) >= need_fresh:
            break
        try:
            text = http_get(url)
        except Exception as exc:  # network / 404 / timeout
            print("source FAIL %-15s (%s)" % (name, first_line(exc)))
            continue
        added = 0
        for cand in PROXY_RE.findall(text):
            if cand not in tested and cand not in master_set:
                master_set.add(cand)
                master.append(cand)
                added += 1
        print("source OK   %-15s (+%d)" % (name, added))
        used += 1
    return used


def github_repos():
    repos = []
    for query in ("proxy-list+in:name", "free-proxy-list+in:name"):
        url = ("https://api.github.com/search/repositories"
               "?q=%s&sort=updated&order=desc&per_page=10" % query)
        try:
            data = json.loads(http_get(url, timeout=30))
            repos.extend(data.get("items", []))
        except Exception as exc:
            print("  GitHub search failed (%s)" % first_line(exc))
    return repos


def find_sources(max_new=6):
    print("Auto source finder: searching GitHub for fresh proxy-list repos...")
    known = {u for _, u in load_all_sources()}
    repos = github_repos()
    print("  probing %d recently-updated repos..." % len(repos))

    paths = [
        "http.txt",
        "proxies/http.txt",
        "proxies/protocols/http/data.txt",
        "http/http.txt",
        "all.txt",
    ]
    new = []
    for repo in repos:
        if len(new) >= max_new:
            break
        full = repo.get("full_name")
        if not full:
            continue
        branch = repo.get("default_branch") or "master"
        for path in paths:
            url = "https://raw.githubusercontent.com/%s/%s/%s" % (full, branch, path)
            if url in known:
                continue
            try:
                text = http_get(url, timeout=25)
            except Exception:
                continue
            count = len(PROXY_RE.findall(text))
            if count >= 20:
                known.add(url)
                name = repo.get("name") or full
                new.append((name, url))
                with open(SOURCES_FILE, "a", encoding="utf-8") as f:
                    f.write("%s|%s\n" % (name, url))
                print("  NEW SOURCE %-22s %6d proxies  %s" % (name, count, url))
                break  # one working list per repo is enough
    if not new:
        print("  No new working sources found this time.")
    else:
        print("  Added %d new source(s) to sources.txt" % len(new))
    return new


# ---------------------------------------------------------------- checker
def run_checker(file_name, verify=False):
    cmd = [sys.executable, CHECKER, file_name, "bar"]
    if verify:
        cmd.append("verify")
    subprocess.run(cmd, cwd=DATA_DIR)


# ---------------------------------------------------------------- modes
def verify_active():
    active = read_active()
    total = len(active)
    if total == 0:
        print("active.txt is empty - nothing to verify.")
        return

    print("Verifying %d active proxies (fails get a 2nd chance)..." % total)
    verify_file = os.path.join(DATA_DIR, "verify.txt")
    survivors_file = os.path.join(DATA_DIR, "survivors.txt")

    def clean_survivors():
        if os.path.exists(survivors_file):
            os.remove(survivors_file)

    # Pass 1 - check everything
    clean_survivors()
    write_list(verify_file, active)
    run_checker("verify.txt", verify=True)
    alive = read_list(survivors_file)

    # Pass 2 - retry only the failures
    alive_set = set(alive)
    failed = [p for p in active if p not in alive_set]
    print("Pass 1: %d alive, %d failed -> retrying the failures once..."
          % (len(alive), len(failed)))
    if failed:
        clean_survivors()
        write_list(verify_file, failed)
        run_checker("verify.txt", verify=True)
        alive.extend(read_list(survivors_file))

    keep = set(alive)
    cleaned = [p for p in active if p in keep]
    write_list(ACTIVE, cleaned)
    clean_survivors()
    if os.path.exists(verify_file):
        os.remove(verify_file)

    removed = total - len(cleaned)
    print("VERIFY DONE: %d alive, %d dead removed. active.txt now has %d."
          % (len(cleaned), removed, len(cleaned)))


def hunt(target, quiet):
    if not os.path.exists(TESTED):
        open(TESTED, "w").close()
    tested = load_tested()
    seed_tested(tested)

    sources = load_all_sources()
    need_fresh = max(200, (target - get_active_count()) * 12)
    if need_fresh <= 300:
        min_sources = 1
    elif need_fresh <= 1200:
        min_sources = 3
    elif need_fresh <= 3000:
        min_sources = 5
    else:
        min_sources = len(sources)
    print("Need ~%d fresh proxies -> using up to %d of %d sources"
          % (need_fresh, min_sources, len(sources)))

    master = []
    master_set = set()
    fetch_sources(sources, tested, master, master_set,
                  need_fresh, min_sources)

    if len(master) < need_fresh:
        print("Known sources gave %d fresh (needed ~%d) -> auto source finder starting..."
              % (len(master), need_fresh))
        new_sources = find_sources(6)
        if new_sources:
            fetch_sources(new_sources, tested, master, master_set, need_fresh, 0)

    print("Fresh untested proxies available: %d" % len(master))
    print("Active at start: %d  (target: %d)" % (get_active_count(), target))

    round_no = 0
    max_rounds = max(15, int(math.ceil(target / 20.0)))
    while True:
        active_now = get_active_count()
        if active_now >= target or not master or round_no >= max_rounds:
            break
        round_no += 1
        remaining = target - active_now
        chunk_size = min(300, max(40, remaining * 5))
        chunk = master[:chunk_size]
        del master[:len(chunk)]

        with open(TESTED, "a", encoding="utf-8") as f:
            f.write("\n".join(chunk) + "\n")
        for p in chunk:
            tested.add(p)

        write_list(os.path.join(DATA_DIR, "round.txt"), chunk)
        started = time.time()
        run_checker("round.txt")
        secs = int(time.time() - started)
        print("Round %d: checked %d in %ds -> active total %d (fresh left: %d)"
              % (round_no, len(chunk), secs, get_active_count(), len(master)))

    final = read_active()
    write_list(ACTIVE, final)
    print("FINAL: %d unique active proxies in active.txt (target was %d)"
          % (len(final), target))
    if not quiet:
        for p in final:
            print(p)


def fetch_only():
    sources = load_all_sources()
    tested = load_tested()
    master = []
    master_set = set()
    fetch_sources(sources, tested, master, master_set, fetch_all=True)
    print("Fresh untested proxies available: %d" % len(master))
    print("FETCH-ONLY mode: no proxies were checked. Active count unchanged: %d"
          % get_active_count())


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Proxy hunt engine (cross-platform)")
    parser.add_argument("--target", type=int, default=100)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--find-sources", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    os.chdir(DATA_DIR)

    if args.verify:
        verify_active()
        return
    if args.find_sources:
        new = find_sources(12)
        on_file = len([l for l in read_list(SOURCES_FILE) if "|" in l])
        print("Done: %d new source(s) added, %d auto-discovered source(s) on file."
              % (len(new), on_file))
        return
    if args.fetch_only:
        fetch_only()
        return

    hunt(args.target, args.quiet)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(1)
