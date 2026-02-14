from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mesh.database import load_nodes, upsert_node
from mesh.models import NodeEntry

COLUMNS = [
    ("Name", 180),
    ("ID", 110),
    ("Hardware", 120),
    ("Role", 80),
    ("Battery", 70),
    ("SNR", 60),
    ("Hops", 50),
    ("Ch Util", 70),
    ("Last Heard", 140),
]


class NodesPage(QWidget):
    def __init__(self, bridge=None, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._nodes: Dict[str, NodeEntry] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Nodes")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #eee; padding: 12px;")
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget {
                background: #1e1e1e;
                alternate-background-color: #252525;
                color: #ddd;
                gridline-color: #333;
                border: none;
                font-size: 13px;
            }
            QHeaderView::section {
                background: #2d2d2d;
                color: #aaa;
                padding: 6px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)

        header = self._table.horizontalHeader()
        for i, (_, width) in enumerate(COLUMNS):
            header.resizeSection(i, width)
        header.setStretchLastSection(True)

        layout.addWidget(self._table, 1)

        # Load cached nodes
        for n in load_nodes():
            self._nodes[n.node_id] = n
        self._rebuild_table()

    def _rebuild_table(self):
        nodes = sorted(self._nodes.values(), key=lambda n: n.last_heard or 0, reverse=True)
        self._table.setRowCount(len(nodes))
        for row, node in enumerate(nodes):
            self._set_row(row, node)

    def _set_row(self, row: int, node: NodeEntry):
        def item(text: str, align=Qt.AlignmentFlag.AlignLeft) -> QTableWidgetItem:
            it = QTableWidgetItem(text)
            it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            return it

        name = node.long_name or node.short_name or node.node_id
        self._table.setItem(row, 0, item(name))
        self._table.setItem(row, 1, item(node.node_id))
        self._table.setItem(row, 2, item(node.hw_model))
        self._table.setItem(row, 3, item(node.role))

        bat = ""
        if node.battery_level is not None:
            bat = f"{node.battery_level}%" if node.battery_level <= 100 else "Powered"
        self._table.setItem(row, 4, item(bat, Qt.AlignmentFlag.AlignCenter))

        snr = f"{node.snr:.1f}" if node.snr is not None else ""
        self._table.setItem(row, 5, item(snr, Qt.AlignmentFlag.AlignCenter))

        hops = str(node.hops_away) if node.hops_away is not None else ""
        self._table.setItem(row, 6, item(hops, Qt.AlignmentFlag.AlignCenter))

        ch_util = f"{node.channel_util:.1f}%" if node.channel_util is not None else ""
        self._table.setItem(row, 7, item(ch_util, Qt.AlignmentFlag.AlignCenter))

        last = ""
        if node.last_heard:
            last = datetime.fromtimestamp(node.last_heard).strftime("%Y-%m-%d %H:%M:%S")
        self._table.setItem(row, 8, item(last))

    def on_page_shown(self):
        if self._bridge:
            self._bridge.request_refresh_nodes.emit()

    def on_refresh_tick(self):
        if self._bridge:
            self._bridge.request_refresh_nodes.emit()

    @Slot(list)
    def on_nodes_updated(self, nodes: List[NodeEntry]):
        for n in nodes:
            self._nodes[n.node_id] = n
            upsert_node(n)
        self._rebuild_table()

    @Slot(object)
    def on_node_updated(self, node: NodeEntry):
        self._nodes[node.node_id] = node
        upsert_node(node)
        self._rebuild_table()
