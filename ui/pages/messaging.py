from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mesh.database import load_messages, save_message
from mesh.models import Message


class ChannelTab(QWidget):
    """A single channel's message view + compose box."""

    send_requested = Signal(str, int)  # (text, channel_index)

    def __init__(self, channel_index: int, channel_name: str, parent=None):
        super().__init__(parent)
        self.channel_index = channel_index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Message list
        self._message_list = QListWidget()
        self._message_list.setStyleSheet("""
            QListWidget {
                background: #1e1e1e;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #333;
            }
        """)
        self._message_list.setWordWrap(True)
        layout.addWidget(self._message_list, 1)

        # Compose area
        compose = QHBoxLayout()
        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("Type a message...")
        self._text_input.setStyleSheet(
            "padding: 8px; background: #2a2a2a; color: #eee; border: 1px solid #555; border-radius: 4px;"
        )
        self._text_input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("Send")
        self._send_btn.setStyleSheet(
            "QPushButton { background: #2196f3; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #1976d2; }"
        )
        self._send_btn.clicked.connect(self._on_send)

        compose.addWidget(self._text_input, 1)
        compose.addWidget(self._send_btn)
        layout.addLayout(compose)

        # Load history
        self._load_history()

    def _load_history(self):
        messages = load_messages(self.channel_index)
        for msg in messages:
            self._append_message(msg, from_db=True)

    def _append_message(self, msg: Message, from_db: bool = False):
        ts = datetime.fromtimestamp(msg.rx_time).strftime("%H:%M:%S")
        sender = msg.from_name or msg.from_id
        if msg.is_outgoing:
            line = f"[{ts}] You: {msg.text}"
        else:
            line = f"[{ts}] {sender}: {msg.text}"

        item = QListWidgetItem(line)
        if msg.is_outgoing:
            item.setForeground(Qt.GlobalColor.cyan)
        else:
            item.setForeground(Qt.GlobalColor.white)
        self._message_list.addItem(item)
        self._message_list.scrollToBottom()

    def add_message(self, msg: Message):
        save_message(msg)
        self._append_message(msg)

    def _on_send(self):
        text = self._text_input.text().strip()
        if not text:
            return
        self._text_input.clear()
        self.send_requested.emit(text, self.channel_index)


class MessagingPage(QWidget):
    send_text = Signal(str, str, int)  # (text, destination, channelIndex)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Messages")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px;")
        layout.addWidget(title)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #2d2d2d; color: #aaa; padding: 8px 16px;
                border: 1px solid #444; border-bottom: none; border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected { background: #1e1e1e; color: #fff; }
        """)
        layout.addWidget(self._tabs, 1)

        self._channel_tabs: Dict[int, ChannelTab] = {}

        # Create default channel 0 tab
        self._ensure_channel_tab(0, "Primary")

    def _ensure_channel_tab(self, index: int, name: str) -> ChannelTab:
        if index in self._channel_tabs:
            return self._channel_tabs[index]
        tab = ChannelTab(index, name)
        tab.send_requested.connect(self._on_channel_send)
        display_name = name if name else f"Channel {index}"
        self._tabs.addTab(tab, display_name)
        self._channel_tabs[index] = tab
        return tab

    def _on_channel_send(self, text: str, channel_index: int):
        self.send_text.emit(text, "^all", channel_index)

    @Slot(list)
    def on_channels_loaded(self, channels: list):
        """Rebuild tabs when channel list arrives from device."""
        # Remove existing tabs
        self._tabs.clear()
        self._channel_tabs.clear()

        for ch in channels:
            role = ch.get("role", "")
            if "DISABLED" in str(role):
                continue
            idx = ch.get("index", 0)
            name = ch.get("name", "")
            if idx == 0 and not name:
                name = "Primary"
            self._ensure_channel_tab(idx, name)

        # Always ensure at least channel 0
        if 0 not in self._channel_tabs:
            self._ensure_channel_tab(0, "Primary")

    @Slot(object)
    def on_text_received(self, msg: Message):
        tab = self._channel_tabs.get(msg.channel_index)
        if not tab:
            tab = self._ensure_channel_tab(msg.channel_index, f"Channel {msg.channel_index}")
        tab.add_message(msg)

    @Slot(object)
    def on_text_sent(self, msg: Message):
        tab = self._channel_tabs.get(msg.channel_index)
        if not tab:
            tab = self._ensure_channel_tab(msg.channel_index, f"Channel {msg.channel_index}")
        tab.add_message(msg)
