from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ConnectionPage(QWidget):
    connect_requested = Signal(str, int)  # hostname, port
    disconnect_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_connected = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Connection")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee;")
        layout.addWidget(title)

        # Hostname
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Hostname:"))
        self._host_edit = QLineEdit("192.168.0.102")
        self._host_edit.setPlaceholderText("IP address or hostname")
        hl.addWidget(self._host_edit)
        layout.addLayout(hl)

        # Port
        pl = QHBoxLayout()
        pl.addWidget(QLabel("Port:"))
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(4403)
        pl.addWidget(self._port_spin)
        pl.addStretch()
        layout.addLayout(pl)

        # Buttons
        bl = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setStyleSheet(
            "QPushButton { background: #4caf50; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #45a049; }"
        )
        self._connect_btn.clicked.connect(self._on_connect_clicked)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setStyleSheet(
            "QPushButton { background: #f44336; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #d32f2f; }"
        )
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)

        bl.addWidget(self._connect_btn)
        bl.addWidget(self._disconnect_btn)
        bl.addStretch()
        layout.addLayout(bl)

        # Status
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _on_connect_clicked(self):
        host = self._host_edit.text().strip()
        port = self._port_spin.value()
        if not host:
            self._status_label.setText("Please enter a hostname.")
            return
        self._status_label.setText(f"Connecting to {host}:{port}...")
        self._connect_btn.setEnabled(False)
        self.connect_requested.emit(host, port)

    def _on_disconnect_clicked(self):
        self.disconnect_requested.emit()

    def on_connected(self, info: dict):
        self._is_connected = True
        self._connect_btn.setEnabled(False)
        self._disconnect_btn.setEnabled(True)
        self._host_edit.setEnabled(False)
        self._port_spin.setEnabled(False)
        name = info.get("node_name", "Unknown")
        self._status_label.setText(f"Connected to {name}")
        self._status_label.setStyleSheet("color: #4caf50;")

    def on_disconnected(self):
        self._is_connected = False
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
        self._host_edit.setEnabled(True)
        self._port_spin.setEnabled(True)
        self._status_label.setText("Disconnected")
        self._status_label.setStyleSheet("color: #f44336;")

    def on_connection_error(self, msg: str):
        self._connect_btn.setEnabled(True)
        self._status_label.setText(f"Error: {msg}")
        self._status_label.setStyleSheet("color: #f44336;")
