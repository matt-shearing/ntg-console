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

# RØDE Central marketing version. USB bcdDevice 1.20 is firmware 1.2.0.
LATEST_FIRMWARE = "2.1.3"

# Browsers and call apps that should hear NTG_Console, not the raw shotgun.
CALL_APP_NEEDLES = (
    "chromium",
    "chrome",
    "brave",
    "firefox",
    "zoom",
    "discord",
    "slack",
    "teams",
    "gather",
    "workadventure",
    "element",
    "signal",
)


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


def firmware_tuple(fw: str) -> tuple[int, int, int]:
    """Parse a USB bcdDevice ('1.20') or marketing version ('2.1.3')."""
    parts: list[int] = []
    for piece in fw.lower().lstrip("v").split("."):
        try:
            parts.append(int(piece, 10))
        except ValueError:
            parts.append(0)
    if len(parts) == 2 and parts[1] >= 10:
        minor = parts[1]
        parts = [parts[0], minor // 10, minor % 10]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def firmware_is_current(fw: str) -> bool:
    return firmware_tuple(fw) >= firmware_tuple(LATEST_FIRMWARE)


def parse_source_outputs(text: str) -> list[dict]:
    items: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        if line.startswith("Source Output #"):
            if cur:
                items.append(cur)
            cur = {
                "id": line.split("#", 1)[1].strip(),
                "source_index": "",
                "source": "",
                "app": "",
                "binary": "",
                "corked": False,
            }
        elif cur is None:
            continue
        elif line.strip().startswith("Source:"):
            cur["source_index"] = line.split(":", 1)[1].strip().split()[0]
        elif "application.name" in line and "=" in line:
            cur["app"] = line.split("=", 1)[-1].strip().strip('"')
        elif "application.process.binary" in line and "=" in line:
            cur["binary"] = line.split("=", 1)[-1].strip().strip('"')
        elif "pulse.corked" in line:
            cur["corked"] = "true" in line.lower()
    if cur:
        items.append(cur)
    return items


def parse_short_sources(text: str) -> dict[str, str]:
    names: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            names[parts[0]] = parts[1]
    return names


def is_call_app(item: dict) -> bool:
    blob = f"{item.get('app', '')} {item.get('binary', '')}".lower()
    if "python" in blob:
        return False
    return any(needle in blob for needle in CALL_APP_NEEDLES)


def list_source_outputs() -> list[dict]:
    items = parse_source_outputs(_run(["pactl", "list", "source-outputs"]))
    names = parse_short_sources(_run(["pactl", "list", "short", "sources"]))
    for item in items:
        item["source"] = names.get(item["source_index"], "")
    return items


def apps_on_source(source_name: str, outputs: list[dict] | None = None) -> list[str]:
    if not source_name:
        return []
    rows = outputs if outputs is not None else list_source_outputs()
    names: list[str] = []
    for item in rows:
        if item.get("source") != source_name:
            continue
        if "python" in f"{item.get('app', '')} {item.get('binary', '')}".lower():
            continue
        names.append(item.get("app") or item.get("binary") or item["id"])
    return names


def steer_call_apps(raw_source: str, virtual_source: str) -> list[str]:
    """Move Chromium / Zoom / etc. off the raw NTG onto NTG_Console."""
    if not raw_source or raw_source == virtual_source:
        return []
    moved: list[str] = []
    for item in list_source_outputs():
        if not is_call_app(item):
            continue
        if item.get("source") != raw_source:
            continue
        _run(["pactl", "move-source-output", item["id"], virtual_source])
        moved.append(item.get("app") or item.get("binary") or item["id"])
    return moved
