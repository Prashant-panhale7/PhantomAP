from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any, Dict, Iterable

try:
    import paramiko
except ImportError:  # pragma: no cover - optional dependency for router adapters
    paramiko = None


@dataclass
class RouterSpec:
    host: str
    username: str
    password: str
    port: int = 22
    adapter: str = "openwrt"


class RouterAdapter:
    """Base class for router-specific management adapters."""

    def __init__(self, spec: RouterSpec):
        self.spec = spec

    def cloak(self, iface: str, whitelist: Iterable[str]) -> None:
        raise NotImplementedError("Every router adapter must implement cloak().")


class OpenWrtRouterAdapter(RouterAdapter):
    """Uses SSH and UCI to hide the SSID and whitelist MAC addresses."""

    def cloak(self, iface: str, whitelist: Iterable[str]) -> None:
        if paramiko is None:
            raise RuntimeError("paramiko is required for router bridge functionality.")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.spec.host, port=self.spec.port, username=self.spec.username, password=self.spec.password,
                      timeout=15)
        try:
            maclist = ",".join(str(mac).strip() for mac in whitelist)
            commands = [
                "uci set wireless.@wifi-iface[0].hidden='1'",
                "uci set wireless.@wifi-iface[0].macfilter='allow'",
                f"uci set wireless.@wifi-iface[0].maclist='{maclist}'",
                "uci commit wireless",
                "wifi reload",
            ]
            stdin, stdout, stderr = client.exec_command("; ".join(commands))
            stdout.channel.recv_exit_status()
            if stderr.read().decode().strip():
                raise RuntimeError(stderr.read().decode().strip())
        finally:
            client.close()


class GenericRouterHttpAdapter(RouterAdapter):
    """Stub for generic web API or TR-064 based routers."""

    def cloak(self, iface: str, whitelist: Iterable[str]) -> None:
        raise NotImplementedError("Generic HTTP/TR-064 adapters require vendor implementation.")


class RouterBridge:
    """Coordinate a router bridge and apply the configured stealth whitelist."""

    def __init__(self, adapter: RouterAdapter):
        self.adapter = adapter

    def cloak(self, iface: str, whitelist: Iterable[str]) -> None:
        self.adapter.cloak(iface, whitelist)


__all__ = ["GenericRouterHttpAdapter", "OpenWrtRouterAdapter", "RouterAdapter", "RouterBridge", "RouterSpec"]
