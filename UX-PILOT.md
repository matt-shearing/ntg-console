# NTG Console — UX Pilot brief

Written for [UX Pilot](https://uxpilot.ai). This is the Linux companion for a RØDE VideoMic NTG: a desktop mixer that does what RØDE Connect / Central do on Windows and Mac. The v1 PyQt window works. This pass is for a look that could not be mistaken for a generic dark Electron mixer.

## How to run this in UX Pilot

1. **HiFi UI Design** (not wireframe).
2. **Device: Desktop** first. Canvas **1440×900**. This is a native Linux window, not a browser, not a phone.
3. Paste the hero prompt below. **Enhance prompt** once, then overwrite anything generic it adds (Inter, charcoal SaaS, purple glow).
4. **Explore 4 looks** on the mixer desk. Pick one direction. Do not average them.
5. **Deep AI Design** on the winner.
6. **Autoflow** the remaining screens (do not generate one at a time).
7. **Max Web Design** last, for empty / mic-unplugged / clipping / recording.
8. Follow-up via **Quick edit**, one change per prompt.
9. Export: **Save & Retrieve Figma**, or **Source Code** if you want HTML to steal structure from. Implementation is PyQt6, not a web app — we will rebuild the look in Qt.

## What it is

A single-window Linux desktop app. It talks to one VideoMic NTG over USB, runs Connect-style voice processors (HPF, RNNoise, gate, compressor, Big Bottom, Aural Exciter), and publishes a virtual microphone named `NTG_Console` that Zoom / Discord / Meet can select. Hardware USB gain stays locked at 0 dB; the physical knob on the mic is the real level.

**Audience.** One person at a desk with a shotgun on a boom or stand, on EndeavourOS / Arch / any PipeWire Linux box. They already own the mic. They do not want Windows, Wine, or RØDE Central.

**What's wrong with v1.** It is a competent dark panel: Inter, chip buttons, two meters, gold accent. It works. It also looks like every other AI mixer. The product is a *location-sound cart*, and the UI is not one yet.

**Idea.** You are looking at the engraved lid of a boom-op's sound bag. Anodised aluminium, a physical VU, a red tally lamp that means the gate is open, real faders, processor keys that click like the switches on the back of the NTG. Not RØDE Connect (we cannot copy their chrome). Not a DAW. A cart.

**UX Pilot settings.** Desktop 1440×900. Deep AI Design. 4 looks. Then Autoflow.

---

### Prompt — mixer desk (hero)

```
Design a high-fidelity desktop application window (1440×900) for NTG Console, a native Linux mixer for one RØDE VideoMic NTG. Used by a single person on calls and recordings. Not a browser. Not a DAW. Not RØDE Connect. Not a SaaS dashboard.

Metaphor: the engraved lid of a location-sound cart. Anodised aluminium plate, a flight-case latch, a physical VU meter, a red tally lamp. You can feel the screws. The window is a piece of kit on the desk, not a website in a frame.

Visual world
- Plate: graphite #1B2129
- Recessed well: #12161C
- Engraved hairline: #3A4350
- Brass (latches, screw heads, meter rim): #C9A227
- Ink on the plate: #E8EDF2
- Quiet engraving: #8B93A0
- Tally / on-air (only when the gate is open): signal red #E23B2C
- Meter green: #1F8A5B
- Meter amber: #C9A227
- Meter red: #E23B2C
- Type: "Fira Sans Compressed" for stencilled panel labels (CHANNEL 1, PROCESS, USB MIXER); "Inter" for body; "Fira Code" for dB readouts. No Inter-only UI. No Roboto. No SF Pro.
- No purple, no glassmorphism, no sidebar of icons, no Electron traffic-lights as the personality, no "modern dark mode SaaS"

Window chrome
- Native Linux window, dark titlebar, app icon is a shotgun mic on a brass-bezelled plate with a red tally LED.
- Wordmark top-left, engraved, not a marketing logo: NTG CONSOLE
- Tiny subtitle in compressed caps: VIDEOMIC NTG · USB COMPANION
- Top-right: a physical tally lamp (round, recessed). Lit red = gate open / on air. Dark = silent. Label ON AIR engraved under it.
- Device line under the wordmark, real copy: RØDE VideoMic NTG · 158E2530 · USB 1.20 · capture +0 dB

Layout — a cart lid, not a settings form
Left column (280px) is CHANNEL 1, a raised well:
- Two vertical mechanical VU meters, IN and OUT, with a peak pip. Scale marks at -60, -18, -6, 0.
- A single red-capped fader, 0 dB at the detent, range -24 to +12, value in Fira Code under it: +0 dB
- MUTE as a square latching key, not a pill. Lit brass when down.
- Peak readout: IN  -14.4 dB     OUT  -12.1 dB

Right of the channel is PROCESS, engraved as a row of hardware keys and one trim per key:
- HIGH-PASS: three mutually exclusive keys Off · 75 Hz · 150 Hz. 75 Hz is down.
- PAD −20 dB (up) and HF BOOST (up)
- RNNOISE (down) — label it RNNOISE, not "AI" or "magic"
- NOISE GATE (down) plus a small threshold trim currently at -42 dB
- COMPRESSOR (down) plus an amount trim
- BIG BOTTOM (up) plus a trim
- AURAL EXCITER (up) plus a trim
Keys are square, slightly proud, brass edge when engaged, graphite when not. They look like the switches on the back of the microphone.

Below PROCESS, a thinner well: HARDWARE · USB MIXER
- USB capture: a trim locked at 0 dB. A latching key LOCK 0 dB is down. The lock is the point of the product — do not draw this as a scary warning, draw it as a set-and-forget switch.
- NTG 3.5 mm jack level trim, and a DIRECT MONITOR key (up)
- One quiet line of copy: "Level lives on the knob on the mic. USB stays at unity."

Bottom rail
- Preset keys: CALLS (down) · BROADCAST · RAW
- 12s TEST (momentary) · RECORD (latching, red when down)
- Status engraved on the plate, not a toast: Preset calls loaded. In the sound menu pick input NTG_Console — not the raw RØDE device.

Use this real content, not lorem
- Serial 158E2530
- Firmware USB 1.20
- Speech peaks −14.4 dB, floor −53 dB, SNR 19 dB on the last take
- Virtual mic name: NTG_Console
- Output / headset stays the Arctis Nova Pro. This window does not become the speaker.

Do not
- Do not copy RØDE Connect, RØDE Central, or RØDECaster chrome
- Do not draw a 3-column card grid or a left icon rail
- Do not use Inter on #0f1115 with blue pills
- Do not invent a user avatar, a cloud account, or a store
- Do not write "Welcome to NTG Console" or "John Doe"
- Do not look like OBS, Voicemeeter, Equalizer APO, or Chrome
- Do not put a fake 3D shotgun render in the middle of the window — the icon already did that. The window is the cart.
```

### Follow-ups

- `Make the VU meters actually mechanical: a needle, a printed scale, a brass rim. Peak is a separate red pip, not a software bar.`
- `The tally lamp is the only saturated red in the window. Everything else stays graphite and brass until RECORD is down.`
- `Processor keys should look pressable. Engaged = slightly recessed + brass edge. Not yellow pills.`

### Autoflow screens

1. **Mixer desk** (hero, above) — mic connected, Calls preset, gate open, tally lit.
2. **Mic unplugged** — same lid, channel well empty, tally dark, one engraved line: Plug the VideoMic NTG in over USB-C. PROCESS keys disabled.
3. **12s test running** — TEST key held, a small mechanical timer 4.0 SILENT → 8.0 TALK, meters live.
4. **Test result** — a stamped take slip in the well: GOOD — ready for calls. Peaks −14.4 · floor −53.1 · SNR 19.3. Three one-line notes from the real analyser.
5. **Recording** — RECORD down, red tally and a running counter 00:03:12, path `~/.local/share/ntg-console/take.wav`.
6. **Clipping** — peak pip pinned, a brass-edged flag PEAK, copy: Turn the knob on the mic, not USB gain.
7. **About / first run** — the same plate, three sentences: Linux companion for the VideoMic NTG. Not affiliated with RØDE. USB gain stays at 0 dB. A single key: OPEN MIXER.

---

## After UX Pilot

Bring the Figma / exported frames back here. Implementation is the existing PyQt6 app in `ntg_console/app.py` — we restyle that window to match the chosen look. We do not wrap it in Electron.
