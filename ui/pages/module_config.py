from __future__ import annotations

import logging

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.config_form import ConfigForm

log = logging.getLogger(__name__)

# Module config sections: (attribute_name, display_label, writeConfig_name)
MODULE_SECTIONS = [
    ("mqtt", "MQTT", "mqtt"),
    ("serial", "Serial", "serial"),
    ("external_notification", "Ext Notify", "external_notification"),
    ("store_forward", "Store & Fwd", "store_forward"),
    ("range_test", "Range Test", "range_test"),
    ("telemetry", "Telemetry", "telemetry"),
    ("canned_message", "Canned Msg", "canned_message"),
    ("audio", "Audio", "audio"),
    ("remote_hardware", "Remote HW", "remote_hardware"),
    ("neighbor_info", "Neighbor Info", "neighbor_info"),
    ("ambient_lighting", "Lighting", "ambient_lighting"),
    ("detection_sensor", "Detect Sensor", "detection_sensor"),
    ("paxcounter", "Paxcounter", "paxcounter"),
]


class ModuleTab(QWidget):
    """Single module config tab with auto-generated form + save button."""

    def __init__(self, attr_name: str, config_name: str, bridge, parent=None):
        super().__init__(parent)
        self._attr_name = attr_name
        self._config_name = config_name
        self._bridge = bridge

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._form = ConfigForm()
        layout.addWidget(self._form, 1)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            "QPushButton { background: #4caf50; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #45a049; }"
        )
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._status = QLabel("")
        layout.addWidget(self._status)

    def load(self):
        if not self._bridge.interface:
            return
        local = self._bridge.interface.localNode
        if not local or not local.moduleConfig:
            return
        section = getattr(local.moduleConfig, self._attr_name, None)
        if section is not None:
            self._form.load(section)

    def _on_save(self):
        if not self._bridge.interface:
            self._status.setText("Not connected")
            self._status.setStyleSheet("color: #f44336;")
            return

        local = self._bridge.interface.localNode
        if not local or not local.moduleConfig:
            return

        section = getattr(local.moduleConfig, self._attr_name, None)
        if section is None:
            return

        reply = QMessageBox.question(
            self,
            f"Save {self._config_name}",
            f"Write {self._config_name} config to device?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        changed = self._form.apply(section)
        if changed:
            self._bridge.write_config(self._config_name)
            self._status.setText("Config saved!")
            self._status.setStyleSheet("color: #4caf50;")
        else:
            self._status.setText("No changes detected.")
            self._status.setStyleSheet("color: #888;")


class ModuleConfigPage(QWidget):
    """Tabbed module configuration page."""

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._tabs_map = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Module Config")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px;")
        layout.addWidget(title)

        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #2d2d2d; color: #aaa; padding: 6px 12px;
                border: 1px solid #444; border-bottom: none; border-radius: 4px 4px 0 0;
                font-size: 12px;
            }
            QTabBar::tab:selected { background: #1e1e1e; color: #fff; }
        """)
        self._tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self._tab_widget.setUsesScrollButtons(True)

        for attr_name, display_label, config_name in MODULE_SECTIONS:
            tab = ModuleTab(attr_name, config_name, bridge)
            self._tab_widget.addTab(tab, display_label)
            self._tabs_map[attr_name] = tab

        layout.addWidget(self._tab_widget, 1)

    def on_page_shown(self):
        self.load_config()

    @Slot()
    def load_config(self):
        for tab in self._tabs_map.values():
            tab.load()
