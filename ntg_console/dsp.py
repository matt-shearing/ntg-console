"""Voice processors modelled on RØDE Connect: HPF, gate, compressor, Big Bottom, Exciter."""

from __future__ import annotations

import ctypes
import math
from dataclasses import dataclass

import numpy as np


@dataclass
class DSPSettings:
    hpf_hz: int = 75  # 0, 75, 150
    pad: bool = False
    hf_boost: bool = False
    gate: bool = True
    gate_threshold_db: float = -42.0
    comp: bool = True
    comp_amount: float = 0.55  # 0..1
    bottom: bool = False
    bottom_amount: float = 0.4
    excite: bool = False
    excite_amount: float = 0.35
    suppress: bool = True
    fader_db: float = 0.0
    mute: bool = False


class RNNoise:
    """Streaming RNNoise wrapper. Frame size is 480 samples @ 48 kHz (~10 ms extra delay)."""

    def __init__(self) -> None:
        self.lib = None
        self.st = None
        self.frame = 480
        self._in = np.zeros(0, dtype=np.float32)
        self._out = np.zeros(0, dtype=np.float32)
        try:
            lib = ctypes.CDLL("librnnoise.so.0")
            lib.rnnoise_create.argtypes = [ctypes.c_void_p]
            lib.rnnoise_create.restype = ctypes.c_void_p
            lib.rnnoise_destroy.argtypes = [ctypes.c_void_p]
            lib.rnnoise_process_frame.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
            ]
            lib.rnnoise_process_frame.restype = ctypes.c_float
            lib.rnnoise_get_frame_size.restype = ctypes.c_int
            self.frame = int(lib.rnnoise_get_frame_size()) or 480
            self.st = lib.rnnoise_create(None)
            self.lib = lib
        except OSError:
            self.lib = None

    @property
    def available(self) -> bool:
        return self.st is not None

    def process(self, mono: np.ndarray) -> np.ndarray:
        if self.st is None:
            return mono
        x = np.concatenate([self._in, np.asarray(mono, dtype=np.float32).ravel()])
        produced: list[np.ndarray] = []
        i = 0
        n = self.frame
        while i + n <= len(x):
            frame = np.array(x[i : i + n] * 32768.0, dtype=np.float32, copy=True)
            ptr = frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            self.lib.rnnoise_process_frame(self.st, ptr, ptr)
            produced.append(frame / 32768.0)
            i += n
        self._in = x[i:]
        if produced:
            self._out = np.concatenate([self._out, *produced])
        take = min(len(mono), len(self._out))
        y = np.empty(len(mono), dtype=np.float32)
        if take:
            y[:take] = self._out[:take]
            self._out = self._out[take:]
        if take < len(mono):
            # First frames: pass dry until the 480-sample pipeline fills.
            y[take:] = np.asarray(mono[take:], dtype=np.float32)
        return y

    def close(self) -> None:
        if self.lib is not None and self.st is not None:
            self.lib.rnnoise_destroy(self.st)
            self.st = None


def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def lin_to_db(x: float) -> float:
    return 20.0 * math.log10(max(float(x), 1e-12))


class Biquad:
    def __init__(self) -> None:
        self.b0 = 1.0
        self.b1 = 0.0
        self.b2 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0
        self.z1 = 0.0
        self.z2 = 0.0

    def reset(self) -> None:
        self.z1 = self.z2 = 0.0

    def set_hpf(self, fc: float, sr: float, q: float = 0.7071) -> None:
        w0 = 2.0 * math.pi * fc / sr
        cosw = math.cos(w0)
        sinw = math.sin(w0)
        alpha = sinw / (2.0 * q)
        b0 = (1.0 + cosw) / 2.0
        b1 = -(1.0 + cosw)
        b2 = (1.0 + cosw) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cosw
        a2 = 1.0 - alpha
        self.b0, self.b1, self.b2 = b0 / a0, b1 / a0, b2 / a0
        self.a1, self.a2 = a1 / a0, a2 / a0

    def set_lpf(self, fc: float, sr: float, q: float = 0.7071) -> None:
        w0 = 2.0 * math.pi * fc / sr
        cosw = math.cos(w0)
        sinw = math.sin(w0)
        alpha = sinw / (2.0 * q)
        b0 = (1.0 - cosw) / 2.0
        b1 = 1.0 - cosw
        b2 = (1.0 - cosw) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cosw
        a2 = 1.0 - alpha
        self.b0, self.b1, self.b2 = b0 / a0, b1 / a0, b2 / a0
        self.a1, self.a2 = a1 / a0, a2 / a0

    def set_high_shelf(self, fc: float, sr: float, gain_db: float, s: float = 0.8) -> None:
        a = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * math.pi * fc / sr
        cosw = math.cos(w0)
        sinw = math.sin(w0)
        alpha = sinw / 2.0 * math.sqrt((a + 1.0 / a) * (1.0 / s - 1.0) + 2.0)
        b0 = a * ((a + 1.0) + (a - 1.0) * cosw + 2.0 * math.sqrt(a) * alpha)
        b1 = -2.0 * a * ((a - 1.0) + (a + 1.0) * cosw)
        b2 = a * ((a + 1.0) + (a - 1.0) * cosw - 2.0 * math.sqrt(a) * alpha)
        a0 = (a + 1.0) - (a - 1.0) * cosw + 2.0 * math.sqrt(a) * alpha
        a1 = 2.0 * ((a - 1.0) - (a + 1.0) * cosw)
        a2 = (a + 1.0) - (a - 1.0) * cosw - 2.0 * math.sqrt(a) * alpha
        self.b0, self.b1, self.b2 = b0 / a0, b1 / a0, b2 / a0
        self.a1, self.a2 = a1 / a0, a2 / a0

    def process(self, x: np.ndarray) -> np.ndarray:
        y = np.empty_like(x)
        z1, z2 = self.z1, self.z2
        b0, b1, b2, a1, a2 = self.b0, self.b1, self.b2, self.a1, self.a2
        for i, s in enumerate(x):
            out = b0 * s + z1
            z1 = b1 * s - a1 * out + z2
            z2 = b2 * s - a2 * out
            y[i] = out
        self.z1, self.z2 = z1, z2
        return y


class VoiceChain:
    """Stereo-in, stereo-out. Uses left as the main NTG capsule (right may be safety)."""

    def __init__(self, sr: int = 48000) -> None:
        self.sr = sr
        self.hpf1 = Biquad()
        self.hpf2 = Biquad()
        self.low = Biquad()
        self.high = Biquad()
        self.shelf = Biquad()
        self.rnnoise = RNNoise()
        self._hpf_hz = -1
        self._hf = False
        self.env = 1e-5
        self.gr = 1.0
        self.comp_env = 1e-5
        self.gate_open = False
        self.gr_db = 0.0
        self._configure_filters(75, False)

    def _configure_filters(self, hpf_hz: int, hf_boost: bool) -> None:
        if hpf_hz != self._hpf_hz:
            fc = max(hpf_hz, 20)
            self.hpf1.set_hpf(fc, self.sr)
            self.hpf2.set_hpf(fc, self.sr)
            self._hpf_hz = hpf_hz
        if hf_boost != self._hf:
            self.shelf.set_high_shelf(5000.0, self.sr, 3.0 if hf_boost else 0.0)
            self._hf = hf_boost
        self.low.set_lpf(180.0, self.sr)
        self.high.set_hpf(3500.0, self.sr)

    def process(self, block: np.ndarray, s: DSPSettings) -> np.ndarray:
        self._configure_filters(s.hpf_hz if s.hpf_hz else 20, s.hf_boost)
        x = np.asarray(block, dtype=np.float32)
        if x.ndim == 1:
            x = x[:, None]
        # Main capsule is left; duplicate so Zoom/Discord never hear a -20 dB safety channel.
        mono = x[:, 0].astype(np.float64)
        if s.pad:
            mono *= db_to_lin(-20.0)
        if s.hpf_hz:
            mono = self.hpf1.process(mono)
            mono = self.hpf2.process(mono)
        if s.hf_boost:
            mono = self.shelf.process(mono)
        if s.suppress:
            mono = self.rnnoise.process(mono)

        peak = float(np.max(np.abs(mono))) + 1e-12
        atk = 1.0 - math.exp(-1.0 / (0.004 * self.sr))
        rel = 1.0 - math.exp(-1.0 / (0.12 * self.sr))
        coeff = atk if peak > self.env else rel
        self.env += coeff * (peak - self.env)

        gain = 1.0
        if s.gate:
            thresh = db_to_lin(s.gate_threshold_db)
            # Open above threshold, close 16 dB below it (hysteresis).
            if self.env > thresh:
                target = 1.0
            elif self.env < thresh * 0.16:
                target = db_to_lin(-18.0)
            else:
                target = self.gr
            g_atk = 1.0 - math.exp(-1.0 / (0.003 * self.sr))
            g_rel = 1.0 - math.exp(-1.0 / (0.16 * self.sr))
            gc = g_atk if target > self.gr else g_rel
            self.gr += gc * (target - self.gr)
            gain *= self.gr
            self.gate_open = self.gr > 0.6
        else:
            self.gr = 1.0
            self.gate_open = True

        if s.comp:
            # Amount maps threshold -24..-12 and ratio 1.5..4
            thresh_db = -24.0 + 12.0 * (1.0 - s.comp_amount)
            ratio = 1.5 + 2.5 * s.comp_amount
            thresh = db_to_lin(thresh_db)
            c_atk = 1.0 - math.exp(-1.0 / (0.008 * self.sr))
            c_rel = 1.0 - math.exp(-1.0 / (0.09 * self.sr))
            cc = c_atk if self.env > self.comp_env else c_rel
            self.comp_env += cc * (self.env - self.comp_env)
            if self.comp_env > thresh:
                over_db = lin_to_db(self.comp_env) - thresh_db
                red = over_db * (1.0 - 1.0 / ratio)
                gain *= db_to_lin(-red)
                gain *= db_to_lin(red * 0.45)  # makeup
        self.gr_db = lin_to_db(gain)

        mono = mono * gain

        if s.bottom and s.bottom_amount > 0:
            low = self.low.process(mono)
            drive = 1.4 + 2.2 * s.bottom_amount
            sat = np.tanh(low * drive)
            mono = mono + (sat - low) * (0.35 * s.bottom_amount)

        if s.excite and s.excite_amount > 0:
            high = self.high.process(mono)
            drive = 1.8 + 3.0 * s.excite_amount
            sat = np.tanh(high * drive)
            mono = mono + (sat - high) * (0.28 * s.excite_amount)

        mono *= db_to_lin(s.fader_db)
        if s.mute:
            mono *= 0.0

        # Soft ceiling so calls never square-wave.
        mono = np.tanh(mono * 1.15) / math.tanh(1.15)
        y = np.column_stack([mono, mono]).astype(np.float32)
        return y
