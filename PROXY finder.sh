#!/usr/bin/env bash
# ============================================================
#  PROXY FINDER - Ubuntu / Debian / Linux / macOS launcher
#
#  Just run it:
#      chmod +x "PROXY finder.sh"     (first time only)
#      ./"PROXY finder.sh"
#
#  It uses your system Python when 'requests' is already
#  installed. If not (or if pip is blocked by PEP 668), it
#  builds a local .venv once and uses that instead.
# ============================================================
set -u

cd "$(dirname "$0")" || exit 1

VENV_PY=".venv/bin/python"

has_requests() {
    "$1" -c "import requests" >/dev/null 2>&1
}

find_python() {
    if [ -x "$VENV_PY" ] && has_requests "$VENV_PY"; then
        PY="$VENV_PY"
        return 0
    fi
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && has_requests "$candidate"; then
            PY="$candidate"
            return 0
        fi
    done
    return 1
}

if ! find_python; then
    BASE=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            BASE="$candidate"
            break
        fi
    done

    if [ -z "$BASE" ]; then
        echo "[!] Python 3 is required."
        echo "    Ubuntu/Debian:  sudo apt install python3 python3-requests"
        echo "    macOS:          python3 -m pip install requests"
        read -rp "Press ENTER to close..." _
        exit 1
    fi

    echo "[*] Python package 'requests' is missing."
    echo "[*] Setting up a local .venv (one time, about 10 seconds)..."
    if "$BASE" -m venv .venv >/dev/null 2>&1 && [ -x "$VENV_PY" ]; then
        if [ -f requirements.txt ]; then
            "$VENV_PY" -m pip install --quiet --disable-pip-version-check -r requirements.txt >/dev/null 2>&1
        else
            "$VENV_PY" -m pip install --quiet --disable-pip-version-check requests >/dev/null 2>&1
        fi
        if has_requests "$VENV_PY"; then
            PY="$VENV_PY"
            echo "[*] Ready - running on the local .venv"
        fi
    fi

    if [ -z "${PY:-}" ]; then
        echo
        echo "[!] Automatic setup failed. Pick one of these:"
        echo "    1) simplest:   sudo apt install python3-requests"
        echo "    2) venv:       sudo apt install python3-venv"
        echo "                   python3 -m venv .venv"
        echo "                   .venv/bin/pip install -r requirements.txt"
        echo "    Then run:      ./\"PROXY finder.sh\""
        read -rp "Press ENTER to close..." _
        exit 1
    fi
fi

"$PY" "app/PROXY finder.py"
status=$?

# Double-click friendly: keep the window open if something went wrong
if [ "$status" -ne 0 ]; then
    read -rp "Press ENTER to close..." _
fi
