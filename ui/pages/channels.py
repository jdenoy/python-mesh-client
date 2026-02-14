from __future__ import annotations

import logging

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


class ChannelsPage(QWidget):
    """View and edit 8 channel slots on the connected node."""

    save_channel = Signal(int)  # channel_index to write

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._channels = []  # raw channel protobuf objects

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Channels")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px;")
        layout.addWidget(title)

        content = QHBoxLayout()

        # Channel list on left
        self._channel_list = QListWidget()
        self._channel_list.setFixedWidth(180)
        self._channel_list.setStyleSheet("""
            QListWidget { background: #252525; border: 1px solid #444; font-size: 13px; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background: #333; color: #fff; }
        """)
        self._channel_list.currentRowChanged.connect(self._on_channel_selected)
        content.addWidget(self._channel_list)

        # Channel editor on right
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setStyleSheet("QScrollArea { border: none; }")

        self._editor = QWidget()
        self._editor_layout = QFormLayout(self._editor)
        self._editor_layout.setSpacing(8)
        self._editor_layout.setContentsMargins(16, 16, 16, 16)

        self._role_combo = QComboBox()
        self._role_combo.addItems(["DISABLED", "PRIMARY", "SECONDARY"])
        self._editor_layout.addRow("Role:", self._role_combo)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Channel name")
        self._editor_layout.addRow("Name:", self._name_edit)

        self._psk_edit = QLineEdit()
        self._psk_edit.setPlaceholderText("Pre-shared key (hex)")
        self._psk_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._editor_layout.addRow("PSK:", self._psk_edit)

        self._psk_show = QPushButton("Show PSK")
        self._psk_show.setCheckable(True)
        self._psk_show.toggled.connect(
            lambda checked: self._psk_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        self._editor_layout.addRow("", self._psk_show)

        self._uplink_check = None
        self._downlink_check = None

        # Save button
        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save Channel")
        self._save_btn.setStyleSheet(
            "QPushButton { background: #4caf50; color: white; padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #45a049; }"
        )
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addStretch()
        self._editor_layout.addRow("", btn_layout)

        self._status_label = QLabel("")
        self._editor_layout.addRow("", self._status_label)

        editor_scroll.setWidget(self._editor)
        content.addWidget(editor_scroll, 1)

        layout.addLayout(content, 1)

        self._current_index = -1

    @Slot(list)
    def on_channels_loaded(self, channels_raw):
        """Called with raw channel protobuf objects from bridge."""
        self._channels = channels_raw
        self._channel_list.clear()
        local_node = self._bridge.interface.localNode if self._bridge.interface else None
        real_channels = getattr(local_node, "channels", []) if local_node else []
        self._channels = list(real_channels) if real_channels else []

        for i, ch in enumerate(self._channels):
            role_names = {0: "DISABLED", 1: "PRIMARY", 2: "SECONDARY"}
            role_name = role_names.get(ch.role, str(ch.role))
            name = ch.settings.name if ch.settings else ""
            if i == 0 and not name:
                name = "Primary"
            label = f"[{i}] {name or 'Unnamed'} ({role_name})"
            self._channel_list.addItem(label)

        if self._channels:
            self._channel_list.setCurrentRow(0)

    def _on_channel_selected(self, row: int):
        if row < 0 or row >= len(self._channels):
            return
        self._current_index = row
        ch = self._channels[row]

        role_names = {0: "DISABLED", 1: "PRIMARY", 2: "SECONDARY"}
        role_name = role_names.get(ch.role, "DISABLED")
        idx = self._role_combo.findText(role_name)
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)

        self._name_edit.setText(ch.settings.name if ch.settings else "")
        self._psk_edit.setText(ch.settings.psk.hex() if ch.settings and ch.settings.psk else "")
        self._status_label.setText("")

    def _on_save(self):
        if self._current_index < 0 or self._current_index >= len(self._channels):
            return

        ch = self._channels[self._current_index]

        role_map = {"DISABLED": 0, "PRIMARY": 1, "SECONDARY": 2}
        ch.role = role_map.get(self._role_combo.currentText(), 0)

        if ch.settings:
            ch.settings.name = self._name_edit.text()
            psk_hex = self._psk_edit.text().strip()
            if psk_hex:
                try:
                    ch.settings.psk = bytes.fromhex(psk_hex)
                except ValueError:
                    self._status_label.setText("Invalid PSK hex")
                    self._status_label.setStyleSheet("color: #f44336;")
                    return

        try:
            self._bridge.write_channel(self._current_index)
            self._status_label.setText("Channel saved!")
            self._status_label.setStyleSheet("color: #4caf50;")
        except Exception as e:
            self._status_label.setText(f"Error: {e}")
            self._status_label.setStyleSheet("color: #f44336;")
