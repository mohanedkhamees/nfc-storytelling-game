"""
Serial communication with the Arduino NFC reader.

Reads newline-terminated UID lines from USB serial (115200 baud) on a
background thread and delivers validated UIDs via callback. Handles port
auto-detection, disconnect detection, and automatic reconnect with backoff.

Usage::

    def handle_uid(uid: str) -> None:
        print(f"Card scanned: {uid}")

    def handle_connection(connected: bool) -> None:
        print("Connected" if connected else "Disconnected")

    reader = SerialReader(
        on_uid=handle_uid,
        on_connection_change=handle_connection,
    )
    reader.start()
    # ... application runs ...
    reader.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import serial
from serial import Serial, SerialException
from serial.tools import list_ports

logger = logging.getLogger(__name__)

# Supported UID sizes: 4, 7, or 10 bytes expressed as hex character counts.
_VALID_UID_HEX_LENGTHS = frozenset({8, 14, 20})

# Substrings matched against port description, manufacturer, hwid, and device path.
_PORT_KEYWORDS = (
    "arduino",
    "ch340",
    "ch341",
    "usb serial",
    "acm",
    "usbserial",
    "wch",
    "cp210",
    "ftdi",
)

# Default delay between reconnect attempts (seconds).
_DEFAULT_RECONNECT_INTERVAL = 3.0

# Serial read timeout so the listener loop can check stop requests promptly.
_READ_TIMEOUT_SECONDS = 0.5


def is_valid_uid(uid: str) -> bool:
    """
    Return True if *uid* is uppercase hexadecimal with a supported byte length.

    Accepts 4-byte (8 chars), 7-byte (14 chars), and 10-byte (20 chars) UIDs.
    """
    if not uid or len(uid) not in _VALID_UID_HEX_LENGTHS:
        return False
    return all("0" <= char <= "9" or "A" <= char <= "F" for char in uid)


def _normalize_uid(line: str) -> Optional[str]:
    """
    Strip whitespace and uppercase a raw serial line.

    Returns the normalized UID string, or None if the line is not valid.
    """
    cleaned = line.strip().upper()
    if is_valid_uid(cleaned):
        return cleaned
    return None


def find_arduino_port() -> Optional[str]:
    """
    Auto-detect a likely Arduino serial port using pyserial heuristics.

    Scans ``list_ports.comports()`` for devices whose description, manufacturer,
    hardware ID, or device path contain common Arduino/USB-serial markers
    (e.g. ``Arduino``, ``CH340``, ``ACM``, ``CP210``).

    Returns:
        Device path (e.g. ``/dev/ttyACM0``, ``COM3``), or None if not found.
    """
    candidates: list[str] = []

    for port_info in list_ports.comports():
        haystack = " ".join(
            part
            for part in (
                port_info.device,
                port_info.description or "",
                port_info.manufacturer or "",
                port_info.hwid or "",
            )
            if part
        ).lower()

        if any(keyword in haystack for keyword in _PORT_KEYWORDS):
            candidates.append(port_info.device)
            logger.debug("Arduino port candidate: %s (%s)", port_info.device, port_info.description)

    if not candidates:
        logger.debug("No Arduino serial port detected")
        return None

    # Prefer the first matching port; explicit ordering is OS-dependent.
    return candidates[0]


class SerialReader:
    """
    Background serial listener for NFC UID messages from Arduino firmware.

    Opens (or auto-detects) a serial port, reads UID lines on a daemon thread,
    debounces duplicate scans, and invokes registered callbacks. Reconnects
    automatically after disconnect or I/O errors.
    """

    def __init__(
        self,
        on_uid: Callable[[str], None],
        port: Optional[str] = None,
        baud_rate: int = 115200,
        on_connection_change: Optional[Callable[[bool], None]] = None,
        debounce_ms: int = 1500,
        reconnect_interval: float = _DEFAULT_RECONNECT_INTERVAL,
    ) -> None:
        """
        Configure the serial reader.

        Args:
            on_uid: Called with each validated UID (may run on background thread).
            port: Explicit serial device path; auto-detected when None.
            baud_rate: Serial baud rate (default 115200 per firmware).
            on_connection_change: Optional callback invoked with connection state.
            debounce_ms: Minimum milliseconds between duplicate UID deliveries.
            reconnect_interval: Seconds to wait between reconnect attempts.
        """
        self._port_override = port
        self._baud_rate = baud_rate
        self._on_uid = on_uid
        self._on_connection_change = on_connection_change
        self._debounce_ms = debounce_ms
        self._reconnect_interval = reconnect_interval

        self._connection: Optional[Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False

        self._last_uid: Optional[str] = None
        self._last_uid_time: float = 0.0

        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the background listener thread (idempotent)."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._listen_loop,
                name="SerialReader",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop listening and close the serial port."""
        with self._lock:
            self._running = False

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=self._reconnect_interval + _READ_TIMEOUT_SECONDS + 1.0)

        self._disconnect()
        self._thread = None

    def is_connected(self) -> bool:
        """Return whether the serial port is currently open and connected."""
        with self._lock:
            return self._connected

    def connect(self) -> bool:
        """
        Open the serial port (explicit port or auto-detected).

        Returns:
            True if the port opened successfully, False otherwise.
        """
        port = self._port_override or find_arduino_port()
        if port is None:
            logger.warning("Serial connect failed: no port available")
            self._set_connected(False)
            return False

        try:
            connection = serial.Serial(
                port=port,
                baudrate=self._baud_rate,
                timeout=_READ_TIMEOUT_SECONDS,
            )
        except (SerialException, OSError) as exc:
            logger.warning("Serial connect failed on %s: %s", port, exc)
            self._set_connected(False)
            return False

        with self._lock:
            self._close_connection_unlocked()
            self._connection = connection

        self._set_connected(True)
        logger.info("Serial connected on %s at %d baud", port, self._baud_rate)
        return True

    def disconnect(self) -> None:
        """Close the serial port and signal disconnected."""
        with self._lock:
            self._close_connection_unlocked()
        self._set_connected(False)

    def _close_connection_unlocked(self) -> None:
        """Close ``_connection``; caller must hold ``_lock``."""
        if self._connection is not None and self._connection.is_open:
            try:
                self._connection.close()
            except (SerialException, OSError) as exc:
                logger.debug("Error closing serial port: %s", exc)
        self._connection = None

    def _set_connected(self, connected: bool) -> None:
        """Update connection flag and notify listener when state changes."""
        with self._lock:
            if self._connected == connected:
                return
            self._connected = connected
            callback = self._on_connection_change

        if callback is not None:
            try:
                callback(connected)
            except Exception:
                logger.exception("on_connection_change callback raised")

    def _listen_loop(self) -> None:
        """Background loop: connect, read UIDs, reconnect on failure."""
        while self._is_running():
            if not self.is_connected():
                if not self.connect():
                    self._sleep_while_running(self._reconnect_interval)
                    continue

            if not self._read_available_line():
                continue

        self.disconnect()

    def _read_available_line(self) -> bool:
        """
        Read and process one line from the open serial port.

        Returns:
            True if the connection remains usable, False if disconnected.
        """
        connection = self._get_connection()
        if connection is None or not connection.is_open:
            return False

        try:
            raw = connection.readline()
        except (SerialException, OSError) as exc:
            logger.warning("Serial read error: %s", exc)
            self.disconnect()
            self._sleep_while_running(self._reconnect_interval)
            return False

        if not raw:
            return True

        try:
            line = raw.decode("ascii", errors="ignore")
        except (UnicodeDecodeError, AttributeError):
            return True

        uid = _normalize_uid(line)
        if uid is None:
            return True

        if self._is_debounced_duplicate(uid):
            return True

        self._record_uid(uid)
        self._deliver_uid(uid)
        return True

    def _deliver_uid(self, uid: str) -> None:
        """Invoke the UID callback, logging but not propagating exceptions."""
        try:
            self._on_uid(uid)
        except Exception:
            logger.exception("on_uid callback raised for UID %s", uid)

    def _is_debounced_duplicate(self, uid: str) -> bool:
        """Return True if *uid* was delivered within the debounce window."""
        now = time.monotonic()
        debounce_seconds = self._debounce_ms / 1000.0

        with self._lock:
            if self._last_uid == uid and (now - self._last_uid_time) < debounce_seconds:
                return True
        return False

    def _record_uid(self, uid: str) -> None:
        """Store the last delivered UID and timestamp for debouncing."""
        with self._lock:
            self._last_uid = uid
            self._last_uid_time = time.monotonic()

    def _get_connection(self) -> Optional[Serial]:
        """Return the active serial connection, if any."""
        with self._lock:
            return self._connection

    def _is_running(self) -> bool:
        """Return whether the listener loop should continue."""
        with self._lock:
            return self._running

    def _sleep_while_running(self, duration: float) -> None:
        """Sleep in small increments so ``stop()`` is responsive."""
        end = time.monotonic() + duration
        while self._is_running() and time.monotonic() < end:
            time.sleep(min(0.2, end - time.monotonic()))
