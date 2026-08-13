"""Audio thread: NTG → processors → virtual mic (+ optional headset monitor)."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from .dsp import DSPSettings, VoiceChain

SAMPLE_RATE = 48000
BLOCK = 256
CHANNELS = 2


@dataclass
class Meters:
    in_peak: float = 1e-12
    in_rms: float = 1e-12
    out_peak: float = 1e-12
    out_rms: float = 1e-12
    gate_open: bool = False
    gr_db: float = 0.0
    clip: bool = False
    running: bool = False
    error: str = ""


class Engine:
    def __init__(self) -> None:
        self.settings = DSPSettings()
        self.settings_lock = threading.Lock()
        self.meters = Meters()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._record_lock = threading.Lock()
        self._record_buf: list[np.ndarray] = []
        self.recording = False
        self.monitor_headset = False
        self.monitor_gain = 0.22
        self.source_name = (
            "alsa_input.usb-R__DE_Microphones_R__DE_VideoMic_NTG_158E2530-00.analog-stereo"
        )
        self.sink_name = "ntg_console"

    def start(self, source_name: str, sink_name: str) -> None:
        self.stop()
        self.source_name = source_name
        self.sink_name = sink_name
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ntg-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        self.meters.running = False

    def update(self, **kwargs) -> None:
        with self.settings_lock:
            for k, v in kwargs.items():
                if hasattr(self.settings, k):
                    setattr(self.settings, k, v)

    def start_record(self) -> None:
        with self._record_lock:
            self._record_buf.clear()
            self.recording = True

    def stop_record(self) -> np.ndarray:
        with self._record_lock:
            self.recording = False
            if not self._record_buf:
                return np.zeros((0, 2), dtype=np.float32)
            return np.concatenate(self._record_buf, axis=0)

    def _run(self) -> None:
        chain = VoiceChain(SAMPLE_RATE)
        self.meters.error = ""
        # PortAudio Pulse reads PULSE_SOURCE / PULSE_SINK at stream open.
        old_src = os.environ.get("PULSE_SOURCE")
        old_sink = os.environ.get("PULSE_SINK")
        os.environ["PULSE_SOURCE"] = self.source_name
        os.environ["PULSE_SINK"] = self.sink_name
        try:
            inn = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                blocksize=BLOCK,
                dtype="float32",
                device="pulse",
            )
            out = sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                blocksize=BLOCK,
                dtype="float32",
                device="pulse",
            )
            inn.start()
            out.start()
            self.meters.running = True
            hold_in = 1e-12
            hold_out = 1e-12
            while not self._stop.is_set():
                block, overflowed = inn.read(BLOCK)
                with self.settings_lock:
                    settings = DSPSettings(**self.settings.__dict__)
                y = chain.process(block, settings)
                out.write(y)
                peak_in = float(np.max(np.abs(block))) + 1e-12
                peak_out = float(np.max(np.abs(y))) + 1e-12
                rms_in = float(np.sqrt(np.mean(block.astype(np.float64) ** 2))) + 1e-12
                rms_out = float(np.sqrt(np.mean(y.astype(np.float64) ** 2))) + 1e-12
                hold_in = max(peak_in, hold_in * 0.92)
                hold_out = max(peak_out, hold_out * 0.92)
                m = self.meters
                m.in_peak = hold_in
                m.in_rms = rms_in
                m.out_peak = hold_out
                m.out_rms = rms_out
                m.gate_open = chain.gate_open
                m.gr_db = chain.gr_db
                m.clip = peak_in >= 0.99 or peak_out >= 0.99
                if overflowed:
                    m.error = "xrun"
                if self.recording:
                    with self._record_lock:
                        if self.recording:
                            self._record_buf.append(y.copy())
            inn.stop()
            out.stop()
            inn.close()
            out.close()
        except Exception as exc:  # noqa: BLE001
            self.meters.error = str(exc)
            self.meters.running = False
        finally:
            if old_src is None:
                os.environ.pop("PULSE_SOURCE", None)
            else:
                os.environ["PULSE_SOURCE"] = old_src
            if old_sink is None:
                os.environ.pop("PULSE_SINK", None)
            else:
                os.environ["PULSE_SINK"] = old_sink
            self.meters.running = False
            time.sleep(0.01)
