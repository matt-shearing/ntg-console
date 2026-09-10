"""Print why the NTG sounds wrong in Gather / Zoom / Meet."""

from __future__ import annotations

from . import device, virtual
from .ipc import Client
from .settings import load


def _line(ok: bool, text: str) -> str:
    return f"{'OK' if ok else '!!'}  {text}"


def report() -> str:
    lines: list[str] = ["NTG Console doctor", ""]
    info = device.poll()
    data = load()
    client = Client()
    st: dict = {}
    meters: dict = {}
    if client.alive():
        try:
            st = client.request({"cmd": "status"}, timeout=1.0)
            meters = client.request({"cmd": "meters"}, timeout=1.0)
        except OSError as exc:
            lines.append(_line(False, f"Engine socket failed: {exc}"))
    else:
        lines.append(_line(False, "Background engine is not running."))

    lines.append(
        _line(info.connected, f"Microphone {'connected' if info.connected else 'not found'}")
    )
    if info.connected:
        fw_ok = device.firmware_is_current(info.firmware)
        lines.append(
            _line(
                fw_ok,
                f"Firmware {info.firmware} "
                f"(RØDE latest {device.LATEST_FIRMWARE}"
                f"{'' if fw_ok else ' — flash with RØDE Central on Windows or Mac'})",
            )
        )
        lines.append(
            _line(
                abs(info.usb_gain_db) < 0.5,
                f"USB digital gain {info.usb_gain_db:+.0f} dB "
                f"(lock {'on' if data.get('lock_usb', True) else 'off'})",
            )
        )

    default = st.get("default_source") or info.default_source
    virt = virtual.SOURCE_NAME
    lines.append(
        _line(
            True,
            f"Default source: {default or '(none)'} "
            f"(NTG_Console is a choice, not forced)",
        )
    )

    raw = st.get("raw_source") or info.source_name
    raw_apps = st.get("raw_apps")
    if raw_apps is None:
        outputs = device.list_source_outputs()
        raw_apps = device.apps_on_source(raw, outputs)
        virt_apps = device.apps_on_source(virt, outputs)
    else:
        virt_apps = st.get("virt_apps") or []
    lines.append(
        _line(
            True,
            "Call apps on the raw NTG: " + (", ".join(raw_apps) if raw_apps else "none"),
        )
    )
    lines.append(
        _line(
            True,
            "Call apps on NTG_Console: " + (", ".join(virt_apps) if virt_apps else "none"),
        )
    )
    lines.append(
        _line(
            True,
            f"Claim default: {bool(data.get('claim_default', False))} "
            "(off — desktop picker is yours)",
        )
    )
    lines.append(
        _line(
            True,
            f"Steer call apps: {bool(data.get('steer_apps', False))}",
        )
    )

    running = bool(st.get("running") if st else False)
    lines.append(_line(running, f"Engine running: {running}"))
    if meters.get("ok"):
        lines.append(
            f"    in {meters.get('in_peak_db', 0):.1f} dB peak  "
            f"out {meters.get('out_peak_db', 0):.1f} dB peak  "
            f"gate {'open' if meters.get('gate_open') else 'closed'}"
        )
        left = meters.get("left_rms_db")
        right = meters.get("right_rms_db")
        if left is not None and right is not None:
            lines.append(f"    L {left:.1f} dB rms   R {right:.1f} dB rms")
        if meters.get("safety_on") or st.get("safety_on"):
            lines.append(
                _line(
                    False,
                    f"Safety channel looks on "
                    f"({st.get('safety_db', meters.get('safety_db', 0)):.0f} dB L/R). "
                    "Cycle the dB button until both LEDs are off.",
                )
            )
        err = meters.get("error") or ""
        if err:
            lines.append(_line(False, f"Engine: {err}"))

    lines.append(
        _line(
            not data.get("comp"),
            f"Compressor {'on' if data.get('comp') else 'off'} "
            "(off for calls — makeup gain flattens the shotgun and fights browser AGC)",
        )
    )
    lines.append(f"    gate {data.get('gate')}  RNNoise {data.get('suppress')}  "
                 f"HPF {data.get('hpf_hz')} Hz")

    if info.is_default_source and virt not in (default or ""):
        lines.append(
            _line(
                False,
                "Gather will hear the raw stereo NTG. Chromium then writes the USB "
                "volume slider, which is why level and directionality wander.",
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    print(report(), end="")
    return 0
