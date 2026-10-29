from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from phantom_ap.cli import build_parser, cmd_start
from phantom_ap.config import NetworkProfile, load_profile, save_profile
from phantom_ap.engines.pc_hotspot import HotspotRuntimeError
from phantom_ap.security.qr_enroll import build_wifi_qr_payload


def test_qr_payload_is_hidden_profile() -> None:
    payload = build_wifi_qr_payload("PhantomAP", "supersecret", hidden=True)
    assert payload.startswith("WIFI:S:")
    assert "H:true" in payload
    assert "T:WPA" in payload


def test_profile_round_trip(tmp_path) -> None:
    profile = NetworkProfile(ssid="GhostNet", iface="wlan0", whitelist=["AA:BB:CC:DD:EE:FF"])
    config_path = tmp_path / "profile.json"
    save_profile(profile, config_path)
    loaded = load_profile(config_path)
    assert loaded.ssid == "GhostNet"
    assert loaded.whitelist == ["AA:BB:CC:DD:EE:FF"]


def test_stealth_start_command_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["start", "--ap", "--qr", "--ssid", "GhostNet", "--passphrase", "pass123"])
    assert args.ap is True
    assert args.qr is True
    assert args.hidden is True


def test_start_qr_falls_back_cleanly_when_ap_not_supported(monkeypatch, capsys) -> None:
    class DummyController:
        def __init__(self, profile):
            self.profile = profile

        def start(self):
            raise HotspotRuntimeError("Linux AP not available")

    monkeypatch.setattr("phantom_ap.cli.HostapdHotspotController", DummyController)
    args = build_parser().parse_args(["start", "--ap", "--qr", "--ssid", "GhostNet", "--passphrase", "pass123"])
    rc = cmd_start(args)
    captured = capsys.readouterr()
    assert rc == 0
    assert "Generated QR code only" in captured.out
    assert "WIFI:S:GhostNet" in captured.out


needs_root = hasattr(os, "geteuid") and os.geteuid() == 0


@pytest.mark.skipif(not needs_root, reason="requires root privileges to load mac80211_hwsim")
def test_mac80211_hwsim_can_load() -> None:
    modprobe = shutil.which("modprobe")
    if modprobe is None:
        pytest.skip("modprobe is not available")
    result = subprocess.run([modprobe, "mac80211_hwsim", "radios=2"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    iw = shutil.which("iw")
    if iw is None:
        pytest.skip("iw is not available")
    output = subprocess.run([iw, "dev"], capture_output=True, text=True, check=False)
    assert output.returncode == 0
    assert "hwsim" in output.stdout.lower()
