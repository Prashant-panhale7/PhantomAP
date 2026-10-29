from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from phantom_ap.config import NetworkProfile


class PhantomAPDashboard:
    def __init__(self, profile: NetworkProfile):
        self.profile = profile

    def render(self):
        status_table = Table.grid(expand=True)
        status_table.add_column(justify="left")
        status_table.add_column(justify="right")
        status_table.add_row("Mode", "GHOST LOCKED" if self.profile.ghost_locked else "ENROLLMENT")
        status_table.add_row("BSSID", self.profile.bssid or "00:11:22:33:44:55")
        status_table.add_row("Channel", str(self.profile.channel))
        status_table.add_row("TX Power", f"{self.profile.tx_power_dbm} dBm")
        status_table.add_row("Beacon", "Silent" if self.profile.hidden else "Visible")

        devices = Table(title="Trusted Devices")
        devices.add_column("MAC")
        devices.add_column("IP")
        devices.add_column("RSSI")
        devices.add_column("Status")
        for mac in self.profile.whitelist or ["00:00:00:00:00:00"]:
            devices.add_row(mac, "192.168.44.2", "-55 dBm", "TRUSTED")

        qrcode = Text(
            "████████████████\n"
            "██  ░░░░ ░░  ██\n"
            "██ ░██████ ░ ██\n"
            "██ ░▓▓▓▓▓▓ ░ ██\n"
            "██ ░▓▓▓▓▓▓ ░ ██\n"
            "██ ░▓▓▓▓▓▓ ░ ██\n"
            "██ ░██████ ░ ██\n"
            "██  ░░░░ ░░  ██\n"
            "████████████████",
            style="bold cyan",
        )

        log_panel = Panel(
            "[green]Probe Request[/green] blocked from 5A:7D:13:...\n"
            "[yellow]Auth[/yellow] rejected from 84:AC:8C:...\n"
            "[blue]TX power[/blue] adjusted to 4 dBm after RSSI poll",
            title="802.11 Event Log",
        )

        return Group(
            Panel(status_table, title="AP Status"),
            Align.center(qrcode),
            devices,
            log_panel,
        )

    def run(self) -> None:
        console = Console()
        with Live(self.render(), console=console, screen=True, refresh_per_second=2) as live:
            while True:
                live.update(self.render())


__all__ = ["PhantomAPDashboard"]
