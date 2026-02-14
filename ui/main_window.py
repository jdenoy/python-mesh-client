from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mesh.connection import MeshtasticBridge
from ui.pages.channels import ChannelsPage
from ui.pages.connection import ConnectionPage
from ui.pages.device_config import DeviceConfigPage
from ui.pages.device_control import DeviceControlPage
from ui.pages.map_page import MapPage
from ui.pages.messaging import MessagingPage
from ui.pages.module_config import ModuleConfigPage
from ui.pages.nodes import NodesPage
from ui.pages.radio_config import RadioConfigPage
from ui.widgets.status_bar import StatusBar


NAV_ITEMS = [
    ("Messages", "messaging"),
    ("Nodes", "nodes"),
    ("Map", "map"),
    ("Channels", "channels"),
    ("Radio", "radio"),
    ("Device", "device"),
    ("Modules", "modules"),
    ("Control", "control"),
]


class MainWindow(QMainWindow):
    def __init__(self, bridge: MeshtasticBridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge

        self.setWindowTitle("Mesh Client")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #1a1a1a; color: #ddd; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QComboBox {
                background: #2a2a2a; color: #eee; border: 1px solid #555;
                border-radius: 4px; padding: 6px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #2a2a2a; color: #eee; selection-background-color: #444;
            }
            QLabel { color: #ccc; }
            QPushButton {
                background: #3a3a3a; color: #ddd; padding: 6px 12px;
                border: 1px solid #555; border-radius: 4px;
            }
            QPushButton:hover { background: #4a4a4a; }
            QPushButton:disabled { background: #2a2a2a; color: #666; }
            QCheckBox { color: #ccc; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid #555; border-radius: 3px; background: #2a2a2a;
            }
            QCheckBox::indicator:checked { background: #2196f3; }
            QGroupBox { color: #aaa; font-weight: bold; border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding-top: 16px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Status bar at top
        self._status_bar = StatusBar()
        root_layout.addWidget(self._status_bar)

        # Main content: sidebar + stacked widget
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        # Sidebar
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(140)
        self._sidebar.setStyleSheet("""
            QListWidget {
                background: #252525;
                border: none;
                border-right: 1px solid #444;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 16px;
                color: #aaa;
            }
            QListWidget::item:selected {
                background: #333;
                color: #fff;
                border-left: 3px solid #2196f3;
            }
            QListWidget::item:hover {
                background: #2d2d2d;
            }
        """)

        # Add nav items
        for label, key in NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._sidebar.addItem(item)

        # Separator-ish spacing before Connect
        spacer_item = QListWidgetItem("")
        spacer_item.setFlags(Qt.ItemFlag.NoItemFlags)
        spacer_item.setSizeHint(spacer_item.sizeHint().__class__(140, 20))
        self._sidebar.addItem(spacer_item)

        connect_item = QListWidgetItem("Connect")
        connect_item.setData(Qt.ItemDataRole.UserRole, "connect")
        self._sidebar.addItem(connect_item)

        self._sidebar.currentItemChanged.connect(self._on_nav_changed)
        content.addWidget(self._sidebar)

        # Stacked widget for pages
        self._stack = QStackedWidget()
        content.addWidget(self._stack, 1)

        root_layout.addLayout(content, 1)

        # Create pages
        self._pages = {}
        self._create_pages()

        # Periodic refresh timer (30s) — active while connected
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(30_000)
        self._refresh_timer.timeout.connect(self._on_refresh_tick)

        # Wire bridge signals to page slots
        self._wire_signals()

        # Select Messages by default
        self._sidebar.setCurrentRow(0)

    def _create_pages(self):
        bridge = self._bridge

        self._messaging_page = MessagingPage()
        self._nodes_page = NodesPage(bridge)
        self._map_page = MapPage(bridge)
        self._connection_page = ConnectionPage()
        self._channels_page = ChannelsPage(bridge)
        self._radio_page = RadioConfigPage(bridge)
        self._device_page = DeviceConfigPage(bridge)
        self._modules_page = ModuleConfigPage(bridge)
        self._control_page = DeviceControlPage(bridge)

        self._pages = {
            "messaging": self._messaging_page,
            "nodes": self._nodes_page,
            "map": self._map_page,
            "channels": self._channels_page,
            "radio": self._radio_page,
            "device": self._device_page,
            "modules": self._modules_page,
            "control": self._control_page,
            "connect": self._connection_page,
        }

        for page in self._pages.values():
            self._stack.addWidget(page)

    def _wire_signals(self):
        bridge = self._bridge

        # Connection page -> bridge
        self._connection_page.connect_requested.connect(bridge.request_connect)
        self._connection_page.disconnect_requested.connect(bridge.request_disconnect)

        # Bridge -> connection page
        bridge.connected.connect(self._connection_page.on_connected)
        bridge.disconnected.connect(self._connection_page.on_disconnected)
        bridge.connection_error.connect(self._connection_page.on_connection_error)

        # Bridge -> status bar
        bridge.connected.connect(self._status_bar.on_connected)
        bridge.disconnected.connect(self._status_bar.on_disconnected)
        bridge.nodes_updated.connect(self._status_bar.on_nodes_updated)

        # Bridge -> messaging
        bridge.text_received.connect(self._messaging_page.on_text_received)
        bridge.text_sent.connect(self._messaging_page.on_text_sent)
        bridge.channels_loaded.connect(self._messaging_page.on_channels_loaded)

        # Messaging -> bridge
        self._messaging_page.send_text.connect(bridge.request_send_text)

        # Bridge -> nodes
        bridge.nodes_updated.connect(self._nodes_page.on_nodes_updated)
        bridge.node_updated.connect(self._nodes_page.on_node_updated)

        # Bridge -> map
        bridge.nodes_updated.connect(self._map_page.on_nodes_updated)
        bridge.node_updated.connect(self._map_page.on_node_updated)

        # Bridge -> channels page
        bridge.channels_loaded.connect(self._channels_page.on_channels_loaded)

        # Load configs when connected
        bridge.connected.connect(self._on_connected_load_configs)

        # Start/stop refresh timer with connection
        bridge.connected.connect(lambda _info: self._refresh_timer.start())
        bridge.disconnected.connect(self._refresh_timer.stop)

    def _on_connected_load_configs(self, info: dict):
        """After connection, load all config pages."""
        self._radio_page.load_config()
        self._device_page.load_config()
        self._modules_page.load_config()

    def _on_nav_changed(self, current: QListWidgetItem, previous):
        if not current:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if key and key in self._pages:
            page = self._pages[key]
            self._stack.setCurrentWidget(page)
            if hasattr(page, "on_page_shown"):
                page.on_page_shown()

    def _on_refresh_tick(self):
        page = self._stack.currentWidget()
        if hasattr(page, "on_refresh_tick"):
            page.on_refresh_tick()
