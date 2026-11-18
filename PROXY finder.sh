#!/usr/bin/env bash
# ============================================================
#  PROXY FINDER - Ubuntu / Debian / Linux / macOS launcher
#
#  First time only:
#      chmod +x "PROXY finder.sh"
#  Then run:
#      ./"PROXY finder.sh"
# ============================================================
set -u

cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[!] Python 3 is required."
    echo "    Ubuntu/Debian:  sudo apt install python3 python3-pip"
    echo "    Then:           python3 -m pip install requests"
    read -rp "Press ENTER to close..." _
    exit 1
fi

"$PY" "app/PROXY finder.py"
status=$?

# Double-click friendly: keep the window open if something went wrong
if [ "$status" -ne 0 ]; then
    read -rp "Press ENTER to close..." _
fi
