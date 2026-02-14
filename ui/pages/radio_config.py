from __future__ import annotations

import logging

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.config_form import ConfigForm

log = logging.getLogger(__name__)


class RadioConfigPage(QWidget):
    """LoRa radio configuration: modem preset, region, TX power, hop limit, etc."""

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Radio Config (LoRa)")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px;")
        layout.addWidget(title)

        self._form = ConfigForm()
        layout.addWidget(self._form, 1)

        # Buttons
        btn_row = QPushButton("Save to Device")
        btn_row.setStyleSheet(
            "QPushButton { background: #4caf50; color: white; padding: 8px 24px; margin: 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #45a049; }"
        )
        btn_row.clicked.connect(self._on_save)
        layout.addWidget(btn_row)

        self._status = QLabel("")
        self._status.setStyleSheet("padding: 0 12px 12px 12px;")
        layout.addWidget(self._status)

    def on_page_shown(self):
        self.load_config()

    @Slot()
    def load_config(self):
        if not self._bridge.interface:
            return
        local = self._bridge.interface.localNode
        if local and local.localConfig:
            self._form.load(local.localConfig.lora)

    def _on_save(self):
        if not self._bridge.interface:
            self._status.setText("Not connected")
            self._status.setStyleSheet("color: #f44336; padding: 0 12px 12px 12px;")
            return

        local = self._bridge.interface.localNode
        if not local or not local.localConfig:
            return

        reply = QMessageBox.question(
            self,
            "Save Radio Config",
            "Write LoRa config to device? The device may reboot.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        changed = self._form.apply(local.localConfig.lora)
        if changed:
            self._bridge.write_config("lora")
            self._status.setText("LoRa config saved!")
            self._status.setStyleSheet("color: #4caf50; padding: 0 12px 12px 12px;")
        else:
            self._status.setText("No changes detected.")
            self._status.setStyleSheet("color: #888; padding: 0 12px 12px 12px;")
