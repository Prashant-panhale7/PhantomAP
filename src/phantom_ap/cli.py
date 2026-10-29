from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phantom_ap.config import NetworkProfile, load_profile, save_profile
from phantom_ap.engines.pc_hotspot import HostapdHotspotController
from phantom_ap.security.qr_enroll import build_wifi_qr_payload, generate_ascii_qr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PhantomAP stealth Wi‑Fi management CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start PhantomAP")
    start_parser.add_argument("--iface", default="wlan0")
    start_parser.add_argument("--ssid", default="PhantomAP")
    start_parser.add_argument("--passphrase", default="phantompass")
    start_parser.add_argument("--channel", type=int, default=6)
    start_parser.add_argument("--hidden", action="store_true", default=True, help="Hide the SSID during enrollment (default: enabled for stealth mode)")
    start_parser.add_argument("--ap", action="store_true", help="Start the Wi‑Fi access point in stealth hidden mode")
    start_parser.add_argument("--qr", action="store_true", help="Generate the QR enrollment code while starting the hidden AP")
    start_parser.add_argument("--enrollment-time", type=int, default=30)
    start_parser.add_argument("--whitelist", nargs="*", default=[])

    lock_parser = subparsers.add_parser("lock", help="Activate Ghost Lock mode")
    lock_parser.add_argument("--iface", default="wlan0")
    lock_parser.add_argument("--whitelist", nargs="*", default=[])

    stop_parser = subparsers.add_parser("stop", help="Stop PhantomAP and restore state")
    stop_parser.add_argument("--iface", default="wlan0")

    qr_parser = subparsers.add_parser("qr", help="Generate enrollment QR")
    qr_parser.add_argument("--ssid", default="PhantomAP")
    qr_parser.add_argument("--passphrase", default="phantompass")
    qr_parser.add_argument("--output", default="/tmp/phantom_qr.png")

    return parser


def _load_profile_from_args(args) -> NetworkProfile:
    profile = load_profile()
    profile.iface = getattr(args, "iface", profile.iface)
    profile.ssid = getattr(args, "ssid", profile.ssid)
    profile.passphrase = getattr(args, "passphrase", profile.passphrase)
    profile.channel = getattr(args, "channel", profile.channel)
    profile.hidden = getattr(args, "hidden", profile.hidden)
    if getattr(args, "ap", False) or getattr(args, "qr", False):
        profile.hidden = True
        profile.ignore_broadcast_ssid = 2
        profile.macaddr_acl = 0
        profile.ghost_locked = False
    profile.enrollment_time = getattr(args, "enrollment_time", profile.enrollment_time)
    profile.whitelist = list(getattr(args, "whitelist", profile.whitelist) or [])
    return profile


def cmd_start(args) -> int:
    profile = _load_profile_from_args(args)
    save_profile(profile)
    payload = build_wifi_qr_payload(profile.ssid, profile.passphrase, hidden=True)

    controller = HostapdHotspotController(profile)
    try:
        controller.start()
    except Exception as exc:
        if getattr(args, "qr", False) or getattr(args, "ap", False):
            print(f"[phantom-ap] AP startup is unavailable on this host: {exc}")
            print("[phantom-ap] Generated QR code only. A real Linux AP requires hostapd, dnsmasq, iproute2, and iw.")
            print(payload)
            print(generate_ascii_qr(payload))
            return 0
        raise

    print(f"[phantom-ap] Started hidden hotspot on {profile.iface} ({profile.ssid})")
    print(f"[phantom-ap] Enrollment mode: SSID hidden, ACL open, Probe Requests allowed during onboarding")
    if getattr(args, "qr", False) or getattr(args, "ap", False):
        print(payload)
        print(generate_ascii_qr(payload))
    return 0


def cmd_lock(args) -> int:
    profile = load_profile()
    profile.iface = args.iface
    profile.whitelist = list(args.whitelist)
    profile.macaddr_acl = 1
    profile.ghost_locked = True
    save_profile(profile)
    controller = HostapdHotspotController(profile)
    controller.ghost_lock(profile.whitelist)
    print(f"[phantom-ap] Ghost Lock engaged for {profile.iface}")
    return 0


def cmd_stop(args) -> int:
    profile = load_profile()
    profile.iface = args.iface
    controller = HostapdHotspotController(profile)
    controller.stop()
    print(f"[phantom-ap] Stopped and restored {profile.iface}")
    return 0


def cmd_qr(args) -> int:
    payload = build_wifi_qr_payload(args.ssid, args.passphrase, hidden=True)
    print(payload)
    print(generate_ascii_qr(payload))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "start": cmd_start,
        "lock": cmd_lock,
        "stop": cmd_stop,
        "qr": cmd_qr,
    }
    try:
        return commands[args.command](args)
    except Exception as exc:  # pragma: no cover - CLI error handling
        print(f"[phantom-ap] Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
