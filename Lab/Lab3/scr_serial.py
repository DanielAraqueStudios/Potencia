"""Hilo serie, registro (log) y vigilante de congelamiento para gui_disparo_scr.py.

Toda la E/S del puerto ocurre en un hilo aparte, con timeouts, para que la interfaz nunca se bloquee.
El registro completo de la ultima ejecucion queda en gui_disparo_scr.log (junto a este archivo).
"""
import faulthandler
import logging
import sys
import threading
import time
import traceback
from pathlib import Path

import serial
from serial.tools import list_ports
from PyQt6.QtCore import QObject, QTimer, QtMsgType, pyqtSignal, pyqtSlot, qInstallMessageHandler

BAUD = 115200
LOG_PATH = Path(__file__).with_name("gui_disparo_scr.log")
SILENT_WARN_S = 3.0
HEARTBEAT_S = 5.0

log = logging.getLogger("scr")
_fault_file = None


class LogBridge(QObject):
    message = pyqtSignal(int, str)


class BridgeHandler(logging.Handler):
    def __init__(self, bridge):
        super().__init__(logging.DEBUG)
        self.bridge = bridge

    def emit(self, record):
        try:
            self.bridge.message.emit(record.levelno, self.format(record))
        except RuntimeError:
            pass


def _qt_msg(mode, _ctx, msg):
    level = {QtMsgType.QtDebugMsg: logging.DEBUG, QtMsgType.QtInfoMsg: logging.INFO,
             QtMsgType.QtWarningMsg: logging.WARNING}.get(mode, logging.ERROR)
    log.log(level, "Qt: %s", msg)


def setup_logging(bridge):
    global _fault_file
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] [%(threadName)s] %(message)s", "%H:%M:%S")
    try:
        fh = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        log.addHandler(fh)
        _fault_file = open(LOG_PATH, "a", buffering=1, encoding="utf-8")
        faulthandler.enable(_fault_file, all_threads=True)
    except OSError as e:
        print(f"No se pudo abrir el log {LOG_PATH}: {e}", file=sys.stderr)
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    bh = BridgeHandler(bridge)
    bh.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(bh)

    sys.excepthook = lambda t, v, tb: log.critical("Excepcion no capturada", exc_info=(t, v, tb))
    threading.excepthook = lambda a: log.critical(
        "Excepcion no capturada en hilo %s", a.thread.name if a.thread else "?",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    qInstallMessageHandler(_qt_msg)


class Watchdog(threading.Thread):
    """Si el hilo de la interfaz deja de latir, registra la pila donde esta atascado."""

    def __init__(self, main_ident, limit=1.5):
        super().__init__(name="watchdog", daemon=True)
        self.main_ident = main_ident
        self.limit = limit
        self.beat = time.monotonic()
        self.stuck = False

    def tick(self):
        self.beat = time.monotonic()

    def run(self):
        while True:
            time.sleep(0.5)
            gap = time.monotonic() - self.beat
            if gap > self.limit and not self.stuck:
                self.stuck = True
                frame = sys._current_frames().get(self.main_ident)
                stack = "".join(traceback.format_stack(frame)) if frame else "(sin pila)"
                log.error("INTERFAZ CONGELADA hace %.1f s. Pila del hilo principal:\n%s", gap, stack)
            elif gap <= self.limit and self.stuck:
                self.stuck = False
                log.warning("Interfaz recuperada")


class SerialWorker(QObject):
    opened = pyqtSignal(str)
    closed = pyqtSignal(str)
    line = pyqtSignal(str)
    sent = pyqtSignal(str)
    failed = pyqtSignal(str)
    ports = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.ser = None
        self.buf = b""
        self.timer = None
        self._reset_stats()

    def _reset_stats(self):
        self.rx_bytes = self.rx_lines = self.tx_count = 0
        self.opened_at = self.last_hb = 0.0
        self.silent_warned = False

    @pyqtSlot()
    def start(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(20)
        log.debug("Hilo serie iniciado")

    @pyqtSlot()
    def scan_ports(self):
        t0 = time.monotonic()
        log.debug("Listando puertos...")
        try:
            infos = list(list_ports.comports())
        except Exception:
            log.exception("Fallo al listar puertos")
            infos = []
        log.info("%d puerto(s) en %.0f ms", len(infos), (time.monotonic() - t0) * 1000)
        for p in infos:
            log.debug("  %s | %s | vid=%s pid=%s | hwid=%s", p.device, p.description, p.vid, p.pid, p.hwid)
        self.ports.emit([(p.device, p.description, p.vid) for p in infos])

    @pyqtSlot(str, bool)
    def open_port(self, name, safe):
        self._drop("Reabriendo", quiet=True)
        t0 = time.monotonic()
        log.info("Abriendo %s @ %d (DTR alto/RTS bajo=%s)", name, BAUD, safe)
        try:
            s = serial.serial_for_url(name, baudrate=BAUD, timeout=0, write_timeout=1, do_not_open=True)
            if safe:
                s.dtr = True   # el USB CDC nativo del S3 solo transmite con DTR en alto
                s.rts = False  # RTS en alto junto a DTR puede reiniciar/entrar a bootloader
            s.open()
        except Exception as e:
            log.exception("No se pudo abrir %s", name)
            self.failed.emit(f"No se pudo abrir {name}: {e}")
            return
        self.ser, self.buf = s, b""
        self._reset_stats()
        self.opened_at = self.last_hb = time.monotonic()
        log.info("%s abierto en %.0f ms (dtr=%s rts=%s)", name, (time.monotonic() - t0) * 1000,
                 getattr(s, "dtr", "?"), getattr(s, "rts", "?"))
        self.opened.emit(name)

    @pyqtSlot()
    def close_port(self):
        self._drop("Desconectado por el usuario")

    @pyqtSlot(str)
    def send(self, text):
        if not self.ser:
            log.warning("send(%r) ignorado: no hay puerto abierto", text)
            return
        t0 = time.monotonic()
        try:
            n = self.ser.write((text + "\n").encode())
        except serial.SerialTimeoutException:
            log.error("Timeout de escritura (1 s) enviando %r: el dispositivo no esta leyendo", text)
            self.failed.emit("Timeout de escritura: el ESP32 no responde")
            return
        except Exception as e:
            log.exception("Error de escritura")
            self._drop(f"Error de escritura: {e}")
            return
        self.tx_count += 1
        log.debug("TX %r (%s bytes, %.1f ms)", text, n, (time.monotonic() - t0) * 1000)
        self.sent.emit(text)

    @pyqtSlot()
    def shutdown(self):
        if self.ser:
            self.send("off")
            self._drop("Cierre de la aplicacion")
        if self.timer:
            self.timer.stop()

    def _drop(self, reason, quiet=False):
        if not self.ser:
            return
        try:
            self.ser.close()
        except Exception:
            log.exception("Error al cerrar el puerto")
        self.ser = None
        log.info("Puerto cerrado: %s (RX %d bytes, %d lineas; TX %d)", reason, self.rx_bytes, self.rx_lines, self.tx_count)
        if not quiet:
            self.closed.emit(reason)

    def _poll(self):
        if not self.ser:
            return
        now = time.monotonic()
        try:
            n = self.ser.in_waiting
            if n:
                data = self.ser.read(n)
                self.rx_bytes += len(data)
                self.buf += data
                log.debug("RX %d bytes: %r", len(data), data[:200])
        except Exception as e:
            log.exception("Error de lectura")
            self._drop(f"Puerto perdido: {e}")
            return
        while b"\n" in self.buf:
            raw, self.buf = self.buf.split(b"\n", 1)
            text = raw.decode(errors="replace").strip()
            if text:
                self.rx_lines += 1
                log.debug("RX linea: %r", text)
                self.line.emit(text)
        if not self.silent_warned and self.rx_bytes == 0 and now - self.opened_at > SILENT_WARN_S:
            self.silent_warned = True
            log.warning("Sin datos del ESP32 tras %.0f s. Revise: sketch cargado, 115200 baud, "
                        "puerto correcto, Monitor Serie de Arduino cerrado, y 'USB CDC On Boot' "
                        "habilitado si usa el puerto USB nativo.", SILENT_WARN_S)
        if now - self.last_hb >= HEARTBEAT_S:
            self.last_hb = now
            log.debug("Latido: abierto %.0f s, RX %d bytes / %d lineas, TX %d",
                      now - self.opened_at, self.rx_bytes, self.rx_lines, self.tx_count)
