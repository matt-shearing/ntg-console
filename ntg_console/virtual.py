"""Create a PipeWire virtual microphone that KDE actually lists as an input.

A sink monitor is hidden by Plasma. We create:
  ntg_send     — internal sink the engine plays into
  NTG_Console  — Audio/Source/Virtual, visible as a microphone
and link send monitors → virtual inputs.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field

SEND_NAME = "ntg_send"
SOURCE_NAME = "NTG_Console"


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _module_ids(*needles: str) -> list[str]:
    ids: list[str] = []
    for line in _run(["pactl", "list", "short", "modules"]).splitlines():
        if any(n in line for n in needles):
            ids.append(line.split()[0])
    return ids


@dataclass
class VirtualMic:
    sink_name: str
    source_name: str
    module_ids: list[str] = field(default_factory=list)


def _link() -> None:
    pairs = [
        (f"{SEND_NAME}:monitor_FL", f"{SOURCE_NAME}:input_FL"),
        (f"{SEND_NAME}:monitor_FR", f"{SOURCE_NAME}:input_FR"),
    ]
    for src, dst in pairs:
        # pw-link is idempotent enough; ignore "File exists".
        subprocess.run(
            ["pw-link", src, dst],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def ensure() -> VirtualMic:
    unload()
    send_id = _run(
        [
            "pactl",
            "load-module",
            "module-null-sink",
            f"sink_name={SEND_NAME}",
            "channel_map=front-left,front-right",
            "rate=48000",
        ]
    )
    src_id = _run(
        [
            "pactl",
            "load-module",
            "module-null-sink",
            "media.class=Audio/Source/Virtual",
            f"sink_name={SOURCE_NAME}",
            "channel_map=front-left,front-right",
        ]
    )
    # Give PipeWire a beat to publish ports before linking.
    for _ in range(10):
        ports = _run(["pw-link", "-io"])
        if f"{SOURCE_NAME}:input_FL" in ports and f"{SEND_NAME}:monitor_FL" in ports:
            break
        time.sleep(0.05)
    _link()
    _run(["pactl", "update-source-proplist", SOURCE_NAME, "device.description=NTG_Console"])
    _run(["pactl", "update-source-proplist", SOURCE_NAME, "device.icon_name=audio-input-microphone"])
    return VirtualMic(
        sink_name=SEND_NAME,
        source_name=SOURCE_NAME,
        module_ids=[i for i in (send_id, src_id) if i],
    )


def relink() -> None:
    _link()


def unload() -> None:
    for mid in _module_ids(
        "sink_name=ntg_console",
        "sink_name=ntg_send",
        "sink_name=NTG_Console",
        "sink_name=ntg_console_mic",
    ):
        _run(["pactl", "unload-module", mid])


def set_default_source(name: str) -> None:
    _run(["pactl", "set-default-source", name])
