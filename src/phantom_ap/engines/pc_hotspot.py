from __future__ import annotations

import os
import platform
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Iterable

from phantom_ap.config import NetworkProfile


class HotspotRuntimeError(RuntimeError):
    pass


class HostapdHotspotController:
    """Create and manage a stealth hostapd hotspot with hidden SSID and ACL whitelisting."""

    def __init__(self, profile: NetworkProfile):
        self.profile = profile
        self.hostapd_conf = Path("/tmp/phantomap_hostapd.conf")
        self.dnsmasq_conf = Path("/tmp/phantomap_dnsmasq.conf")
        self.acl_path = Path("/tmp/phantom_accept.acl")
        self.processes: dict[str, subprocess.Popen[str]] = {}
        self._restore_mac: str | None = None

    def _write_acl(self) -> None:
        whitelist = [m.lower() for m in self.profile.whitelist]
        self.acl_path.write_text("\n".join(whitelist) + ("\n" if whitelist else ""), encoding="utf-8")

    def _hostapd_config_text(self) -> str:
        self._write_acl()
        bssid_line = f"bssid={self.profile.bssid}\n" if self.profile.bssid else ""
        return (
            "interface={iface}\n"
            "driver=nl80211\n"
            "ssid={ssid}\n"
            "hw_mode=g\n"
            "channel={channel}\n"
            "ieee80211n=1\n"
            "ignore_broadcast_ssid={hidden}\n"
            "macaddr_acl={acl}\n"
            "accept_mac_file=/tmp/phantom_accept.acl\n"
            "auth_algs=1\n"
            "wpa=2\n"
            "wpa_passphrase={passphrase}\n"
            "wpa_key_mgmt=WPA-PSK\n"
            "wpa_pairwise=CCMP\n"
            "rsn_pairwise=CCMP\n"
            "country_code={country}\n"
            "ctrl_interface=/var/run/hostapd\n"
            "ctrl_interface_group=0\n"
            "{bssid}"
        ).format(
            iface=self.profile.iface,
            ssid=self.profile.ssid,
            channel=self.profile.channel,
            hidden=self.profile.ignore_broadcast_ssid,
            acl=self.profile.macaddr_acl,
            passphrase=self.profile.passphrase,
            country=self.profile.country,
            bssid=bssid_line,
        )

    def _dnsmasq_config_text(self) -> str:
        return (
            "interface={iface}\n"
            "dhcp-range=192.168.44.2,192.168.44.100,255.255.255.0,12h\n"
            "dhcp-option=3,192.168.44.1\n"
            "dhcp-option=6,192.168.44.1\n"
            "listen-address=127.0.0.1\n"
            "bind-interfaces\n"
            "domain=phantom.local\n"
            "except-interface=lo\n"
        ).format(iface=self.profile.iface)

    def _run_command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(args), capture_output=True, text=True, check=False)

    def _ensure_iface_up(self) -> None:
        self._run_command("ip", "link", "set", self.profile.iface, "up")
        self._run_command("ip", "addr", "flush", "dev", self.profile.iface)
        self._run_command("ip", "addr", "add", "192.168.44.1/24", "dev", self.profile.iface)

    def _save_current_mac(self) -> None:
        result = self._run_command("cat", "/sys/class/net/{iface}/address".format(iface=self.profile.iface))
        if result.returncode == 0:
            self._restore_mac = result.stdout.strip()

    def _apply_randomized_bssid(self) -> None:
        if not self.profile.bssid:
            return
        self._run_command("ip", "link", "set", "dev", self.profile.iface, "down")
        self._run_command("ip", "link", "set", "dev", self.profile.iface, "address", self.profile.bssid)
        self._run_command("ip", "link", "set", "dev", self.profile.iface, "up")

    def start(self) -> None:
        if os.name != "posix" or platform.system() != "Linux":
            raise HotspotRuntimeError("PhantomAP AP mode requires Linux with hostapd, dnsmasq, iproute2, and iw. This host is not Linux-capable.")

        missing = [
            tool for tool in ("hostapd", "dnsmasq", "ip", "iw")
            if shutil.which(tool) is None
        ]
        if missing:
            raise HotspotRuntimeError(
                "Missing required wireless tools: " + ", ".join(missing) + ". Install hostapd dnsmasq iproute2 iw to use AP mode."
            )

        self._save_current_mac()
        self._ensure_iface_up()
        self.hostapd_conf.write_text(self._hostapd_config_text(), encoding="utf-8")
        self.dnsmasq_conf.write_text(self._dnsmasq_config_text(), encoding="utf-8")
        self._apply_randomized_bssid()

        self._run_command("sysctl", "-w", "net.ipv4.ip_forward=1")
        self._run_command("iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE")
        self._run_command("iptables", "-A", "FORWARD", "-i", self.profile.iface, "-o", "eth0", "-j", "ACCEPT")
        self._run_command("iptables", "-A", "FORWARD", "-i", "eth0", "-o", self.profile.iface, "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT")

        self.processes["hostapd"] = subprocess.Popen(["hostapd", self.hostapd_conf.as_posix()], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes["dnsmasq"] = subprocess.Popen(["dnsmasq", "-C", self.dnsmasq_conf.as_posix()], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        wait_for = 10
        while wait_for > 0:
            if self.processes["hostapd"].poll() is None:
                break
            time.sleep(0.2)
            wait_for -= 1
        if self.processes["hostapd"].poll() is not None:
            raise HotspotRuntimeError("hostapd failed to start")

    def ghost_lock(self, whitelist: Iterable[str]) -> None:
        self.profile.whitelist = list(whitelist)
        self.profile.macaddr_acl = 1
        self.profile.ghost_locked = True
        self.hostapd_conf.write_text(self._hostapd_config_text(), encoding="utf-8")
        self._run_command("kill", "-HUP", str(self.processes["hostapd"].pid))

    def stop(self) -> None:
        for name, process in list(self.processes.items()):
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except Exception:
                pass
            self.processes.pop(name, None)

        self._run_command("iptables", "-t", "nat", "-D", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE", check=False)
        self._run_command("iptables", "-D", "FORWARD", "-i", self.profile.iface, "-o", "eth0", "-j", "ACCEPT", check=False)
        self._run_command("iptables", "-D", "FORWARD", "-i", "eth0", "-o", self.profile.iface, "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT", check=False)

        if self._restore_mac:
            self._run_command("ip", "link", "set", "dev", self.profile.iface, "down")
            self._run_command("ip", "link", "set", "dev", self.profile.iface, "address", self._restore_mac)
            self._run_command("ip", "link", "set", "dev", self.profile.iface, "up")

        self._run_command("service", "NetworkManager", "start", check=False)
        self._run_command("systemctl", "restart", "NetworkManager", check=False)


__all__ = ["HostapdHotspotController", "HotspotRuntimeError"]
