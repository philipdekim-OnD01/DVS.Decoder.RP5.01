#!/usr/bin/env python3
"""RAW2 stdin -> ffplay, with a companion settings panel using the live backend."""
import asyncio
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from frame_surface import FrameSurface

import numpy as np
import websockets
from PyQt5 import QtCore, QtGui, QtWidgets as Q

W, H = 960, 720
BITS = {'merged_group': 'Merged Group', 'all_event': 'All Event',
        'on_event_only': 'ON Event Only', 'off_event_only': 'OFF Event Only',
        'flip_row': 'Flip Row', 'mirror_column': 'Mirror Column'}
REGS = [0x392C, 0x0157, 0x0166, 0x0167, 0x0168, 0x3282, *range(0x3300, 0x330D)]


class Backend(QtCore.QThread):
    message = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.commands = queue.Queue()
        self.running = True
    def run(self):
        asyncio.run(self.connect())
    async def connect(self):
        while self.running:
            try:
                async with websockets.connect('ws://127.0.0.1:8765/control', max_size=2**20) as ws:
                    self.message.emit({'type': 'connection', 'connected': True})
                    async def send():
                        while self.running:
                            try: cmd = self.commands.get_nowait()
                            except queue.Empty:
                                await asyncio.sleep(.05)
                                continue
                            await ws.send(json.dumps(cmd))
                    sender = asyncio.create_task(send())
                    try:
                        async for data in ws:
                            if isinstance(data, str): self.message.emit(json.loads(data))
                    finally:
                        sender.cancel()
                        await asyncio.gather(sender, return_exceptions=True)
            except Exception as exc:
                self.message.emit({'type': 'connection', 'connected': False, 'message': str(exc)})
                while not self.commands.empty(): self.commands.get_nowait()
                await asyncio.sleep(1)


class Panel(Q.QWidget):
    def __init__(self, output=True):
        super().__init__()
        self.setWindowTitle('DVS Settings · pipe:0')
        self.connected = self.read_valid = self.pending = False
        self.paused = False
        self.clear_requested = False
        self.running = True
        self.frame = None
        self.roi = (0, W-1, 0, H-1)
        self.options = {}
        self.widgets = {}
        self.colors = {'ON': '#ffffff', 'OFF': '#00bfff', 'BG': '#000000'}
        outer = Q.QVBoxLayout(self)
        self.status = Q.QLabel('Backend connecting…')
        outer.addWidget(self.status)
        self.stats = Q.QLabel('Capture: — | HDMI: —')
        outer.addWidget(self.stats)
        scroll = Q.QScrollArea(); scroll.setWidgetResizable(True)
        body = Q.QWidget(); layout = Q.QVBoxLayout(body); scroll.setWidget(body)
        outer.addWidget(scroll)
        def group(title):
            box = Q.QGroupBox(title); form = Q.QFormLayout(box); layout.addWidget(box); return form
        stream = group('Stream / Time Surface')
        def combo(form, name, values, default=0):
            widget = Q.QComboBox(); widget.addItems(values); widget.setCurrentIndex(default)
            self.widgets[name] = widget; form.addRow(name, widget)
            widget.currentIndexChanged.connect(self.update_options)
        def number(form, name, lo, hi, value):
            widget = Q.QSpinBox(); widget.setRange(lo, hi); widget.setValue(value)
            self.widgets[name] = widget; form.addRow(name, widget)
            widget.valueChanged.connect(self.update_options)
        combo(stream, 'Display mode', ['Raw frame', 'Event Dot', 'Accumulation', 'Time Surface'], 3)
        combo(stream, 'Display FPS', ['30', '60'], 1)
        combo(stream, 'Sub-sampling', ['1', '2', '4', '8'])
        number(stream, 'Event lifetime (ms)', 20, 200, 60)
        number(stream, 'Accumulation (ms)', 10, 200, 35)
        number(stream, 'Time Surface τ (ms)', 10, 500, 25)
        number(stream, 'Point size', 1, 4, 1)
        number(stream, 'Contrast / gain (%)', 25, 300, 125)
        image = group('Image / Event')
        combo(image, 'Polarity', ['ON + OFF', 'ON only', 'OFF only'])
        for name in ['Flip X', 'Flip Y', 'Noise filter', 'Dilation', 'Hot pixel filter']:
            widget = Q.QCheckBox(name); self.widgets[name] = widget
            image.addRow(widget); widget.setChecked(name in ['Noise filter', 'Hot pixel filter']); widget.toggled.connect(self.update_options)
        number(image, 'Hot pixel active frames/s', 1, 60, 20)
        for name in self.colors:
            button = Q.QPushButton(self.colors[name]); image.addRow(name + ' color', button)
            button.clicked.connect(lambda _, n=name, b=button: self.pick_color(n, b))
        roi = group('Display ROI / Crop')
        for name, hi, default in [('X start', W-1, 0), ('X end', W-1, W-1),
                                  ('Y start', H-1, 0), ('Y end', H-1, H-1)]:
            number(roi, name, 0, hi, default)
        apply = Q.QPushButton('Apply Display ROI'); roi.addRow(apply); apply.clicked.connect(self.apply_roi)
        reg = group('Sensor register')
        self.address = Q.QComboBox(); self.address.addItems([f'0x{r:04X}' for r in REGS])
        reg.addRow('Address', self.address)
        self.read_button = Q.QPushButton('Read register'); reg.addRow(self.read_button)
        self.read_button.clicked.connect(self.read_register)
        self.reg_value = Q.QLabel('—'); reg.addRow('Value', self.reg_value)
        self.bit_widgets = {}
        for name, label in BITS.items():
            widget = Q.QCheckBox(label); self.bit_widgets[name] = widget
            reg.addRow(widget); widget.toggled.connect(lambda enabled, n=name: self.write_bit(n, enabled))
        self.reg_message = Q.QLabel('Read 0x392C before changing a bit.'); self.reg_message.setWordWrap(True)
        reg.addRow(self.reg_message)
        self.address.currentIndexChanged.connect(self.address_changed)
        register_box = reg.parentWidget()
        layout.removeWidget(register_box); layout.insertWidget(0, register_box)
        buttons = Q.QHBoxLayout(); outer.addLayout(buttons)
        self.pause_button = Q.QPushButton('Pause'); buttons.addWidget(self.pause_button)
        self.pause_button.clicked.connect(self.pause)
        clear = Q.QPushButton('Clear'); buttons.addWidget(clear)
        clear.clicked.connect(lambda: setattr(self, 'clear_requested', True))
        save = Q.QPushButton('Save PNG'); buttons.addWidget(save); save.clicked.connect(self.save)
        layout.addStretch()
        self.resize(390, 970); self.move(1075, 50)
        self.backend = Backend(); self.backend.message.connect(self.handle_message)
        self.backend.start()
        self.update_options(); self.enable_registers()
        self.player = None
        if output:
            env = dict(os.environ, SDL_VIDEODRIVER='x11', DISPLAY=':0')
            self.player = subprocess.Popen(['ffplay', '-hide_banner', '-loglevel', 'warning',
                '-window_title', 'pipe:0 · DVS', '-left', '40', '-top', '70', '-x', '1000', '-y', '750',
                '-fflags', 'nobuffer', '-flags', 'low_delay', '-sync', 'ext', '-framedrop',
                '-probesize', '32', '-analyzeduration', '0', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                '-video_size', '960x720', '-framerate', '60', '-i', 'pipe:0'],
                stdin=subprocess.PIPE, env=env)
            threading.Thread(target=self.frames, daemon=True).start()
            timer = QtCore.QTimer(self); timer.timeout.connect(self.check_player); timer.start(500)
    def update_options(self, *_):
        result = {}
        for name, widget in self.widgets.items():
            if isinstance(widget, Q.QComboBox): result[name] = widget.currentText()
            elif isinstance(widget, Q.QSpinBox): result[name] = widget.value()
            else: result[name] = widget.isChecked()
        result['colors'] = {k: np.array([int(v[i:i+2], 16) for i in (1, 3, 5)], dtype=np.float32)
                            for k, v in self.colors.items()}
        result['roi'] = self.roi; self.options = result
    def pick_color(self, name, button):
        color = Q.QColorDialog.getColor(QtGui.QColor(self.colors[name]), self)
        if color.isValid():
            self.colors[name] = color.name(); button.setText(color.name()); self.update_options()
    def apply_roi(self):
        roi = tuple(self.widgets[n].value() for n in ['X start', 'X end', 'Y start', 'Y end'])
        if roi[0] > roi[1] or roi[2] > roi[3]:
            Q.QMessageBox.warning(self, 'ROI', 'Start must be less than or equal to end.'); return
        self.roi = roi; self.clear_requested = True; self.update_options()
    def pause(self):
        self.paused = not self.paused; self.pause_button.setText('Resume' if self.paused else 'Pause')
    def address_changed(self):
        self.reg_value.setText('—'); self.reg_message.setText('Read selected register.'); self.enable_registers()
    def enable_registers(self):
        self.read_button.setEnabled(self.connected and not self.pending)
        self.address.setEnabled(not self.pending)
        for widget in self.bit_widgets.values():
            widget.setEnabled(self.connected and self.read_valid and not self.pending and self.address.currentText() == '0x392C')
    def read_register(self):
        self.pending = True; self.enable_registers(); self.reg_message.setText('Reading…')
        self.backend.commands.put({'type': 'reg_read', 'address': self.address.currentText()})
    def write_bit(self, name, enabled):
        if not self.connected or not self.read_valid or self.pending: return
        self.pending = True; self.enable_registers(); self.reg_message.setText('Writing and verifying readback…')
        self.backend.commands.put({'type': 'reg_update_bit', 'address': '0x392C', 'bit': name, 'enabled': enabled})
    def handle_message(self, msg):
        kind = msg.get('type')
        if kind == 'connection':
            self.connected = msg['connected']; self.read_valid = False; self.pending = False
            self.status.setText('Backend connected · 127.0.0.1:8765' if self.connected else 'Backend disconnected · retrying')
            if self.connected: QtCore.QTimer.singleShot(0, self.read_register)
        elif kind == 'stats':
            self.stats.setText(f"Capture: {msg.get('capture_fps', 0):.1f}/s | HDMI: {msg.get('hdmi_fps', 0):.1f} fps\nON: {msg.get('sensor_on_events_sec', 0):,} | OFF: {msg.get('sensor_off_events_sec', 0):,}/s")
        elif kind in ('reg_read', 'reg_write_result'):
            self.pending = False
            value = msg.get('readback', msg.get('value', '—'))
            self.reg_value.setText(f"{msg.get('address')} = {value}")
            if msg.get('address') == '0x392C':
                self.read_valid = True
                for name, widget in self.bit_widgets.items():
                    widget.blockSignals(True); widget.setChecked(bool(msg.get('bits', {}).get(name))); widget.blockSignals(False)
            self.reg_message.setText(f"Readback verified: {value}" if kind == 'reg_write_result' else f"Read: {value}")
        elif kind == 'error':
            self.pending = False; self.read_valid = False; self.reg_message.setText(msg.get('message', 'Register error'))
        self.enable_registers()
    def save(self):
        if self.frame is None: return
        path, _ = Q.QFileDialog.getSaveFileName(self, 'Save DVS PNG', str(Path.home() / 'dvs.png'), 'PNG (*.png)')
        if path:
            frame = self.frame.copy()
            if not QtGui.QImage(frame.data, W, H, W*3, QtGui.QImage.Format_RGB888).save(path):
                Q.QMessageBox.warning(self, 'Save', 'Could not save image.')
    def check_player(self):
        if self.player.poll() is not None: Q.QApplication.quit()
    def closeEvent(self, event):
        # Closing the settings panel keeps capture and ffplay alive.
        self.hide(); event.ignore()
    def frames(self):
        surface = FrameSurface()
        incoming = [None]
        ended = threading.Event()
        def read_latest():
            try:
                while self.running:
                    data = bytearray()
                    while len(data) < W*H:
                        part = sys.stdin.buffer.read(W*H-len(data))
                        if not part: return
                        data.extend(part)
                    incoming[0] = (data, time.monotonic())
            finally:
                ended.set()
        threading.Thread(target=read_latest, daemon=True).start()
        previous = None
        deadline = time.monotonic()
        try:
            while self.running:
                now = time.monotonic(); opt = self.options
                latest = incoming[0]
                if self.clear_requested:
                    surface.clear(); self.clear_requested = False
                if latest is not None and latest is not previous:
                    previous = latest
                    if not self.paused:
                        raw = np.frombuffer(latest[0], np.uint8)
                        surface.accept(raw, latest[1], opt)
                if not self.paused and latest is not None:
                    rgb = surface.render(now, opt); self.frame = rgb
                    self.player.stdin.write(rgb.tobytes()); self.player.stdin.flush()
                if ended.is_set(): break
                deadline += 1/int(opt['Display FPS'])
                time.sleep(max(0, deadline-time.monotonic()))
                if time.monotonic()-deadline > .1: deadline = time.monotonic()
        except (BrokenPipeError, OSError):
            pass
        finally:
            if self.player and self.player.stdin: self.player.stdin.close()


if __name__ == '__main__':
    os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
    os.environ.setdefault('DISPLAY', ':0')
    app = Q.QApplication(sys.argv)
    panel = Panel(output='--test-ui' not in sys.argv); panel.show()
    if '--test-ui' in sys.argv: QtCore.QTimer.singleShot(1000, app.quit)
    exit_code = app.exec_()
    panel.running = False
    if panel.player: panel.player.terminate()
    sys.exit(exit_code)
