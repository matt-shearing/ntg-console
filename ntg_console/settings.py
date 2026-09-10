"""Persisted mixer settings. Shared by the daemon and the GUI."""

from __future__ import annotations

import json
from pathlib import Path

from .dsp import DSPSettings

CONFIG = Path.home() / ".config" / "ntg-console" / "settings.json"

SETTINGS_VERSION = 2

DEFAULTS: dict = {
    "hpf_hz": 75,
    "pad": False,
    "hf_boost": False,
    "suppress": True,
    "gate": True,
    "gate_threshold_db": -42,
    "comp": False,
    "comp_amount": 0.55,
    "bottom": False,
    "bottom_amount": 0.35,
    "excite": False,
    "excite_amount": 0.3,
    "fader_db": 0,
    "mute": False,
    "lock_usb": True,
    "claim_default": True,
    "steer_apps": True,
    "settings_version": SETTINGS_VERSION,
}


def _looks_like_stock_calls(data: dict) -> bool:
    try:
        amount = float(data.get("comp_amount", 0))
    except (TypeError, ValueError):
        amount = 0.0
    return (
        data.get("comp") is True
        and abs(amount - 0.55) < 0.02
        and data.get("gate") is True
        and data.get("suppress") is True
        and int(data.get("hpf_hz", 0) or 0) == 75
        and not data.get("bottom")
        and not data.get("excite")
        and not data.get("pad")
    )


def migrate(data: dict) -> dict:
    """v2: Calls no longer runs a compressor (it flattens the shotgun)."""
    version = int(data.get("settings_version") or 1)
    if version >= SETTINGS_VERSION:
        return data
    if _looks_like_stock_calls(data):
        data["comp"] = False
    data.setdefault("claim_default", True)
    data.setdefault("steer_apps", True)
    data["settings_version"] = SETTINGS_VERSION
    return data


def apply_disk(raw: dict) -> dict:
    """Merge a settings file onto defaults. A missing version is v1, not v2."""
    data = dict(DEFAULTS)
    data.update(raw)
    data["settings_version"] = int(raw.get("settings_version") or 1)
    return migrate(data)


def load() -> dict:
    raw: dict = {}
    if CONFIG.exists():
        try:
            raw = json.loads(CONFIG.read_text())
        except json.JSONDecodeError:
            pass
    data = apply_disk(raw)
    if int(raw.get("settings_version") or 1) < SETTINGS_VERSION:
        save(data)
    return data


def save(data: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULTS)
    merged.update(data)
    CONFIG.write_text(json.dumps(merged, indent=2) + "\n")


def to_dsp(data: dict) -> DSPSettings:
    fields = DSPSettings.__dataclass_fields__
    kwargs = {}
    for name in fields:
        if name in data:
            kwargs[name] = data[name]
    return DSPSettings(**kwargs)
