# NTG Console

Linux companion for the [RØDE VideoMic NTG](https://rode.com/en/products/videomic-ntg). A desktop mixer that does the useful parts of RØDE Connect / Central on PipeWire: meters, Connect-style voice processors, USB gain lock, and a virtual microphone that Zoom / Discord / Meet can actually select.

**Not affiliated with RØDE.** RØDE, VideoMic, and Connect are trademarks of RØDE Microphones. This is an independent, class-compliant USB app for people who live on Linux.

## Why it exists

RØDE Central and Connect are Windows / Mac only. The NTG still works on Linux as a 24-bit / 48 kHz USB mic, but:

- the desktop volume slider maps **0–24 dB of extra digital gain** (100% is +24 dB — that is why a new NTG looks “noisy”)
- Plasma hides sink monitors, so a naive virtual mic never appears as an input
- the hardware HPF / pad / safety / HF boost live on the two buttons on the mic
- Connect’s gate, compressor, Big Bottom, and Aural Exciter never show up

NTG Console locks USB capture at **0 dB**, runs those processors in software, and publishes a real input named **`NTG_Console`**.

## Install

### From this tree (per-user, no root)

```bash
git clone https://github.com/matt-shearing/ntg-console.git
cd ntg-console
./install.sh
```

Then launch **NTG Console** from the application menu, or `ntg-console`.

### Arch / EndeavourOS (AUR, once published)

```bash
yay -S ntg-console
```

### Ad-hoc (no install)

```bash
python3 ntg-console
```

Needs: Python 3.11+, PyQt6, numpy, python-sounddevice, PipeWire / `pactl` / `pw-link`. Optional: `librnnoise` (already on most Arch boxes) for the RNNOISE key.

The audio engine is a **user systemd service**. It keeps the `NTG_Console` virtual mic alive after you close the window, and it does **not** steal your default headset. Pick `NTG_Console` in Zoom when you want it.

```bash
systemctl --user enable --now ntg-console.service   # start at login
systemctl --user status ntg-console.service
```

`./install.sh` enables the service. The GUI is only a control surface.

## Use it

1. Plug the VideoMic NTG in over USB-C. Foam windshield on.
2. Open NTG Console. USB capture stays **locked at 0 dB**.
3. In the sound menu pick input **`NTG_Console`**, not the raw “RØDE VideoMic NTG”.
4. Leave speakers / headset on the Arctis (or whatever you already use).
5. Start on the **CALLS** preset. Talk. The red tally means the gate is open.
6. If voice is quiet, turn the **knob on the mic**, not the KDE slider.

Hardware on the mic itself (the app cannot flip these until HID is reversed):

- EQ button: 75 Hz HPF for a desk + PC (press once, left LED)
- Power button: pad and safety **off** (safety makes USB right-channel −20 dB)
- Gain knob: start at 10, peaks around −18 to −12 dB, red peak LED never flashes

## Processors

| Key | What it is |
|---|---|
| High-pass 75 / 150 | Same corners as the hardware filter |
| Pad −20 | Software pad |
| HF boost | +3 dB shelf ~5 kHz |
| RNNOISE | `librnnoise` suppressor |
| Noise gate | Voice gate with hysteresis |
| Compressor | Light voice compressor + makeup |
| Big Bottom / Aural Exciter | Harmonic extras in the spirit of Connect’s APHEX pair |

Presets: **Calls** (HPF 75 + RNNoise + gate + comp), **Broadcast** (adds HF / Bottom / Exciter), **Raw** (straight through).

## UX Pilot

The visual redesign brief lives in [`UX-PILOT.md`](UX-PILOT.md). Paste the hero prompt into [UX Pilot](https://uxpilot.ai) (HiFi, Desktop 1440×900, 4 looks, then Deep AI Design + Autoflow). Bring the frames back and we restyle the PyQt window — we are not wrapping this in Electron.

## Firmware

Firmware updates still need RØDE Central on a Windows or Mac box. The NTG exposes a vendor HID interface (`/dev/hidraw*`, usage page `0xFF00`); `99-rode-ntg.rules` gives the `audio` group access so we can talk to it later. This app does **not** write mystery bytes to the mic.

## License

MIT. See [LICENSE](LICENSE).
