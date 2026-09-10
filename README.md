# NTG Console

Linux companion for the [RØDE VideoMic NTG](https://rode.com/en/products/videomic-ntg). A desktop mixer that covers the useful parts of RØDE Connect / Central on PipeWire: meters, voice processors, a USB gain lock, and a virtual microphone that Zoom, Discord, and Meet can select.

**Not affiliated with RØDE.** RØDE, VideoMic, and Connect are trademarks of RØDE Microphones. This is an independent, class-compliant USB app.

## Why it exists

RØDE Central and Connect are Windows and Mac only. The NTG still works on Linux as a 24-bit / 48 kHz USB mic, but:

- the desktop volume slider maps **0–24 dB of extra digital gain** (100% is +24 dB, which is why a new NTG looks noisy)
- a sink monitor does not show up as a microphone in Plasma
- Connect’s gate, compressor, Big Bottom, and Aural Exciter are not available

NTG Console locks USB capture at **0 dB**, runs those processors in software, and publishes an input named **`NTG_Console`**. The engine is a user service, so the virtual mic stays up after you close the window. It does not steal your default headset, speakers, or microphone — pick `NTG_Console` in an app when you want it.

## Install

### From source (per-user, no root)

```bash
git clone https://github.com/matt-shearing/ntg-console.git
cd ntg-console
./install.sh
```

Then launch **NTG Console** from the application menu, or run `ntg-console`.

`./install.sh` also enables the user service so the virtual mic starts at login.

```bash
systemctl --user status ntg-console.service
ntg-console doctor
```

### Arch Linux / EndeavourOS

AUR package `ntg-console` is planned. Until then, use the source install above.

### Dependencies

Python 3.11+, PyQt6, numpy, python-sounddevice, PipeWire (`pactl`, `pw-link`). Optional: `rnnoise` for the RNNOISE key.

## Use

1. Plug the VideoMic NTG in over USB-C. Leave the foam windshield on.
2. Open NTG Console. USB capture stays **locked at 0 dB**.
3. In the sound menu (or Zoom / Discord / Gather), pick input **`NTG_Console`**, not the raw “RØDE VideoMic NTG”.
4. Keep your existing headset or speakers for playback.
5. Start on the **Calls** preset.
6. If voice is quiet, turn the **knob on the mic**, not the desktop slider.

Hardware on the mic itself:

- EQ button: 75 Hz high-pass for a desk and a PC (press once, left LED)
- Power button: pad and safety **off** (safety makes the USB right channel −20 dB)
- Gain knob: start at 10. Peaks around −18 to −12 dB. The red peak LED should never flash.

## Processors

| Control | What it does |
|---|---|
| High-pass 75 / 150 | Same corners as the hardware filter |
| Pad −20 | Software pad |
| HF boost | +3 dB shelf around 5 kHz |
| RNNOISE | `librnnoise` suppressor |
| Noise gate | Voice gate with hysteresis |
| Compressor | Light voice compressor with makeup gain |
| Big Bottom / Aural Exciter | Low / high harmonic extras in the spirit of Connect’s APHEX pair |

Presets: **Calls** (75 Hz, RNNoise, gate — no compressor), **Broadcast** (adds compressor, HF boost, Big Bottom, Exciter), **Raw** (straight through).

Calls leaves the compressor off on purpose. Makeup gain on a supercardioid flattens the pattern (off-axis sound is pulled up to speech level) and then Chromium's AGC in Gather fights it. Broadcast still has the compressor for recordings that will not go through a browser.

If something sounds wrong:

```bash
ntg-console doctor
```

That prints firmware, USB gain, which app is capturing which source, and whether the safety channel looks engaged.

## Firmware

Firmware updates still need RØDE Central on Windows or Mac. This app does not flash the microphone. RØDE's current VideoMic NTG firmware is **2.1.3**. USB `bcdDevice` `1.20` is firmware 1.2.0; update that.

## License

MIT. See [LICENSE](LICENSE).
