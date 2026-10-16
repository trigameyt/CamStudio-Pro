"""Normalize the Android 'Copy address and key' payload without logging secrets.

Android clipboard format:
    <phone IPv4>:8765
    <32-character hexadecimal pairing key>

Single-line manual key entry also works. Other formats fail closed.
"""
from __future__ import annotations

import ipaddress
import re

_KEY = re.compile(r"^[A-F0-9]{32}$")


def parse_pairing_text(text: str) -> tuple[str, str | None]:
    """Return (key, optional_host), or raise ValueError without exposing the input."""
    if not isinstance(text, str):
        raise ValueError("Saisis la clé affichée sur Android.")
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]
    if not lines:
        raise ValueError("Saisis la clé affichée sur Android.")
    if len(lines) > 2:
        raise ValueError("Colle uniquement l'adresse et la clé copiées depuis Android.")
    candidate = lines[-1].replace(" ", "").replace("-", "").upper()
    if not _KEY.fullmatch(candidate):
        raise ValueError("Clé incorrecte : 32 caractères hexadécimaux attendus.")
    if len(lines) == 1:
        return candidate, None
    raw_host = lines[0]
    if raw_host.lower().startswith("http://"):
        raw_host = raw_host[7:]
    if "/" in raw_host or "?" in raw_host or "@" in raw_host:
        raise ValueError("Adresse Android invalide.")
    ip_part, sep, port = raw_host.partition(":")
    try:
        ipaddress.IPv4Address(ip_part)
    except ValueError:
        raise ValueError("Adresse IP Android invalide.") from None
    if sep and (not port.isdigit() or not 1 <= int(port) <= 65535):
        raise ValueError("Port Android invalide.")
    return candidate, ip_part + (":" + port if sep else "")
