from __future__ import annotations

import subprocess
from typing import Iterable


class TrafficAnonymizer:
    """Routes hotspot traffic through Tor or a WireGuard interface."""

    def __init__(self, hotspot_iface: str):
        self.hotspot_iface = hotspot_iface

    def route_via_tor(self, tor_dns_port: int = 9053, trans_port: int = 9040) -> None:
        # Safe command-generation helper; actual Debian/Ubuntu Tor setups vary by distro.
        commands = [
            ["ip", "route", "add", "default", "via", "127.0.0.1", "dev", self.hotspot_iface],
            ["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", str(tor_dns_port)],
            ["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "--syn", "-j", "REDIRECT", "--to-ports", str(trans_port)],
        ]
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

    def route_via_vpn(self, vpn_interface: str) -> None:
        try:
            subprocess.run(["ip", "route", "replace", "default", "dev", vpn_interface], check=True,
                           capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass


__all__ = ["TrafficAnonymizer"]
