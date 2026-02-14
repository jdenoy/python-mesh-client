from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


class DeviceControlPage(QWidget):
    """Reboot, shutdown, and factory reset controls."""

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 24)

        title = QLabel("Device Control")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px 0;")
        layout.addWidget(title)

        # Reboot
        reboot_group = QGroupBox("Reboot")
        reboot_group.setStyleSheet("QGroupBox { color: #aaa; font-weight: bold; border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding-top: 16px; }")
        rg_layout = QHBoxLayout(reboot_group)

        rg_layout.addWidget(QLabel("Delay (seconds):"))
        self._reboot_delay = QSpinBox()
        self._reboot_delay.setRange(0, 300)
        self._reboot_delay.setValue(10)
        rg_layout.addWidget(self._reboot_delay)

        reboot_btn = QPushButton("Reboot")
        reboot_btn.setStyleSheet(
            "QPushButton { background: #ff9800; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #f57c00; }"
        )
        reboot_btn.clicked.connect(self._on_reboot)
        rg_layout.addWidget(reboot_btn)
        rg_layout.addStretch()

        layout.addWidget(reboot_group)

        # Shutdown
        shutdown_group = QGroupBox("Shutdown")
        shutdown_group.setStyleSheet("QGroupBox { color: #aaa; font-weight: bold; border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding-top: 16px; }")
        sg_layout = QHBoxLayout(shutdown_group)

        sg_layout.addWidget(QLabel("Delay (seconds):"))
        self._shutdown_delay = QSpinBox()
        self._shutdown_delay.setRange(0, 300)
        self._shutdown_delay.setValue(10)
        sg_layout.addWidget(self._shutdown_delay)

        shutdown_btn = QPushButton("Shutdown")
        shutdown_btn.setStyleSheet(
            "QPushButton { background: #f44336; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #d32f2f; }"
        )
        shutdown_btn.clicked.connect(self._on_shutdown)
        sg_layout.addWidget(shutdown_btn)
        sg_layout.addStretch()

        layout.addWidget(shutdown_group)

        # Factory reset
        reset_group = QGroupBox("Factory Reset")
        reset_group.setStyleSheet("QGroupBox { color: #aaa; font-weight: bold; border: 1px solid #555; border-radius: 4px; margin-top: 8px; padding-top: 16px; }")
        fg_layout = QVBoxLayout(reset_group)

        warn = QLabel("This will erase all device settings and restore factory defaults.")
        warn.setStyleSheet("color: #f44336;")
        warn.setWordWrap(True)
        fg_layout.addWidget(warn)

        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Factory Reset (Config Only)")
        reset_btn.setStyleSheet(
            "QPushButton { background: #d32f2f; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #b71c1c; }"
        )
        reset_btn.clicked.connect(lambda: self._on_factory_reset(full=False))
        btn_row.addWidget(reset_btn)

        full_reset_btn = QPushButton("Full Factory Reset")
        full_reset_btn.setStyleSheet(
            "QPushButton { background: #b71c1c; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #880e0e; }"
        )
        full_reset_btn.clicked.connect(lambda: self._on_factory_reset(full=True))
        btn_row.addWidget(full_reset_btn)
        btn_row.addStretch()

        fg_layout.addLayout(btn_row)
        layout.addWidget(reset_group)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet("padding-top: 12px;")
        layout.addWidget(self._status)

        layout.addStretch()

    def _get_node(self):
        if not self._bridge.interface:
            self._status.setText("Not connected")
            self._status.setStyleSheet("color: #f44336; padding-top: 12px;")
            return None
        return self._bridge.interface.localNode

    def _on_reboot(self):
        node = self._get_node()
        if not node:
            return
        secs = self._reboot_delay.value()
        reply = QMessageBox.question(
            self,
            "Reboot Device",
            f"Reboot device in {secs} seconds?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            node.reboot(secs)
            self._status.setText(f"Reboot command sent ({secs}s delay)")
            self._status.setStyleSheet("color: #4caf50; padding-top: 12px;")
        except Exception as e:
            self._status.setText(f"Error: {e}")
            self._status.setStyleSheet("color: #f44336; padding-top: 12px;")

    def _on_shutdown(self):
        node = self._get_node()
        if not node:
            return
        secs = self._shutdown_delay.value()
        reply = QMessageBox.question(
            self,
            "Shutdown Device",
            f"Shutdown device in {secs} seconds?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            node.shutdown(secs)
            self._status.setText(f"Shutdown command sent ({secs}s delay)")
            self._status.setStyleSheet("color: #4caf50; padding-top: 12px;")
        except Exception as e:
            self._status.setText(f"Error: {e}")
            self._status.setStyleSheet("color: #f44336; padding-top: 12px;")

    def _on_factory_reset(self, full: bool):
        node = self._get_node()
        if not node:
            return
        kind = "FULL factory reset" if full else "config-only factory reset"
        reply = QMessageBox.warning(
            self,
            "Factory Reset",
            f"Are you sure you want to perform a {kind}?\n\n"
            "This cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            node.factoryReset(full=full)
            self._status.setText(f"Factory reset command sent (full={full})")
            self._status.setStyleSheet("color: #ff9800; padding-top: 12px;")
        except Exception as e:
            self._status.setText(f"Error: {e}")
            self._status.setStyleSheet("color: #f44336; padding-top: 12px;")
