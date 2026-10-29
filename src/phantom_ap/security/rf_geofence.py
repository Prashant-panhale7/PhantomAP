from __future__ import annotations

import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class StationSample:
    mac: str
    rssi: int
    bitrate: str | None = None


class RFGeofence:
    """Polls connected clients and adapts transmit power to keep the signal inside the room."""

    def __init__(self, iface: str, poll_interval: float = 2.0, tx_power_min_dbm: float = 4.0,
                 tx_power_max_dbm: float = 20.0, trusted_macs: Iterable[str] | None = None):
        self.iface = iface
        self.poll_interval = poll_interval
        self.tx_power_min_dbm = tx_power_min_dbm
        self.tx_power_max_dbm = tx_power_max_dbm
        self.trusted_macs = set(trusted_macs or [])
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def set_trusted_macs(self, macs: Iterable[str]) -> None:
        self.trusted_macs = set(macs)

    def read_station_rssi(self) -> list[StationSample]:
        try:
            result = subprocess.run(["iw", "dev", self.iface, "station", "dump"], capture_output=True,
                                    text=True, check=False)
        except FileNotFoundError:
            return []
        if result.returncode != 0:
            return []

        samples: list[StationSample] = []
        current_mac: str | None = None
        current_rssi: int | None = None
        bitrate: str | None = None
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("Station"):
                if current_mac is not None and current_rssi is not None:
                    samples.append(StationSample(current_mac, current_rssi, bitrate))
                mac = stripped.split()[-1]
                current_mac = mac
                current_rssi = None
                bitrate = None
                continue
            if "signal:" in line.lower():
                match = re.search(r"signal:\s+([-+]?\d+)\s+dBm", line, flags=re.I)
                if match:
                    current_rssi = int(match.group(1))
            if "tx bitrate:" in line.lower():
                bitrate = line.split("tx bitrate:", 1)[1].strip()
        if current_mac is not None and current_rssi is not None:
            samples.append(StationSample(current_mac, current_rssi, bitrate))
        return samples

    def _compute_power_for_clients(self, samples: list[StationSample]) -> float:
        if not samples:
            return self.tx_power_max_dbm
        trusted = [s for s in samples if s.mac.lower() in {m.lower() for m in self.trusted_macs}]
        if not trusted:
            return self.tx_power_max_dbm
        strongest = max(s.rssi for s in trusted)
        # Keep transmit power just enough to reach the closest trusted device while limiting leakage.
        target_dbm = min(self.tx_power_max_dbm, max(self.tx_power_min_dbm, float(1.5 + abs(strongest) * 0.4)))
        return round(target_dbm, 2)

    def apply_tx_power(self, power_dbm: float) -> float:
        power_mbm = int(round(power_dbm * 100))
        try:
            subprocess.run(["iw", "dev", self.iface, "set", "txpower", "fixed", f"{power_mbm}"], check=True,
                           capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return float("nan")
        return power_dbm

    def tick(self) -> float:
        samples = self.read_station_rssi()
        new_power = self._compute_power_for_clients(samples)
        return self.apply_tx_power(new_power)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="RFGeofence", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)


__all__ = ["RFGeofence", "StationSample"]
