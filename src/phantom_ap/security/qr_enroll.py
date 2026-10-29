from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import qrcode
from PIL import Image


def build_wifi_qr_payload(ssid: str, passphrase: str, hidden: bool = True) -> str:
    """Build the Hidden Wi‑Fi QR payload used by Android/iOS/Windows.

    The hidden flag uses the QR `H:true` attribute so the OS saves a hidden profile.
    """
    safe_ssid = ssid.replace(";", "\\;")
    safe_pass = passphrase.replace(";", "\\;")
    hidden_flag = "true" if hidden else "false"
    return f"WIFI:S:{safe_ssid};T:WPA;P:{safe_pass};H:{hidden_flag};;"


def generate_qr_png(payload: str, output_path: str | Path, size: int = 7) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                      box_size=size, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output)
    return output


def generate_ascii_qr(payload: str, border: int = 1) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                      box_size=2, border=border)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    pixels = img.convert("1")
    width, height = pixels.size
    rows: list[str] = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append("██" if pixels.getpixel((x, y)) == 0 else "  ")
        rows.append("".join(row))
    return "\n".join(rows)


def generate_hidden_qr(ssid: str, passphrase: str, output_path: str | Path, ascii_only: bool = False) -> tuple[str, str]:
    payload = build_wifi_qr_payload(ssid, passphrase, hidden=True)
    if ascii_only:
        return payload, generate_ascii_qr(payload)
    output = generate_qr_png(payload, output_path)
    return payload, str(output)


__all__ = [
    "build_wifi_qr_payload",
    "generate_ascii_qr",
    "generate_hidden_qr",
    "generate_qr_png",
]
