from __future__ import annotations

import unittest

import numpy as np

from ntg_console.dsp import (
    DSPSettings,
    VoiceChain,
    lin_to_db,
    safety_channel_db,
    safety_channel_likely,
)


def _run(chain: VoiceChain, block: np.ndarray, settings: DSPSettings, times: int = 8) -> np.ndarray:
    y = block
    for _ in range(times):
        y = chain.process(block, settings)
    return y


class SafetyTests(unittest.TestCase):
    def test_detects_twenty_db_right_channel(self) -> None:
        left = 0.1
        right = 0.1 * 10 ** (-20.0 / 20.0)
        self.assertAlmostEqual(safety_channel_db(left, right), 20.0, places=1)
        self.assertTrue(safety_channel_likely(left, right))

    def test_ignores_silence(self) -> None:
        self.assertFalse(safety_channel_likely(1e-6, 1e-7))

    def test_equal_channels_are_not_safety(self) -> None:
        self.assertFalse(safety_channel_likely(0.1, 0.1))


class VoiceChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = VoiceChain(48000)
        self.dry = DSPSettings(
            hpf_hz=0,
            pad=False,
            hf_boost=False,
            gate=False,
            comp=False,
            bottom=False,
            excite=False,
            suppress=False,
            fader_db=0.0,
            mute=False,
        )

    def test_uses_left_capsule_only(self) -> None:
        block = np.zeros((256, 2), dtype=np.float32)
        block[:, 1] = 0.5
        y = _run(self.chain, block, self.dry)
        self.assertLess(float(np.max(np.abs(y))), 0.02)

    def test_left_signal_reaches_both_outputs(self) -> None:
        block = np.zeros((256, 2), dtype=np.float32)
        block[:, 0] = 0.2
        y = _run(self.chain, block, self.dry)
        self.assertGreater(float(np.mean(np.abs(y[:, 0]))), 0.1)
        self.assertAlmostEqual(
            float(np.mean(y[:, 0])), float(np.mean(y[:, 1])), places=5
        )

    def test_mute_silences(self) -> None:
        settings = DSPSettings(**{**self.dry.__dict__, "mute": True})
        block = np.full((256, 2), 0.3, dtype=np.float32)
        y = _run(self.chain, block, settings)
        self.assertLess(float(np.max(np.abs(y))), 1e-6)

    def test_gate_closes_on_silence(self) -> None:
        chain = VoiceChain(48000)
        settings = DSPSettings(
            hpf_hz=0,
            pad=False,
            hf_boost=False,
            gate=True,
            gate_threshold_db=-42.0,
            comp=False,
            bottom=False,
            excite=False,
            suppress=False,
        )
        speech = np.full((512, 2), 0.2, dtype=np.float32)
        quiet = np.zeros((512, 2), dtype=np.float32)
        for _ in range(20):
            chain.process(speech, settings)
        self.assertTrue(chain.gate_open)
        for _ in range(int(1.5 * 48000 / 512)):
            chain.process(quiet, settings)
        self.assertFalse(chain.gate_open)

    def test_pad_drops_about_20db(self) -> None:
        block = np.full((256, 2), 0.2, dtype=np.float32)
        dry = _run(self.chain, block, self.dry)
        padded = _run(
            VoiceChain(48000),
            block,
            DSPSettings(**{**self.dry.__dict__, "pad": True}),
        )
        delta = lin_to_db(float(np.mean(np.abs(dry)))) - lin_to_db(
            float(np.mean(np.abs(padded)))
        )
        self.assertGreater(delta, 16.0)
        self.assertLess(delta, 24.0)


if __name__ == "__main__":
    unittest.main()
