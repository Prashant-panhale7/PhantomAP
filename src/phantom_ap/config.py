from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class NetworkProfile:
    ssid: str = "PhantomAP"
    passphrase: str = "phantompass"
    iface: str = "wlan0"
    channel: int = 6
    country: str = "US"
    hidden: bool = True
    ignore_broadcast_ssid: int = 2
    macaddr_acl: int = 0
    enrollment_time: int = 30
    tx_power_dbm: float = 15.0
    ghost_locked: bool = False
    whitelist: list[str] = field(default_factory=list)
    bssid: str | None = None
    secondary_monitor_iface: str | None = None
    tor_route: bool = False
    vpn_interface: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "ssid": self.ssid,
            "passphrase": self.passphrase,
            "iface": self.iface,
            "channel": self.channel,
            "country": self.country,
            "hidden": self.hidden,
            "ignore_broadcast_ssid": self.ignore_broadcast_ssid,
            "macaddr_acl": self.macaddr_acl,
            "enrollment_time": self.enrollment_time,
            "tx_power_dbm": self.tx_power_dbm,
            "ghost_locked": self.ghost_locked,
            "whitelist": list(self.whitelist),
            "bssid": self.bssid,
            "secondary_monitor_iface": self.secondary_monitor_iface,
            "tor_route": self.tor_route,
            "vpn_interface": self.vpn_interface,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NetworkProfile":
        return cls(
            ssid=str(payload.get("ssid", "PhantomAP")),
            passphrase=str(payload.get("passphrase", "phantompass")),
            iface=str(payload.get("iface", "wlan0")),
            channel=int(payload.get("channel", 6)),
            country=str(payload.get("country", "US")),
            hidden=bool(payload.get("hidden", True)),
            ignore_broadcast_ssid=int(payload.get("ignore_broadcast_ssid", 2)),
            macaddr_acl=int(payload.get("macaddr_acl", 0)),
            enrollment_time=int(payload.get("enrollment_time", 30)),
            tx_power_dbm=float(payload.get("tx_power_dbm", 15.0)),
            ghost_locked=bool(payload.get("ghost_locked", False)),
            whitelist=[str(item) for item in payload.get("whitelist", [])],
            bssid=payload.get("bssid"),
            secondary_monitor_iface=payload.get("secondary_monitor_iface"),
            tor_route=bool(payload.get("tor_route", False)),
            vpn_interface=payload.get("vpn_interface"),
        )


def _default_profile_path() -> Path:
    return Path("/etc/phantom-ap/profile.json")


def save_profile(profile: NetworkProfile, path: str | Path | None = None) -> Path:
    profile_path = Path(path) if path else _default_profile_path()
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with profile_path.open("w", encoding="utf-8") as handle:
        json.dump(profile.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return profile_path


def load_profile(path: str | Path | None = None) -> NetworkProfile:
    profile_path = Path(path) if path else _default_profile_path()
    if not profile_path.exists():
        return NetworkProfile()
    with profile_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return NetworkProfile.from_dict(payload)
