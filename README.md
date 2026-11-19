# Proxy Finder

[![Ubuntu smoke tests](https://github.com/ItzJoker2YT-city/proxy-finder/actions/workflows/test.yml/badge.svg)](https://github.com/ItzJoker2YT-city/proxy-finder/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#quick-start)

Find fresh working **HTTP proxies** from public lists, test them for real, and keep a clean list in `active.txt`.

Type a number, wait a few seconds, get that many verified proxies. Dead ones are removed on demand and never come back.

```
  _____ _____ _____ _____         _____ _____
 |  __ \|  ___/  __ \  _  |       |  _  /  ___|
 | |  \/| |_  | /  \/ | | |_   _  | | | \ `--.
 | | __ |  _|| |   | | | |\ \ / / | | | |`--. \
 | |_\ \| |  | \/\ /\ \_/ / V V / \ \_/ /\__/ /
  \____/\_|   \____/ \___/ \_/\_/   \___/\____/
        FINDER  ->  hunt + check for you
```

## What it does

- **Hunts** fresh proxies from ~30 public sources, plus any sources you add to `data/sources.txt`.
- **Tests** every candidate against real endpoints with a 5 second timeout, 50 threads at a time, and a live progress bar.
- **Remembers** every proxy it has ever checked in `data/tested.txt`, so nothing is wasted and dead proxies are never retested.
- **Scales itself** to the request: asking for 5 finishes in seconds, asking for 1,000 keeps pulling and checking until it gets there.
- **Finds new sources** by itself when the known lists run dry (GitHub search + common file paths).

## Quick start

### Windows

Double-click **`PROXY finder.bat`**.

If Python is missing: install it from [python.org](https://www.python.org/downloads/) and tick *Add python.exe to PATH*, then run the batch file again. It installs nothing by itself; the only required package is `requests`.

```bat
python -m pip install requests
```

### Linux / Ubuntu / macOS

```bash
git clone https://github.com/ItzJoker2YT-city/proxy-finder.git
cd proxy-finder

chmod +x "PROXY finder.sh"
./"PROXY finder.sh"
```

That is the whole install. The launcher finds `requests` itself: when the distro blocks system pip (Ubuntu 23.04+ does, PEP 668) it builds a local `.venv` once and reuses it afterwards. To install it manually instead:

```bash
sudo apt install python3-requests     # Ubuntu / Debian
python3 -m pip install requests       # macOS
```

No `git`? Download the ZIP, extract it, and run the last two lines in that folder.

## Using it

```
How many MORE active proxies do you want? (e.g. 20, or 'v' = clean dead):
```

| You type | What happens |
|---|---|
| `20` | adds **20 more** on top of what you already have |
| `500` | keeps hunting in rounds until 500 new ones are found |
| `v` | re-tests your list and deletes the dead proxies |

The number is **additional**, not a total. With 100 in `active.txt`, typing `20` aims for 120.

At the end you see only the proxies found **in that run**, plus the new total:

```
[DONE] Added 21 new actives! You now have 874 total (goal was 873).

NEW actives found this run (21):
  [+] 103.150.61.42:8080
  ...
TOTAL ACTIVE PROXIES: 874
```

## Verify: get rid of dead proxies

Free proxies die fast. Before you actually need them, type `v` at the prompt:

- Every proxy in `active.txt` is tested.
- Failures get a **second pass** with three different test endpoints, so a slow moment does not delete a good proxy.
- Survivors are written back to `active.txt`; the dead ones stay in `tested.txt` forever.

```
Checking your 863 active proxies...
[VERIFY] 412 alive, 451 dead removed.
TOTAL ACTIVE PROXIES: 412
```

## Files

| Path | What it is |
|---|---|
| `PROXY finder.bat` | Windows entry point (double-click) |
| `PROXY finder.sh` | Linux / macOS entry point |
| `app/PROXY finder.py` | The menu: asks how many, computes the goal, picks the engine, prints the report |
| `app/PROXY CHECKER.py` | The tester: threads, progress bar, endpoint rotation |
| `app/_hunt.py` | Hunt engine for Linux / macOS |
| `app/_hunt.ps1` | Hunt engine for Windows |
| `data/active.txt` | **Your live proxies** (one `ip:port` per line) |
| `data/new.txt` | Only the proxies found by the last run |
| `data/tested.txt` | Every proxy ever checked, used to skip repeats |
| `data/sources.txt` | Extra sources you or the auto-finder discovered |

Everything in `data/` except `sources.txt` is git-ignored, so your personal list never ends up in the repo.

## How it works

```
        ┌─────────────────┐
        │ PROXY finder.py │  asks: how many more?
        └────────┬────────┘
                 │ goal = current active + what you asked
        ┌────────▼────────┐
        │  hunt engine    │  _hunt.py (Linux/macOS)  or  _hunt.ps1 (Windows)
        └────────┬────────┘
                 │ 1. download public lists, drop known/dead ones
                 │ 2. check a batch with PROXY CHECKER.py
                 │ 3. still short? bigger batch, more sources, repeat
        ┌────────▼────────┐
        │  active.txt     │  deduped at the end of every run
        └─────────────────┘
```

- Candidates already present in `tested.txt` are skipped, so you never pay for the same check twice.
- Round size grows with the request: small asks check ~40 at a time, big asks up to 300.
- If a round comes back nearly empty, the auto source finder looks for new list URLs and keeps going.

## How proxies are tested

A proxy is marked **active** only when a real request through it returns a page that contains an IP address. The test rotates between six endpoints so no single site rate-limits the whole run:

```
http://checkip.amazonaws.com   http://icanhazip.com     http://api.ipify.org
http://httpbin.org/ip          http://httpbingo.org/ip  http://ifconfig.me/ip
```

- 5 second timeout per attempt
- 50 concurrent checks
- hunting: 1 endpoint per proxy (fast); verify: up to 3 endpoints per proxy (accurate)

## Command line

The engines also work on their own:

```bash
python3 app/_hunt.py --target 100      # hunt until active.txt has 100
python3 app/_hunt.py --verify          # clean dead proxies
python3 app/_hunt.py --fetch-only      # only download lists, check nothing
python3 app/_hunt.py --find-sources    # search for new list URLs
```

On Windows the same options exist on `app/_hunt.ps1`: `-TargetCount`, `-VerifyActive`, `-FetchOnly`, `-FindSources`.

### Adding your own source

Append one line per source to `data/sources.txt`:

```
my-list|https://example.com/http.txt
```

Any page containing `ip:port` lines works. Sources found automatically are appended in the same format.

## Testing in the cloud (free Ubuntu box)

The repo ships two GitHub Actions workflows:

- **Ubuntu smoke tests** (`test.yml`) — runs on every push: syntax, launcher, a real hunt, and a verify pass with a fake proxy that must be removed.
- **remote shell** (`remote-shell.yml`) — manual: starts an [sshx](https://sshx.io) web terminal on an Ubuntu runner and posts the link in an issue. Handy for trying the Linux build without installing Linux.

Actions → *remote shell* → **Run workflow**, then open the issue it creates and run:

```bash
cd "$GITHUB_WORKSPACE"
./"PROXY finder.sh"
```

## FAQ

**Why do proxies stop working after a while?**
They are free, public, and shared by thousands of people. Many last minutes. Run `v` right before you need them.

**Why does it say sources ran dry?**
Public lists refresh at different times of day. Run it again later, or add a source to `data/sources.txt`.

**Does it need admin rights or install anything global?**
No. It reads public URLs and writes text files next to itself. `pip install requests` is the only dependency.

**Is it fast on a small ask?**
Yes. Asking for 5 typically checks ~40 candidates and finishes in under 30 seconds.

## Disclaimer

The proxies come from third-party public lists. Their reliability, speed, and safety are unknown, and traffic through them is only as private as the proxy operator makes it. Use them for low-risk, rate-limited work, and never send credentials or personal data through a random free proxy.

## License

MIT — see [LICENSE](LICENSE).
