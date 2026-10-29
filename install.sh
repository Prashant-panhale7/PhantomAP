#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "[phantom-ap] Please run as root: sudo ./install.sh" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv iproute2 dnsmasq hostapd iptables nftables iw wireless-tools qrencode \
  net-tools curl git ca-certificates || true

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r "$(dirname "$0")/requirements.txt"
python3 -m pip install -e "$(dirname "$0")"

mkdir -p /etc/phantom-ap
chmod 700 /etc/phantom-ap

cat >/usr/local/bin/phantom-ap <<'EOF'
#!/usr/bin/env bash
exec python3 -m phantom_ap.cli "$@"
EOF
chmod 755 /usr/local/bin/phantom-ap

printf "\n[phantom-ap] PhantomAP installed. Use: phantom-ap --help\n"
