from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


class FirewallController:
    """Control nftables/iptables rules for the hotpot isolation and NAT."""

    def __init__(self, iface: str, subnet: str = "192.168.44.0/24", upstream_iface: str | None = None):
        self.iface = iface
        self.subnet = subnet
        self.upstream_iface = upstream_iface
        self.chain_name = "PHANTOMAP"

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(args), check=check, capture_output=True, text=True)

    def ensure_nat(self) -> None:
        # nftables-first path with a safe fallback to iptables if the kernel does not support nft.
        nft_rules = [
            "nft add table ip phantomap", 
            "nft add chain ip phantomap prerouting { type nat hook prerouting priority -100; policy accept; }",
            "nft add chain ip phantomap postrouting { type nat hook postrouting priority 100; policy accept; }",
            "nft add rule ip phantomap postrouting oifname \"{upstream}\" masquerade".format(upstream=self.upstream_iface or "eth0"),
        ]
        for cmd in nft_rules:
            try:
                self._run("nft", *cmd.split())
            except subprocess.CalledProcessError:
                pass

        try:
            self._run("iptables", "-t", "nat", "-A", "POSTROUTING", "-o", self.upstream_iface or "eth0",
                      "-j", "MASQUERADE", check=False)
        except FileNotFoundError:
            pass

    def apply_acl(self, whitelist: Iterable[str]) -> None:
        allowed = [m.lower() for m in whitelist]
        acl_path = Path("/tmp/phantom_accept.acl")
        acl_path.write_text("\n".join(allowed) + ("\n" if allowed else ""), encoding="utf-8")

    def flush(self) -> None:
        for command in (
            ["nft", "delete", "table", "ip", "phantomap"],
            ["iptables", "-t", "nat", "-F", "POSTROUTING"],
            ["iptables", "-F", "INPUT"],
            ["iptables", "-F", "FORWARD"],
        ):
            try:
                self._run(*command, check=False)
            except FileNotFoundError:
                pass

    def __enter__(self) -> "FirewallController":
        self.ensure_nat()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.flush()


__all__ = ["FirewallController"]
