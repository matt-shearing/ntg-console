#!/usr/bin/env python3
"""NTG Console — Linux companion for the RØDE VideoMic NTG."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import device
from .dsp import lin_to_db
from .ipc import Client, ensure_daemon
from .settings import load as load_settings, save as save_settings

PRESETS = {
    "calls": {
        "hpf_hz": 75,
        "pad": False,
        "hf_boost": False,
        "gate": True,
        "gate_threshold_db": -42.0,
        "comp": True,
        "comp_amount": 0.55,
        "bottom": False,
        "bottom_amount": 0.35,
        "excite": False,
        "excite_amount": 0.3,
        "suppress": True,
        "fader_db": 0.0,
    },
    "broadcast": {
        "hpf_hz": 75,
        "pad": False,
        "hf_boost": True,
        "gate": True,
        "gate_threshold_db": -40.0,
        "comp": True,
        "comp_amount": 0.7,
        "bottom": True,
        "bottom_amount": 0.4,
        "excite": True,
        "excite_amount": 0.35,
        "suppress": True,
        "fader_db": 0.0,
    },
    "raw": {
        "hpf_hz": 0,
        "pad": False,
        "hf_boost": False,
        "gate": False,
        "comp": False,
        "bottom": False,
        "excite": False,
        "suppress": False,
        "fader_db": 0.0,
    },
}


class Meter(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rms = -90.0
        self.peak = -90.0
        self.setMinimumSize(36, 220)

    def set_levels(self, rms_db: float, peak_db: float) -> None:
        self.rms = rms_db
        self.peak = peak_db
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(8, 8, -8, -8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0d1116"))
        p.drawRoundedRect(r, 4, 4)

        def h_of(db: float) -> float:
            t = (max(-60.0, min(0.0, db)) + 60.0) / 60.0
            return r.height() * t

        rms_h = h_of(self.rms)
        peak_y = r.bottom() - h_of(self.peak)
        grad = QLinearGradient(0, r.bottom(), 0, r.top())
        grad.setColorAt(0.0, QColor("#1f8a5b"))
        grad.setColorAt(0.62, QColor("#c9a227"))
        grad.setColorAt(0.86, QColor("#e36a1a"))
        grad.setColorAt(1.0, QColor("#e23b2c"))
        p.setBrush(grad)
        p.drawRect(QRectF(r.left() + 3, r.bottom() - rms_h, r.width() - 6, rms_h))
        p.setPen(QPen(QColor("#f4efe4"), 2))
        p.drawLine(r.left() + 1, int(peak_y), r.right() - 1, int(peak_y))
        p.end()


class Tally(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on = False
        self.setFixedSize(18, 18)

    def set_on(self, on: bool) -> None:
        if on != self.on:
            self.on = on
            self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e23b2c") if self.on else QColor("#3a2220"))
        p.drawEllipse(1, 1, 16, 16)
        p.end()


class Chip(QPushButton):
    def __init__(self, text: str, checkable: bool = True) -> None:
        super().__init__(text)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("chip", True)


class Console(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NTG Console")
        self.resize(920, 620)
        self.client = Client()
        self.info = device.poll()
        self._building = True
        self._meters = {}

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 18, 22, 16)
        outer.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        eye = QLabel("VIDEOMIC NTG  ·  USB COMPANION")
        eye.setObjectName("eyebrow")
        name = QLabel("NTG Console")
        name.setObjectName("title")
        self.dev_lbl = QLabel("looking for microphone…")
        self.dev_lbl.setObjectName("device")
        titles.addWidget(eye)
        titles.addWidget(name)
        titles.addWidget(self.dev_lbl)
        header.addLayout(titles, 1)
        self.tally = Tally()
        tally_col = QVBoxLayout()
        tally_lab = QLabel("ON AIR")
        tally_lab.setObjectName("kicker")
        tally_col.addWidget(tally_lab, alignment=Qt.AlignmentFlag.AlignRight)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.tally)
        tally_col.addLayout(row)
        header.addLayout(tally_col)
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        strip = QFrame()
        strip.setObjectName("strip")
        sl = QVBoxLayout(strip)
        sl.addWidget(self._kicker("CHANNEL 1"))
        meters = QHBoxLayout()
        self.meter_in = Meter()
        self.meter_out = Meter()
        meters.addWidget(self._meter_col("IN", self.meter_in))
        meters.addWidget(self._meter_col("OUT", self.meter_out))
        sl.addLayout(meters, 1)
        self.peak_lbl = QLabel("IN  —     OUT  —")
        self.peak_lbl.setObjectName("mono")
        sl.addWidget(self.peak_lbl)
        sl.addWidget(self._kicker("LEVEL"))
        self.fader = QSlider(Qt.Orientation.Vertical)
        self.fader.setRange(-24, 12)
        self.fader.setValue(0)
        self.fader.setFixedHeight(160)
        self.fader.valueChanged.connect(self._push)
        frow = QHBoxLayout()
        frow.addStretch(1)
        frow.addWidget(self.fader)
        frow.addStretch(1)
        sl.addLayout(frow)
        self.fader_lbl = QLabel("0 dB")
        self.fader_lbl.setObjectName("mono")
        sl.addWidget(self.fader_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.mute_btn = Chip("MUTE")
        self.mute_btn.toggled.connect(self._push)
        sl.addWidget(self.mute_btn)
        body.addWidget(strip)

        right = QVBoxLayout()
        right.addWidget(self._kicker("PROCESS  ·  CONNECT-STYLE DSP"))

        proc = QFrame()
        proc.setObjectName("panel")
        pg = QGridLayout(proc)
        pg.setHorizontalSpacing(12)
        pg.setVerticalSpacing(10)

        pg.addWidget(self._kicker("HIGH-PASS"), 0, 0)
        hpf_row = QHBoxLayout()
        self.hpf_group = QButtonGroup(self)
        self.hpf_group.setExclusive(True)
        self.hpf_btns = {}
        for hz, label in ((0, "Off"), (75, "75 Hz"), (150, "150 Hz")):
            b = Chip(label)
            self.hpf_group.addButton(b)
            self.hpf_btns[hz] = b
            b.toggled.connect(self._push)
            hpf_row.addWidget(b)
        hpf_row.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(hpf_row)
        pg.addWidget(wrap, 0, 1, 1, 2)

        self.pad_btn = Chip("PAD −20 dB")
        self.hf_btn = Chip("HF BOOST")
        self.pad_btn.toggled.connect(self._push)
        self.hf_btn.toggled.connect(self._push)
        pg.addWidget(self.pad_btn, 1, 1)
        pg.addWidget(self.hf_btn, 1, 2)

        self.suppress_btn = Chip("RNNOISE")
        self.suppress_btn.setChecked(True)
        self.suppress_btn.toggled.connect(self._push)
        self.gate_btn = Chip("NOISE GATE")
        self.gate_btn.setChecked(True)
        self.gate_btn.toggled.connect(self._push)
        self.gate_s = self._slider(-60, -20, -42, "GATE")
        pg.addWidget(self.suppress_btn, 2, 0)
        pg.addWidget(self.gate_btn, 2, 1)
        pg.addWidget(self.gate_s, 2, 2)

        self.comp_btn = Chip("COMPRESSOR")
        self.comp_btn.setChecked(True)
        self.comp_btn.toggled.connect(self._push)
        self.comp_s = self._slider(0, 100, 55, "COMP")
        pg.addWidget(self.comp_btn, 3, 0)
        pg.addWidget(self.comp_s, 3, 1, 1, 2)

        self.bottom_btn = Chip("BIG BOTTOM")
        self.bottom_btn.toggled.connect(self._push)
        self.bottom_s = self._slider(0, 100, 40, "LOW")
        pg.addWidget(self.bottom_btn, 4, 0)
        pg.addWidget(self.bottom_s, 4, 1, 1, 2)

        self.excite_btn = Chip("AURAL EXCITER")
        self.excite_btn.toggled.connect(self._push)
        self.excite_s = self._slider(0, 100, 30, "AIR")
        pg.addWidget(self.excite_btn, 5, 0)
        pg.addWidget(self.excite_s, 5, 1, 1, 2)

        right.addWidget(proc)

        right.addWidget(self._kicker("HARDWARE  ·  USB MIXER"))
        hw = QFrame()
        hw.setObjectName("panel")
        hg = QGridLayout(hw)
        self.usb_s = self._slider(0, 24, 0, "USB GAIN")
        self.lock_btn = Chip("LOCK 0 dB")
        self.lock_btn.setChecked(True)
        self.lock_btn.toggled.connect(self._on_lock)
        hg.addWidget(QLabel("USB capture"), 0, 0)
        hg.addWidget(self.usb_s, 0, 1)
        hg.addWidget(self.lock_btn, 0, 2)
        self.jack_s = self._slider(-60, 0, -23, "JACK")
        self.direct_btn = Chip("DIRECT MONITOR")
        self.direct_btn.toggled.connect(self._on_direct)
        hg.addWidget(QLabel("NTG 3.5 mm"), 1, 0)
        hg.addWidget(self.jack_s, 1, 1)
        hg.addWidget(self.direct_btn, 1, 2)
        self.usb_s.valueChanged.connect(self._on_usb)
        self.jack_s.valueChanged.connect(self._on_jack)
        right.addWidget(hw)

        right.addWidget(self._kicker("PRESET"))
        pre = QHBoxLayout()
        self.pre_calls = Chip("CALLS")
        self.pre_bcast = Chip("BROADCAST")
        self.pre_raw = Chip("RAW")
        for b, name in (
            (self.pre_calls, "calls"),
            (self.pre_bcast, "broadcast"),
            (self.pre_raw, "raw"),
        ):
            b.clicked.connect(lambda _=False, n=name: self.apply_preset(n))
            pre.addWidget(b)
        pre.addStretch(1)
        self.rec_btn = Chip("RECORD", checkable=True)
        self.rec_btn.toggled.connect(self._toggle_rec)
        self.test_btn = Chip("12s TEST", checkable=False)
        self.test_btn.clicked.connect(self._run_test)
        pre.addWidget(self.test_btn)
        pre.addWidget(self.rec_btn)
        right.addLayout(pre)

        self.status = QLabel(
            "Engine runs in the background. Close this window — NTG_Console stays. "
            "Pick it in Zoom when you want it; this app will not steal your headset."
        )
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        right.addWidget(self.status)
        right.addStretch(1)
        body.addLayout(right, 1)
        outer.addLayout(body, 1)

        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #14181e; color: #e8edf2; font-family: Inter, "Fira Sans"; }
            QLabel#eyebrow { color: #c9a227; letter-spacing: 2px; font: 600 11px "Fira Sans Compressed"; }
            QLabel#title { font: 600 28px Inter; color: #f4efe4; }
            QLabel#device { font: 13px Inter; color: #8b93a0; }
            QLabel#kicker { color: #8b93a0; letter-spacing: 1.4px; font: 600 10px "Fira Sans Compressed"; }
            QLabel#mono { font: 600 12px "Fira Code"; color: #c5cdd6; }
            QLabel#status { font: 13px Inter; color: #b7c0c9; }
            QFrame#strip, QFrame#panel {
                background: #1b2129; border: 1px solid #2a323c; border-radius: 10px;
            }
            QFrame#strip { padding: 12px; }
            QPushButton[chip="true"] {
                background: #242b34; color: #d5dbe2; border: 1px solid #3a4350;
                border-radius: 7px; padding: 7px 11px; font: 600 12px Inter;
            }
            QPushButton[chip="true"]:hover { border-color: #c9a227; }
            QPushButton[chip="true"]:checked {
                background: #c9a227; color: #14181e; border-color: #c9a227;
            }
            QSlider::groove:horizontal { height: 4px; background: #2a323c; border-radius: 2px; }
            QSlider::handle:horizontal { width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; background: #e8edf2; }
            QSlider::groove:vertical { width: 6px; background: #2a323c; border-radius: 3px; }
            QSlider::handle:vertical { height: 16px; width: 16px; margin: 0 -5px; border-radius: 8px; background: #e23b2c; }
            """
        )

        self._building = False
        self.apply_preset("calls")
        self._load()
        self._start_audio()
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.dev_timer = QTimer(self)
        self.dev_timer.setInterval(1500)
        self.dev_timer.timeout.connect(self._refresh_device)
        self.dev_timer.start()
        self._refresh_device()

    def _kicker(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("kicker")
        return lab

    def _meter_col(self, name: str, meter: Meter) -> QWidget:
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self._kicker(name), alignment=Qt.AlignmentFlag.AlignHCenter)
        col.addWidget(meter, 1)
        return box

    def _slider(self, lo: int, hi: int, val: int, name: str) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setObjectName(name)
        s.valueChanged.connect(self._push)
        return s

    def apply_preset(self, name: str) -> None:
        p = PRESETS[name]
        self._building = True
        self.hpf_btns[p["hpf_hz"]].setChecked(True)
        self.pad_btn.setChecked(p["pad"])
        self.hf_btn.setChecked(p["hf_boost"])
        self.suppress_btn.setChecked(p.get("suppress", True))
        self.gate_btn.setChecked(p["gate"])
        if "gate_threshold_db" in p:
            self.gate_s.setValue(int(p["gate_threshold_db"]))
        self.comp_btn.setChecked(p["comp"])
        if "comp_amount" in p:
            self.comp_s.setValue(int(p["comp_amount"] * 100))
        self.bottom_btn.setChecked(p["bottom"])
        if "bottom_amount" in p:
            self.bottom_s.setValue(int(p["bottom_amount"] * 100))
        self.excite_btn.setChecked(p["excite"])
        if "excite_amount" in p:
            self.excite_s.setValue(int(p["excite_amount"] * 100))
        self.fader.setValue(int(p["fader_db"]))
        self.pre_calls.setChecked(name == "calls")
        self.pre_bcast.setChecked(name == "broadcast")
        self.pre_raw.setChecked(name == "raw")
        self._building = False
        self._push()
        self.status.setText(
            f"Preset {name} loaded. Pick input NTG_Console in an app when you want it — "
            "we will not change your default headset."
        )

    def _hpf(self) -> int:
        for hz, b in self.hpf_btns.items():
            if b.isChecked():
                return hz
        return 75

    def _push(self, *_args) -> None:
        if self._building:
            return
        self.fader_lbl.setText(f"{self.fader.value():+d} dB")
        patch = {
            "hpf_hz": self._hpf(),
            "pad": self.pad_btn.isChecked(),
            "hf_boost": self.hf_btn.isChecked(),
            "suppress": self.suppress_btn.isChecked(),
            "gate": self.gate_btn.isChecked(),
            "gate_threshold_db": float(self.gate_s.value()),
            "comp": self.comp_btn.isChecked(),
            "comp_amount": self.comp_s.value() / 100.0,
            "bottom": self.bottom_btn.isChecked(),
            "bottom_amount": self.bottom_s.value() / 100.0,
            "excite": self.excite_btn.isChecked(),
            "excite_amount": self.excite_s.value() / 100.0,
            "fader_db": float(self.fader.value()),
            "mute": self.mute_btn.isChecked(),
            "lock_usb": self.lock_btn.isChecked(),
        }
        save_settings(patch)
        try:
            self.client.request({"cmd": "set", "settings": patch})
        except OSError:
            self.status.setText("Background engine is not running yet.")

    def _on_lock(self, on: bool) -> None:
        self.usb_s.setEnabled(not on)
        if on:
            device.set_usb_gain_db(0)
            self.usb_s.blockSignals(True)
            self.usb_s.setValue(0)
            self.usb_s.blockSignals(False)

    def _on_usb(self, val: int) -> None:
        if self.lock_btn.isChecked():
            return
        device.set_usb_gain_db(val)

    def _on_jack(self, val: int) -> None:
        device.set_jack_db(val)

    def _on_direct(self, on: bool) -> None:
        device.set_direct_monitor(on)

    def _start_audio(self) -> None:
        # Start or attach to the background engine. Do not touch default devices.
        self.client = ensure_daemon()
        if not self.client.alive():
            self.status.setText("Could not start the background engine.")
            return
        if self.lock_btn.isChecked():
            device.set_usb_gain_db(0)
        self._push()

    def _refresh_device(self) -> None:
        info = device.poll()
        self.info = info
        if info.connected:
            self.dev_lbl.setText(
                f"RØDE VideoMic NTG  ·  {info.serial}  ·  USB {info.firmware}  ·  "
                f"capture {info.usb_gain_db:+.0f} dB"
            )
        else:
            self.dev_lbl.setText("Microphone not found — plug the NTG in over USB-C.")

    def _tick(self) -> None:
        try:
            m = self.client.request({"cmd": "meters"}, timeout=0.4)
        except OSError:
            self.tally.set_on(False)
            return
        if not m.get("ok"):
            return
        self.meter_in.set_levels(m.get("in_rms_db", -90), m.get("in_peak_db", -90))
        self.meter_out.set_levels(m.get("out_rms_db", -90), m.get("out_peak_db", -90))
        self.peak_lbl.setText(
            f"IN  {m.get('in_peak_db', -90):6.1f} dB     OUT  {m.get('out_peak_db', -90):6.1f} dB"
        )
        self.tally.set_on(
            bool(m.get("gate_open"))
            and not self.mute_btn.isChecked()
            and bool(m.get("running"))
        )
        err = m.get("error") or ""
        if err and "xrun" not in err:
            self.status.setText(f"Engine: {err}")

    def _toggle_rec(self, on: bool) -> None:
        try:
            if on:
                self.client.request({"cmd": "record_start"})
                self.rec_btn.setText("STOP")
                self.status.setText("Recording processed output…")
            else:
                reply = self.client.request({"cmd": "record_stop"}, timeout=5.0)
                self.rec_btn.setText("RECORD")
                self.status.setText(
                    f"{reply.get('verdict', 'saved')}  ·  {reply.get('wav', '')}"
                )
        except OSError:
            self.status.setText("Background engine is not running.")
            self.rec_btn.setChecked(False)

    def _run_test(self) -> None:
        self.status.setText("Recording 12s processed take — stay quiet 4s, then talk 8s.")
        self.test_btn.setEnabled(False)
        try:
            self.client.request({"cmd": "record_start"})
        except OSError:
            self.status.setText("Background engine is not running.")
            self.test_btn.setEnabled(True)
            return
        QTimer.singleShot(12000, self._finish_test)

    def _finish_test(self) -> None:
        try:
            reply = self.client.request({"cmd": "record_stop"}, timeout=5.0)
            notes = reply.get("notes") or []
            self.status.setText(str(reply.get("verdict", "done")) + "  ·  " + " ".join(notes))
        except OSError:
            self.status.setText("Background engine is not running.")
        self.test_btn.setEnabled(True)

    def _load(self) -> None:
        data = load_settings()
        self._building = True
        hz = int(data.get("hpf_hz", 75))
        if hz in self.hpf_btns:
            self.hpf_btns[hz].setChecked(True)
        self.pad_btn.setChecked(bool(data.get("pad")))
        self.hf_btn.setChecked(bool(data.get("hf_boost")))
        self.suppress_btn.setChecked(bool(data.get("suppress", True)))
        self.gate_btn.setChecked(bool(data.get("gate", True)))
        self.gate_s.setValue(int(data.get("gate_threshold_db", -42)))
        self.comp_btn.setChecked(bool(data.get("comp", True)))
        self.comp_s.setValue(int(float(data.get("comp_amount", 0.55)) * 100))
        self.bottom_btn.setChecked(bool(data.get("bottom")))
        self.bottom_s.setValue(int(float(data.get("bottom_amount", 0.4)) * 100))
        self.excite_btn.setChecked(bool(data.get("excite")))
        self.excite_s.setValue(int(float(data.get("excite_amount", 0.3)) * 100))
        self.fader.setValue(int(data.get("fader_db", 0)))
        self.lock_btn.setChecked(bool(data.get("lock_usb", True)))
        self._building = False
        self._push()

    def closeEvent(self, event) -> None:  # noqa: N802
        # Leave the background engine and NTG_Console device running.
        # Do not change the default source or sink.
        event.accept()


def _app_icon() -> QIcon:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "icons" / "ntg-console.png",
        here.parents[1] / "icons" / "hicolor" / "256x256" / "apps" / "ntg-console.png",
        Path("/usr/share/icons/hicolor/256x256/apps/ntg-console.png"),
        Path.home() / ".local/share/icons/hicolor/256x256/apps/ntg-console.png",
    ]
    for path in candidates:
        if path.is_file():
            return QIcon(str(path))
    return QIcon.fromTheme("ntg-console")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("NTG Console")
    app.setDesktopFileName("ntg-console")
    icon = _app_icon()
    app.setWindowIcon(icon)
    win = Console()
    win.setWindowIcon(icon)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
