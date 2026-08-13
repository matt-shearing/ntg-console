"""Headless engine: keeps NTG_Console alive without the GUI.

Never touches the system default source or sink. Routing stays whatever
the user last chose (headset while walking, NTG_Console when they pick it).
"""

from __future__ import annotations

import signal
import threading
import time
from pathlib import Path

from . import device, virtual
from .analyze import DATA_DIR, analyze, save_report, save_wav
from .dsp import lin_to_db
from .engine import Engine
from .ipc import serve
from .settings import load, save, to_dsp

# Do not import or call virtual.set_default_source from this module.


class Daemon:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.engine = Engine()
        self.data = load()
        self.lock = threading.Lock()
        self.virt = None

    def start_graph(self) -> None:
        info = device.poll()
        self.virt = virtual.ensure()
        if self.data.get("lock_usb", True) and info.connected:
            device.set_usb_gain_db(0)
        self.engine.update(**to_dsp(self.data).__dict__)
        if info.connected:
            self.engine.start(info.source_name, self.virt.sink_name)

    def _watch(self) -> None:
        while not self.stop.is_set():
            virtual.relink()
            info = device.poll()
            if info.connected and not self.engine.meters.running:
                try:
                    if self.virt is None:
                        self.virt = virtual.ensure()
                    if self.data.get("lock_usb", True):
                        device.set_usb_gain_db(0)
                    self.engine.start(info.source_name, self.virt.sink_name)
                except Exception:
                    pass
            self.stop.wait(1.5)

    def handle(self, req: dict) -> dict:
        cmd = req.get("cmd")
        if cmd == "ping":
            return {"ok": True}
        if cmd == "get":
            with self.lock:
                return {"ok": True, "settings": dict(self.data)}
        if cmd == "set":
            patch = req.get("settings") or {}
            with self.lock:
                self.data.update(patch)
                save(self.data)
                self.engine.update(**to_dsp(self.data).__dict__)
                if self.data.get("lock_usb", True):
                    device.set_usb_gain_db(0)
            return {"ok": True}
        if cmd == "meters":
            m = self.engine.meters
            return {
                "ok": True,
                "running": m.running,
                "in_peak": m.in_peak,
                "in_rms": m.in_rms,
                "out_peak": m.out_peak,
                "out_rms": m.out_rms,
                "gate_open": m.gate_open,
                "gr_db": m.gr_db,
                "clip": m.clip,
                "error": m.error,
                "in_peak_db": lin_to_db(m.in_peak),
                "out_peak_db": lin_to_db(m.out_peak),
                "in_rms_db": lin_to_db(m.in_rms),
                "out_rms_db": lin_to_db(m.out_rms),
            }
        if cmd == "status":
            info = device.poll()
            return {
                "ok": True,
                "running": self.engine.meters.running,
                "connected": info.connected,
                "serial": info.serial,
                "firmware": info.firmware,
                "usb_gain_db": info.usb_gain_db,
                "source_name": virtual.SOURCE_NAME,
                "error": self.engine.meters.error,
            }
        if cmd == "record_start":
            self.engine.start_record()
            return {"ok": True}
        if cmd == "record_stop":
            samples = self.engine.stop_record()
            wav = DATA_DIR / "take.wav"
            save_wav(wav, samples, 48000)
            result = analyze(samples, 48000, wav)
            save_report(result)
            return {
                "ok": True,
                "wav": str(wav),
                "verdict": result.verdict,
                "notes": result.notes,
                "speech_peak_db": result.speech_peak_db,
                "floor_rms_db": result.floor_rms_db,
                "snr_db": result.snr_db,
            }
        if cmd == "shutdown":
            self.stop.set()
            return {"ok": True}
        return {"ok": False, "error": f"unknown cmd {cmd!r}"}

    def run(self) -> int:
        self.start_graph()
        watcher = threading.Thread(target=self._watch, name="ntg-watch", daemon=True)
        watcher.start()

        def handle_sig(_signum, _frame) -> None:
            self.stop.set()

        signal.signal(signal.SIGTERM, handle_sig)
        signal.signal(signal.SIGINT, handle_sig)
        serve(self.handle, self.stop)
        self.engine.stop()
        virtual.unload()
        return 0


def main() -> int:
    return Daemon().run()


if __name__ == "__main__":
    raise SystemExit(main())
