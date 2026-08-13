"""Detect the VideoMic NTG and talk to its class-compliant USB mixer."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

NTG_VENDOR = 0x19F7
NTG_PRODUCT = 0x001A
NTG_SOURCE = (
    "alsa_input.usb-R__DE_Microphones_R__DE_VideoMic_NTG_158E2530-00.analog-stereo"
)
NTG_SINK = (
    "alsa_output.usb-R__DE_Microphones_R__DE_VideoMic_NTG_158E2530-00.analog-stereo"
)
CARD = "NTG"


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


@dataclass
class DeviceInfo:
    connected: bool
    serial: str
    firmware: str
    source_name: str
    sink_name: str
    is_default_source: bool
    default_source: str
    default_sink: str
    usb_gain_db: float
    jack_db: float
    direct_monitor: bool
    mute: bool


def _parse_capture_db(amixer: str) -> float:
    for line in amixer.splitlines():
        if "Capture" in line and "dB]" in line:
            try:
                return float(line.rsplit("[", 1)[-1].split("dB")[0])
            except ValueError:
                continue
    return 0.0


def _parse_playback_db(amixer: str) -> float:
    for line in amixer.splitlines():
        if "Playback" in line and "dB]" in line and "%" in line:
            try:
                return float(line.rsplit("[", 1)[-1].split("dB")[0])
            except ValueError:
                continue
    return -12.0


def poll() -> DeviceInfo:
    default_source = _run(["pactl", "get-default-source"])
    default_sink = _run(["pactl", "get-default-sink"])
    sources = _run(["pactl", "list", "short", "sources"])
    connected = "VideoMic_NTG" in sources or "R__DE_VideoMic_NTG" in sources
    source = ""
    for line in sources.splitlines():
        if "VideoMic_NTG" in line or "R__DE_VideoMic_NTG" in line:
            parts = line.split()
            if len(parts) >= 2 and "monitor" not in parts[1]:
                source = parts[1]
                break
    if not source:
        source = NTG_SOURCE

    lsusb = _run(["lsusb", "-d", f"{NTG_VENDOR:04x}:{NTG_PRODUCT:04x}", "-v"])
    serial = "158E2530"
    firmware = "1.20"
    m = re.search(r"iSerial\s+\d+\s+(\S+)", lsusb)
    if m:
        serial = m.group(1)
    m = re.search(r"bcdDevice\s+(\S+)", lsusb)
    if m:
        firmware = m.group(1)

    mic = _run(["amixer", "-c", CARD, "sget", "Mic"])
    pcm = _run(["amixer", "-c", CARD, "sget", "PCM"])
    usb_gain = _parse_capture_db(mic) if mic else 0.0
    jack = _parse_playback_db(pcm) if pcm else -23.0
    # Mic Playback Switch is the direct-monitor path into the NTG jack.
    direct = "Playback [on]" in mic

    mute = "Mute: yes" in _run(["pactl", "get-source-mute", source])
    return DeviceInfo(
        connected=connected,
        serial=serial,
        firmware=firmware,
        source_name=source,
        sink_name=NTG_SINK,
        is_default_source="VideoMic_NTG" in default_source,
        default_source=default_source,
        default_sink=default_sink,
        usb_gain_db=usb_gain,
        jack_db=jack,
        direct_monitor=direct,
        mute=mute,
    )


def set_usb_gain_db(db: float) -> None:
    db = max(0.0, min(24.0, float(db)))
    _run(["amixer", "-c", CARD, "-q", "sset", "Mic", f"{db:.0f}dB"])


def set_jack_db(db: float) -> None:
    db = max(-60.0, min(0.0, float(db)))
    _run(["amixer", "-c", CARD, "-q", "sset", "PCM", f"{db:.0f}dB"])


def set_direct_monitor(on: bool) -> None:
    _run(["amixer", "-c", CARD, "-q", "sset", "Mic", "Playback", "on" if on else "off"])


def set_source_mute(source: str, on: bool) -> None:
    _run(["pactl", "set-source-mute", source, "1" if on else "0"])
