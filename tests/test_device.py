from __future__ import annotations

import unittest

from ntg_console.device import (
    firmware_is_current,
    firmware_tuple,
    is_call_app,
    parse_short_sources,
    parse_source_outputs,
)


SHORT_SOURCES = """\
64	alsa_output.pci-0000_19_00.6.analog-stereo.monitor	PipeWire	s32le 2ch 48000Hz	SUSPENDED
93	NTG_Console	PipeWire	float32le 2ch 48000Hz	IDLE
189	alsa_input.usb-R__DE_Microphones_R__DE_VideoMic_NTG_158E2530-00.analog-stereo	PipeWire	s24le 2ch 48000Hz	RUNNING
"""

SOURCE_OUTPUTS = """\
Source Output #235
	Driver: PipeWire
	Owner Module: n/a
	Client: 126
	Source: 189
	Sample Specification: float32le 2ch 48000Hz
	Channel Map: front-left,front-right
	Format: pcm, format.sample_format = "\\"float32le\\""
		application.name = "ALSA plug-in [python3.14]"
		application.process.id = "2351"
		application.process.binary = "python3.14"
		pulse.corked = "false"
Source Output #880
	Driver: PipeWire
	Source: 189
		application.name = "Chromium"
		application.process.binary = "chromium"
		pulse.corked = "false"
"""


class FirmwareTests(unittest.TestCase):
    def test_usb_bcd_one_twenty_is_1_2_0(self) -> None:
        self.assertEqual(firmware_tuple("1.20"), (1, 2, 0))

    def test_marketing_two_one_three(self) -> None:
        self.assertEqual(firmware_tuple("2.1.3"), (2, 1, 3))

    def test_usb_bcd_two_thirteen(self) -> None:
        self.assertEqual(firmware_tuple("2.13"), (2, 1, 3))

    def test_1_20_is_stale(self) -> None:
        self.assertFalse(firmware_is_current("1.20"))
        self.assertTrue(firmware_is_current("2.1.3"))
        self.assertTrue(firmware_is_current("2.13"))


class SourceOutputTests(unittest.TestCase):
    def test_parse_and_resolve(self) -> None:
        items = parse_source_outputs(SOURCE_OUTPUTS)
        names = parse_short_sources(SHORT_SOURCES)
        self.assertEqual(len(items), 2)
        for item in items:
            item["source"] = names.get(item["source_index"], "")
        self.assertEqual(items[0]["app"], "ALSA plug-in [python3.14]")
        self.assertFalse(is_call_app(items[0]))
        self.assertEqual(items[1]["app"], "Chromium")
        self.assertTrue(is_call_app(items[1]))
        self.assertTrue(items[1]["source"].endswith("VideoMic_NTG_158E2530-00.analog-stereo"))


if __name__ == "__main__":
    unittest.main()
