from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setStyleSheet("""
            #statusBar {
                background: #2d2d2d;
                border-bottom: 1px solid #444;
                padding: 4px 8px;
            }
            QLabel { color: #ccc; font-size: 13px; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._status_label = QLabel("Disconnected")
        self._node_label = QLabel("")
        self._battery_label = QLabel("")
        self._nodes_count_label = QLabel("")

        layout.addWidget(self._status_label)
        layout.addStretch()
        layout.addWidget(self._node_label)
        layout.addWidget(self._sep())
        layout.addWidget(self._battery_label)
        layout.addWidget(self._sep())
        layout.addWidget(self._nodes_count_label)

    def _sep(self) -> QLabel:
        lbl = QLabel("|")
        lbl.setStyleSheet("color: #555; margin: 0 6px;")
        return lbl

    @Slot(dict)
    def on_connected(self, info: dict):
        name = info.get("node_name", "Unknown")
        hw = info.get("hw_model", "")
        self._status_label.setText("Connected")
        self._status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        hw_str = f" ({hw})" if hw else ""
        self._node_label.setText(f"{name}{hw_str}")

    @Slot()
    def on_disconnected(self):
        self._status_label.setText("Disconnected")
        self._status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self._node_label.setText("")
        self._battery_label.setText("")
        self._nodes_count_label.setText("")

    @Slot(list)
    def on_nodes_updated(self, nodes):
        self._nodes_count_label.setText(f"{len(nodes)} nodes")
        # Update battery from our local node
        for n in nodes:
            if n.battery_level is not None and n.battery_level <= 100:
                self._battery_label.setText(f"Battery: {n.battery_level}%")
                break
