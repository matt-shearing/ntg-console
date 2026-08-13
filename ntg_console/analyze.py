"""Score a recorded take the same way NTG Check does."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .dsp import lin_to_db

DATA_DIR = Path.home() / ".local" / "share" / "ntg-console"


@dataclass
class TestResult:
    recorded_at: str
    duration_s: float
    floor_rms_db: float
    speech_rms_db: float
    speech_peak_db: float
    snr_db: float
    clip_samples: int
    stereo_delta_db: float
    verdict: str
    notes: list[str]
    wav_path: str


def analyze(samples: np.ndarray, sr: int, wav_path: Path) -> TestResult:
    if samples.size == 0:
        return TestResult(
            recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            duration_s=0,
            floor_rms_db=-120,
            speech_rms_db=-120,
            speech_peak_db=-120,
            snr_db=0,
            clip_samples=0,
            stereo_delta_db=0,
            verdict="No audio captured",
            notes=["Record a take first."],
            wav_path=str(wav_path),
        )
    if samples.ndim == 1:
        samples = samples[:, None]
    win = max(int(0.05 * sr), 32)
    rms_w = []
    peaks = []
    for i in range(0, max(len(samples) - win, 0), win):
        chunk = samples[i : i + win]
        rms_w.append(float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2))))
        peaks.append(float(np.max(np.abs(chunk))))
    floor = float(np.percentile(rms_w, 20)) if rms_w else 1e-6
    speech = float(np.percentile(rms_w, 80)) if rms_w else 1e-6
    peak = max(peaks) if peaks else 1e-6
    snr = lin_to_db(speech) - lin_to_db(floor)
    clips = int(np.sum(np.abs(samples) >= 0.99))
    left = samples[:, 0]
    right = samples[:, 1] if samples.shape[1] > 1 else left
    l = float(np.sqrt(np.mean(left.astype(np.float64) ** 2)))
    r = float(np.sqrt(np.mean(right.astype(np.float64) ** 2)))
    stereo = abs(lin_to_db(l) - lin_to_db(r))
    notes: list[str] = []
    if clips:
        notes.append("Clipping. Turn the physical knob down.")
    elif lin_to_db(peak) > -6:
        notes.append(f"Peaks {lin_to_db(peak):.1f} dB — a touch hot.")
    elif lin_to_db(peak) < -22:
        notes.append(f"Peaks {lin_to_db(peak):.1f} dB — turn the mic knob up, not the OS slider.")
    else:
        notes.append(f"Peaks {lin_to_db(peak):.1f} dB — good call level.")
    if lin_to_db(floor) > -42:
        notes.append(f"Floor {lin_to_db(floor):.1f} dB — engage 75 Hz HPF.")
    else:
        notes.append(f"Floor {lin_to_db(floor):.1f} dB — quiet enough.")
    if snr < 16:
        notes.append(f"SNR {snr:.1f} dB — get closer or more on-axis.")
    elif snr < 24:
        notes.append(f"SNR {snr:.1f} dB — acceptable for calls.")
    else:
        notes.append(f"SNR {snr:.1f} dB — strong.")
    if clips or lin_to_db(peak) > -3:
        verdict = "HOT — turn the knob down"
    elif lin_to_db(peak) < -28 or snr < 12:
        verdict = "WEAK — needs gain or placement"
    elif snr >= 20 and -22 <= lin_to_db(peak) <= -6:
        verdict = "GOOD — ready for calls"
    else:
        verdict = "OK — usable"
    return TestResult(
        recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        duration_s=len(samples) / sr,
        floor_rms_db=round(lin_to_db(floor), 2),
        speech_rms_db=round(lin_to_db(speech), 2),
        speech_peak_db=round(lin_to_db(peak), 2),
        snr_db=round(snr, 2),
        clip_samples=clips,
        stereo_delta_db=round(stereo, 2),
        verdict=verdict,
        notes=notes,
        wav_path=str(wav_path),
    )


def save_wav(path: Path, samples: np.ndarray, sr: int) -> None:
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    ch = pcm.shape[1] if pcm.ndim > 1 else 1
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def save_report(result: TestResult) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = DATA_DIR / "last-report.json"
    p.write_text(json.dumps(asdict(result), indent=2) + "\n")
    return p
