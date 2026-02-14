from __future__ import annotations

import logging

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.config_form import ConfigForm

log = logging.getLogger(__name__)


class DeviceConfigPage(QWidget):
    """Device config: owner name, role, serial settings, plus general device config."""

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Device Config")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        clayout = QVBoxLayout(container)
        clayout.setContentsMargins(12, 0, 12, 12)

        # Owner section
        owner_group = QGroupBox("Owner")
        owner_group.setStyleSheet("QGroupBox { color: #aaa; font-weight: bold; border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding-top: 16px; }")
        owner_layout = QFormLayout(owner_group)

        self._long_name_edit = QLineEdit()
        self._long_name_edit.setPlaceholderText("Long name")
        owner_layout.addRow("Long Name:", self._long_name_edit)

        self._short_name_edit = QLineEdit()
        self._short_name_edit.setPlaceholderText("Short name (4 chars)")
        self._short_name_edit.setMaxLength(4)
        owner_layout.addRow("Short Name:", self._short_name_edit)

        owner_btn = QPushButton("Set Owner")
        owner_btn.setStyleSheet(
            "QPushButton { background: #2196f3; color: white; padding: 6px 16px; border-radius: 4px; }"
            "QPushButton:hover { background: #1976d2; }"
        )
        owner_btn.clicked.connect(self._on_set_owner)
        owner_layout.addRow("", owner_btn)

        self._owner_status = QLabel("")
        owner_layout.addRow("", self._owner_status)

        clayout.addWidget(owner_group)

        # Device config form (auto-generated from protobuf)
        device_group = QGroupBox("Device Settings")
        device_group.setStyleSheet("QGroupBox { color: #aaa; font-weight: bold; border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding-top: 16px; }")
        dg_layout = QVBoxLayout(device_group)

        self._device_form = ConfigForm()
        dg_layout.addWidget(self._device_form)

        save_device_btn = QPushButton("Save Device Config")
        save_device_btn.setStyleSheet(
            "QPushButton { background: #4caf50; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #45a049; }"
        )
        save_device_btn.clicked.connect(self._on_save_device)
        dg_layout.addWidget(save_device_btn)

        self._device_status = QLabel("")
        dg_layout.addWidget(self._device_status)

        clayout.addWidget(device_group)
        clayout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def on_page_shown(self):
        self.load_config()

    @Slot()
    def load_config(self):
        if not self._bridge.interface:
            return
        local = self._bridge.interface.localNode
        if not local:
            return

        # Owner info
        nodes = getattr(self._bridge.interface, "nodes", {}) or {}
        my_id = self._bridge._my_node_id
        for n in nodes.values():
            user = n.get("user", {})
            if user.get("id") == my_id:
                self._long_name_edit.setText(user.get("longName", ""))
                self._short_name_edit.setText(user.get("shortName", ""))
                break

        # Device config
        if local.localConfig:
            self._device_form.load(local.localConfig.device)

    def _on_set_owner(self):
        if not self._bridge.interface:
            self._owner_status.setText("Not connected")
            self._owner_status.setStyleSheet("color: #f44336;")
            return

        long_name = self._long_name_edit.text().strip() or None
        short_name = self._short_name_edit.text().strip() or None

        try:
            self._bridge.interface.localNode.setOwner(
                long_name=long_name,
                short_name=short_name,
            )
            self._owner_status.setText("Owner updated!")
            self._owner_status.setStyleSheet("color: #4caf50;")
        except Exception as e:
            self._owner_status.setText(f"Error: {e}")
            self._owner_status.setStyleSheet("color: #f44336;")

    def _on_save_device(self):
        if not self._bridge.interface:
            self._device_status.setText("Not connected")
            self._device_status.setStyleSheet("color: #f44336;")
            return

        local = self._bridge.interface.localNode
        if not local or not local.localConfig:
            return

        reply = QMessageBox.question(
            self,
            "Save Device Config",
            "Write device config to device?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        changed = self._device_form.apply(local.localConfig.device)
        if changed:
            self._bridge.write_config("device")
            self._device_status.setText("Device config saved!")
            self._device_status.setStyleSheet("color: #4caf50;")
        else:
            self._device_status.setText("No changes detected.")
            self._device_status.setStyleSheet("color: #888;")
