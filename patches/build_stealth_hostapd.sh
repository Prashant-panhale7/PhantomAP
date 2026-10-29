#!/usr/bin/env bash
set -euo pipefail

HOSTAPD_DIR="${1:-/tmp/hostapd-stealth}"
PATCH_FILE="$(dirname "$0")/zero_beacon_hostapd.patch"

if [[ ! -d "$HOSTAPD_DIR/.git" ]]; then
  git clone --depth 1 https://w1.fi/hostap.git "$HOSTAPD_DIR"
fi

cd "$HOSTAPD_DIR"
git checkout -- .
patch -p1 < "$PATCH_FILE" || true
make -j"$(nproc)" hostapd
cp -f hostapd /usr/local/sbin/hostapd_stealth
printf "[phantom-ap] Patched hostapd binary installed at /usr/local/sbin/hostapd_stealth\n"
