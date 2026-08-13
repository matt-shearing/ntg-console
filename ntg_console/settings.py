"""Persisted mixer settings. Shared by the daemon and the GUI."""

from __future__ import annotations

import json
from pathlib import Path

from .dsp import DSPSettings

CONFIG = Path.home() / ".config" / "ntg-console" / "settings.json"

DEFAULTS: dict = {
    "hpf_hz": 75,
    "pad": False,
    "hf_boost": False,
    "suppress": True,
    "gate": True,
    "gate_threshold_db": -42,
    "comp": True,
    "comp_amount": 0.55,
    "bottom": False,
    "bottom_amount": 0.35,
    "excite": False,
    "excite_amount": 0.3,
    "fader_db": 0,
    "mute": False,
    "lock_usb": True,
}


def load() -> dict:
    data = dict(DEFAULTS)
    if CONFIG.exists():
        try:
            data.update(json.loads(CONFIG.read_text()))
        except json.JSONDecodeError:
            pass
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
