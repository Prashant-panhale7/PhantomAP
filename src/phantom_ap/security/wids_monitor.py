from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ClientFingerprint:
    mac: str
    dhcp_hostname: str | None = None
    ttl: int | None = None
    os_hint: str | None = None
    arp_ip: str | None = None
    seen_at: float = 0.0


class WIDSMonitor:
    """Passive monitor for duplicate MAC detection, fingerprint binding and alerts."""

    def __init__(self, iface: str, deadman_timeout: int = 60):
        self.iface = iface
        self.deadman_timeout = deadman_timeout
        self.fingerprints: dict[str, ClientFingerprint] = {}
        self.last_seen: dict[str, float] = defaultdict(float)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def register_fingerprint(self, mac: str, *, dhcp_hostname: str | None = None, ttl: int | None = None,
                            os_hint: str | None = None, arp_ip: str | None = None) -> None:
        self.fingerprints[mac.lower()] = ClientFingerprint(
            mac=mac.lower(),
            dhcp_hostname=dhcp_hostname,
            ttl=ttl,
            os_hint=os_hint,
            arp_ip=arp_ip,
            seen_at=time.time(),
        )

    def detect_duplicate_mac(self, mac: str) -> bool:
        current = self.last_seen.get(mac.lower(), 0.0)
        if current and time.time() - current < 5.0:
            return True
        self.last_seen[mac.lower()] = time.time()
        return False

    def run(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._watch, name="WIDSMonitor", daemon=True)
        self._thread.start()

    def _watch(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(1.0)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)


__all__ = ["ClientFingerprint", "WIDSMonitor"]
