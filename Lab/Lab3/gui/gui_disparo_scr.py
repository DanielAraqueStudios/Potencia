"""Interfaz PyQt6 para el control de disparo del SCR (Lab 3, ESP32-S3).

Requisitos: pip install PyQt6 pyserial
Uso: python gui_disparo_scr.py   (el sketch debe estar cargado en el ESP32-S3, 115200 baud)
"""
import math
import re
import sys
from datetime import datetime

import logging
import platform
import threading

from PyQt6.QtCore import PYQT_VERSION_STR, QMetaObject, QPointF, QRectF, Qt, QThread, QTimer, QT_VERSION_STR, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QCompleter, QLineEdit
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit,
                             QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget)

from scr_serial import (BAUD, LOG_PATH, LogBridge, SerialWorker, Watchdog, log as flog, setup_logging)

VM = 120 * math.sqrt(2)
HALF_PERIOD_NOM_US = 8333
PRESETS = [0, 30, 45, 60, 90, 135, 160, 180]

RE_STATUS = re.compile(r"f=([\d.]+) Hz\s+ancho ZC=(\d+) us\s+alfa=(\d+)\s+retardo=(\d+) us\s+disparo=(ON|OFF)")
RE_ACK = re.compile(r"alfa = (\d+) grados -> retardo = (\d+) us")

GREEN, RED, BLUE, AMBER, MUTED = "#3ddc97", "#ff5c6c", "#4da3ff", "#ffb84d", "#8b95ad"

STYLE = """
QWidget { background:#12151c; color:#e6eaf5; font-size:13px; }
QLabel { background:transparent; }
QGroupBox { border:1px solid #262d42; border-radius:10px; margin-top:14px; padding:14px 12px 10px 12px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#8b95ad; }
QFrame#card { background:#1b2030; border:1px solid #262d42; border-radius:10px; }
QLabel#cardTitle { color:#8b95ad; font-size:11px; }
QLabel#cardValue { font-size:20px; font-weight:700; }
QLabel#angle { font-size:58px; font-weight:800; color:#ffb84d; }
QPushButton { background:#242b40; border:1px solid #2f3852; border-radius:8px; padding:7px 12px; }
QPushButton:hover { background:#2c3550; }
QPushButton:disabled { color:#5b667f; background:#1a1f30; border-color:#232a3d; }
QPushButton#primary { background:#2f7fe0; border:none; font-weight:700; }
QPushButton#primary:hover { background:#3d8df0; }
QPushButton#primary:disabled { background:#1f3556; color:#6f86a8; }
QPushButton#danger { background:#c93a4b; border:none; font-weight:700; }
QPushButton#danger:hover { background:#e04a5c; }
QPushButton#danger:disabled { background:#4a2329; color:#8a6068; }
QComboBox, QSpinBox { background:#1b2030; border:1px solid #2f3852; border-radius:8px; padding:5px 8px; }
QComboBox QAbstractItemView { background:#1b2030; selection-background-color:#2f7fe0; }
QSlider::groove:horizontal { height:6px; background:#2a3147; border-radius:3px; }
QSlider::sub-page:horizontal { background:#4da3ff; border-radius:3px; }
QSlider::handle:horizontal { background:#ffb84d; width:18px; height:18px; margin:-6px 0; border-radius:9px; }
QPlainTextEdit { background:#0e1117; border:1px solid #262d42; border-radius:8px; font-family:Consolas,monospace; font-size:12px; }
QStatusBar { color:#8b95ad; }
"""


def theory(alpha_deg):
    a = math.radians(alpha_deg)
    vdc = VM / (2 * math.pi) * (1 + math.cos(a))
    vrms = math.sqrt(max(0.0, VM ** 2 / (4 * math.pi) * (math.pi - a + math.sin(2 * a) / 2)))
    return vdc, vrms


class Card(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        self.value = QLabel("—")
        self.value.setObjectName("cardValue")
        lay.addWidget(t)
        lay.addWidget(self.value)

    def set(self, text, color=None):
        self.value.setText(text)
        self.value.setStyleSheet(f"color:{color};" if color else "")


class WavePreview(QWidget):
    def __init__(self):
        super().__init__()
        self.alpha = 90
        self.setMinimumHeight(200)

    def set_alpha(self, a):
        self.alpha = a
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1b2030"))
        r = QRectF(self.rect()).adjusted(16, 14, -16, -30)
        x0, x1, ymid, amp = r.left(), r.right(), r.center().y(), r.height() / 2

        def X(th):
            return x0 + th / (2 * math.pi) * (x1 - x0)

        def Y(v):
            return ymid - v * amp

        p.setPen(QPen(QColor("#2a3147"), 1))
        for k in range(5):
            xx = x0 + k * (x1 - x0) / 4
            p.drawLine(QPointF(xx, r.top()), QPointF(xx, r.bottom()))
        for v in (-1, 0, 1):
            p.drawLine(QPointF(x0, Y(v)), QPointF(x1, Y(v)))

        src = QPainterPath(QPointF(X(0), Y(0)))
        for i in range(1, 241):
            th = 2 * math.pi * i / 240
            src.lineTo(X(th), Y(math.sin(th)))
        p.setPen(QPen(QColor("#5b667f"), 1.5, Qt.PenStyle.DashLine))
        p.drawPath(src)

        a = math.radians(self.alpha)
        if self.alpha < 180:
            line = QPainterPath(QPointF(X(a), Y(0)))
            line.lineTo(X(a), Y(math.sin(a)))
            for i in range(1, 121):
                th = a + (math.pi - a) * i / 120
                line.lineTo(X(th), Y(math.sin(th)))
            fill = QPainterPath(line)
            fill.lineTo(X(a), Y(0))
            p.fillPath(fill, QColor(77, 163, 255, 80))
            p.setPen(QPen(QColor(BLUE), 2.5))
            p.drawPath(line)

        p.setPen(QPen(QColor(AMBER), 1.5, Qt.PenStyle.DotLine))
        p.drawLine(QPointF(X(a), r.top()), QPointF(X(a), r.bottom()))
        f = QFont()
        f.setPointSize(9)
        p.setFont(f)
        p.setPen(QColor(MUTED))
        for k, lab in enumerate(["0", "π/2", "π", "3π/2", "2π"]):
            p.drawText(QPointF(x0 + k * (x1 - x0) / 4 - 8, r.bottom() + 20), lab)
        p.setPen(QColor(AMBER))
        p.drawText(QPointF(min(X(a) + 6, x1 - 60), r.top() + 14), f"α = {self.alpha}°")
        p.end()


class CmdLine(QLineEdit):
    def __init__(self):
        super().__init__()
        self.hist, self.pos = [], 0

    def push(self, t):
        if t and (not self.hist or self.hist[-1] != t):
            self.hist.append(t)
        self.pos = len(self.hist)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self.hist:
            self.pos = max(0, min(len(self.hist), self.pos + (-1 if e.key() == Qt.Key.Key_Up else 1)))
            self.setText(self.hist[self.pos] if self.pos < len(self.hist) else "")
            return
        super().keyPressEvent(e)


class Main(QMainWindow):
    req_scan = pyqtSignal()
    req_open = pyqtSignal(str, bool)
    req_close = pyqtSignal()
    req_send = pyqtSignal(str)

    def __init__(self, bridge):
        super().__init__()
        self.setWindowTitle("Lab 3 — Control de disparo del SCR (ESP32-S3)")
        self.resize(1120, 760)
        self.connected = False
        self.connecting = False
        self.half_us = HALF_PERIOD_NOM_US
        self.alpha = 90
        self._build()
        bridge.message.connect(self.on_log_record)

        self.thread = QThread(self)
        self.thread.setObjectName("serial")
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)
        self.req_scan.connect(self.worker.scan_ports)
        self.req_open.connect(self.worker.open_port)
        self.req_close.connect(self.worker.close_port)
        self.req_send.connect(self.worker.send)
        self.worker.ports.connect(self.on_ports)
        self.worker.opened.connect(self.on_opened)
        self.worker.closed.connect(self.on_closed)
        self.worker.failed.connect(self.on_failed)
        self.worker.line.connect(self.handle_line)
        self.worker.sent.connect(lambda t: (self.log(t, "tx"), self.statusBar().showMessage(f"Enviado: {t}", 3000)))
        self.thread.start()

        self.set_connected(False)
        self.update_alpha_views()
        self.log(f"Log de diagnóstico: {LOG_PATH}", "info")
        self.refresh_ports()

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(16, 16, 16, 12)
        h.setSpacing(16)

        left_w = QWidget()
        left_w.setFixedWidth(390)
        left = QVBoxLayout(left_w)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(12)
        h.addWidget(left_w, 0)

        g = QGroupBox("Conexión")
        gl = QGridLayout(g)
        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.setObjectName("primary")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.link = QLabel()
        self.safe_chk = QCheckBox("Modo USB nativo S3 (DTR alto, RTS bajo)")
        self.safe_chk.setChecked(True)
        gl.addWidget(self.safe_chk, 3, 0, 1, 2)
        gl.addWidget(self.port_combo, 0, 0)
        gl.addWidget(self.refresh_btn, 0, 1)
        gl.addWidget(self.connect_btn, 1, 0, 1, 2)
        gl.addWidget(self.link, 2, 0, 1, 2)
        left.addWidget(g)

        self.ctrl = QGroupBox("Ángulo de disparo (α)")
        cl = QVBoxLayout(self.ctrl)
        self.angle_lbl = QLabel("90°")
        self.angle_lbl.setObjectName("angle")
        self.angle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.angle_lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 180)
        self.slider.setValue(90)
        self.slider.valueChanged.connect(self.on_slider)
        self.slider.sliderReleased.connect(self.on_slider_released)
        cl.addWidget(self.slider)

        row = QHBoxLayout()
        row.addWidget(QLabel("Valor exacto:"))
        self.spin = QSpinBox()
        self.spin.setRange(0, 180)
        self.spin.setValue(90)
        self.spin.setSuffix(" °")
        self.spin.valueChanged.connect(self.on_spin)
        self.spin.editingFinished.connect(self.apply)
        row.addWidget(self.spin, 1)
        cl.addLayout(row)

        pg = QGridLayout()
        for i, v in enumerate(PRESETS):
            b = QPushButton(f"{v}°")
            b.clicked.connect(lambda _, x=v: self.preset(x))
            pg.addWidget(b, i // 4, i % 4)
        cl.addLayout(pg)

        self.auto = QCheckBox("Enviar automáticamente al soltar el slider")
        self.auto.setChecked(True)
        cl.addWidget(self.auto)

        self.apply_btn = QPushButton("Aplicar α")
        self.apply_btn.setObjectName("primary")
        self.apply_btn.clicked.connect(self.apply)
        self.off_btn = QPushButton("APAGAR DISPARO")
        self.off_btn.setObjectName("danger")
        self.off_btn.clicked.connect(lambda: self.send("off"))
        cl.addWidget(self.apply_btn)
        cl.addWidget(self.off_btn)
        left.addWidget(self.ctrl)
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(12)
        h.addLayout(right, 1)

        wg = QGroupBox("Vista teórica de la tensión en la carga (media onda, carga resistiva)")
        wl = QVBoxLayout(wg)
        self.wave = WavePreview()
        wl.addWidget(self.wave)
        right.addWidget(wg)

        tg = QGroupBox("Telemetría del ESP32-S3")
        grid = QGridLayout(tg)
        self.c_freq, self.c_width, self.c_zc = Card("Frecuencia de red"), Card("Ancho del pulso ZC"), Card("Señal de cruce por cero")
        self.c_fire, self.c_alpha, self.c_delay = Card("Disparo"), Card("α en el ESP32"), Card("Retardo en el ESP32")
        self.c_vdc, self.c_vrms, self.c_calc = Card("Vdc teórico (carga R)"), Card("Vrms teórico (carga R)"), Card("Retardo calculado")
        cards = [self.c_freq, self.c_width, self.c_zc, self.c_fire, self.c_alpha, self.c_delay,
                 self.c_vdc, self.c_vrms, self.c_calc]
        for i, c in enumerate(cards):
            grid.addWidget(c, i // 3, i % 3)
        right.addWidget(tg)

        lg = QGroupBox("Registro serie")
        ll = QVBoxLayout(lg)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        clear = QPushButton("Limpiar")
        clear.clicked.connect(self.log_view.clear)
        ll.addWidget(self.log_view)
        cmd_row = QHBoxLayout()
        self.cmd = CmdLine()
        self.cmd.setPlaceholderText("Comando UART: 0-180 (grados) u off — Enter para enviar, ↑↓ historial")
        self.cmd.setCompleter(QCompleter(["off"] + [str(v) for v in PRESETS]))
        self.cmd.returnPressed.connect(self.send_cmd)
        self.cmd_btn = QPushButton("Enviar")
        self.cmd_btn.clicked.connect(self.send_cmd)
        cmd_row.addWidget(self.cmd, 1)
        cmd_row.addWidget(self.cmd_btn)
        cmd_row.addWidget(clear)
        ll.addLayout(cmd_row)
        right.addWidget(lg, 1)

    def log(self, text, kind="info"):
        color = {"tx": BLUE, "rx": "#c3cbe0", "err": RED, "info": MUTED}[kind]
        arrow = {"tx": "▶", "rx": "◀", "err": "✖", "info": "•"}[kind]
        ts = datetime.now().strftime("%H:%M:%S")
        safe = text.replace("&", "&amp;").replace("<", "&lt;")
        self.log_view.appendHtml(f'<span style="color:#5b667f">{ts}</span> <span style="color:{color}">{arrow} {safe}</span>')

    def on_log_record(self, level, msg):
        if level >= logging.WARNING:
            self.log(msg.splitlines()[0], "err")
        elif level == logging.INFO:
            self.log(msg, "info")

    def refresh_ports(self):
        self.port_combo.clear()
        self.port_combo.addItem("Buscando puertos…", None)
        self.refresh_btn.setEnabled(False)
        self.req_scan.emit()

    def on_ports(self, infos):
        self.port_combo.clear()
        for dev, desc, _ in infos:
            self.port_combo.addItem(f"{dev} — {desc}", dev)
        for i, (_, _, vid) in enumerate(infos):
            if vid == 0x303A:
                self.port_combo.setCurrentIndex(i)
                break
        if not infos:
            self.port_combo.addItem("Sin puertos disponibles", None)
        self.refresh_btn.setEnabled(not self.connected)

    def set_connected(self, ok):
        self.connected = ok
        self.connecting = False
        self.ctrl.setEnabled(ok)
        self.cmd.setEnabled(ok)
        self.cmd_btn.setEnabled(ok)
        self.port_combo.setEnabled(not ok)
        self.refresh_btn.setEnabled(not ok)
        self.safe_chk.setEnabled(not ok)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Desconectar" if ok else "Conectar")
        color, txt = (GREEN, "Conectado") if ok else (RED, "Desconectado")
        self.link.setText(f'<span style="color:{color}">●</span> {txt}')
        self.statusBar().showMessage("Listo" if ok else "Seleccione un puerto y conecte")
        if not ok:
            for c in (self.c_freq, self.c_width, self.c_zc, self.c_fire, self.c_alpha, self.c_delay):
                c.set("—")

    def toggle_connection(self):
        if self.connecting:
            return
        if self.connected:
            flog.info("Usuario: desconectar")
            self.req_close.emit()
            return
        name = self.port_combo.currentData()
        if not name:
            self.log("No hay puerto seleccionado.", "err")
            return
        self.connecting = True
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Conectando…")
        flog.info("Usuario: conectar a %s", name)
        self.req_open.emit(name, self.safe_chk.isChecked())

    def on_opened(self, name):
        self.log(f"Conectado a {name} @ {BAUD}", "info")
        self.set_connected(True)

    def on_closed(self, reason):
        self.log(f"Desconectado: {reason}", "info")
        self.set_connected(False)

    def on_failed(self, msg):
        self.log(msg, "err")
        if not self.connected:
            self.set_connected(False)

    def send(self, text):
        if self.connected:
            self.req_send.emit(text)

    def send_cmd(self):
        t = self.cmd.text().strip()
        if not t:
            return
        if not self.connected:
            self.log("Conecte primero al puerto.", "err")
            return
        self.cmd.push(t)
        self.cmd.clear()
        if t.isdigit() and 0 <= int(t) <= 180:
            self.slider.setValue(int(t))
        elif t.lower() != "off":
            self.log(f"'{t}' no es 0-180 ni 'off'; se envía igual (el ESP32 lo rechazará).", "err")
        self.send(t)

    def apply(self):
        if self.connected:
            self.send(str(self.alpha))

    def preset(self, v):
        self.slider.setValue(v)
        self.apply()

    def on_slider(self, v):
        self.alpha = v
        self.spin.blockSignals(True)
        self.spin.setValue(v)
        self.spin.blockSignals(False)
        self.update_alpha_views()

    def on_slider_released(self):
        if self.auto.isChecked():
            self.apply()

    def on_spin(self, v):
        self.slider.setValue(v)

    def update_alpha_views(self):
        self.angle_lbl.setText(f"{self.alpha}°")
        self.wave.set_alpha(self.alpha)
        vdc, vrms = theory(self.alpha)
        self.c_vdc.set(f"{vdc:.1f} V", BLUE)
        self.c_vrms.set(f"{vrms:.1f} V", BLUE)
        self.c_calc.set(f"{self.half_us * self.alpha // 180} µs", AMBER)

    def handle_line(self, text):
        m = RE_STATUS.search(text)
        if m:
            f, w, a, d, fire = m.groups()
            self.half_us = int(1e6 / (2 * float(f)))
            self.c_freq.set(f"{float(f):.2f} Hz", GREEN if 58 <= float(f) <= 62 else AMBER)
            self.c_width.set(f"{w} µs")
            self.c_zc.set("OK", GREEN)
            self.c_alpha.set(f"{a}°")
            self.c_delay.set(f"{d} µs")
            self.c_fire.set(fire, GREEN if fire == "ON" else MUTED)
            self.update_alpha_views()
            return
        if "Sin senal de cruce por cero" in text:
            self.c_zc.set("SIN SEÑAL", RED)
            self.c_freq.set("—")
            return
        m = RE_ACK.search(text)
        if m:
            self.c_alpha.set(f"{m.group(1)}°")
            self.c_delay.set(f"{m.group(2)} µs")
            self.c_fire.set("ON", GREEN)
        elif "Disparo desactivado" in text:
            self.c_fire.set("OFF", MUTED)
        self.log(text, "err" if "invalido" in text.lower() else "rx")

    def closeEvent(self, e):
        flog.info("Cerrando aplicación")
        QMetaObject.invokeMethod(self.worker, "shutdown", Qt.ConnectionType.BlockingQueuedConnection)
        self.thread.quit()
        if not self.thread.wait(3000):
            flog.error("El hilo serie no terminó en 3 s")
        e.accept()


def main():
    bridge = LogBridge()
    setup_logging(bridge)
    flog.info("Python %s | PyQt6 %s | Qt %s | %s", sys.version.split()[0], PYQT_VERSION_STR, QT_VERSION_STR, platform.platform())
    try:
        import serial
        flog.info("pyserial %s", serial.__version__)
    except Exception:
        flog.exception("pyserial no disponible")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    w = Main(bridge)
    wd = Watchdog(threading.get_ident())
    beat = QTimer()
    beat.timeout.connect(wd.tick)
    beat.start(200)
    wd.start()
    w.show()
    flog.info("Ventana mostrada; entrando al bucle de eventos")
    code = app.exec()
    flog.info("Salida limpia (código %s)", code)
    sys.exit(code)


if __name__ == "__main__":
    main()
