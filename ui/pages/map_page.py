from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from mesh.models import NodeEntry

MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map { margin: 0; padding: 0; width: 100%; height: 100%; background: #1a1a1a; }
  .leaflet-popup-content-wrapper { background: #2a2a2a; color: #ddd; border-radius: 6px; }
  .leaflet-popup-tip { background: #2a2a2a; }
  .leaflet-popup-content { margin: 8px 12px; font-size: 13px; line-height: 1.5; }
  .leaflet-popup-content b { color: #fff; }
  .node-marker {
    background: #2196f3;
    border: 2px solid #fff;
    border-radius: 50%;
    width: 12px;
    height: 12px;
  }
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map('map', { zoomControl: true }).setView([0, 0], 2);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
    maxZoom: 19,
    subdomains: 'abcd'
}).addTo(map);

var markers = [];

function clearMarkers() {
    markers.forEach(function(m) { map.removeLayer(m); });
    markers = [];
}

function addNode(lat, lon, name, nodeId, battery, lastHeard, altitude) {
    var icon = L.divIcon({ className: 'node-marker', iconSize: [12, 12], iconAnchor: [6, 6] });
    var m = L.marker([lat, lon], { icon: icon }).addTo(map);
    var popup = '<b>' + name + '</b><br>ID: ' + nodeId;
    if (battery !== null) popup += '<br>Battery: ' + (battery <= 100 ? battery + '%' : 'Powered');
    if (altitude !== null) popup += '<br>Alt: ' + altitude + 'm';
    if (lastHeard !== null) popup += '<br>Heard: ' + lastHeard;
    m.bindPopup(popup);
    markers.push(m);
}

function fitBounds() {
    if (markers.length === 0) return;
    if (markers.length === 1) {
        map.setView(markers[0].getLatLng(), 14);
    } else {
        var group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.15));
    }
}
</script>
</body>
</html>"""


class MapPage(QWidget):
    def __init__(self, bridge=None, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._nodes: Dict[str, NodeEntry] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._web = QWebEngineView()
        self._web.setHtml(MAP_HTML)
        layout.addWidget(self._web, 1)

        self._map_ready = False
        self._web.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok: bool):
        self._map_ready = ok
        if ok and self._nodes:
            self._refresh_markers()

    def _refresh_markers(self):
        if not self._map_ready:
            return

        js_parts = ["clearMarkers();"]
        for node in self._nodes.values():
            if node.latitude is None or node.longitude is None:
                continue
            if node.latitude == 0.0 and node.longitude == 0.0:
                continue

            name = _js_escape(node.long_name or node.short_name or node.node_id)
            node_id = _js_escape(node.node_id)
            bat = "null" if node.battery_level is None else str(node.battery_level)
            alt = "null" if node.altitude is None else str(node.altitude)
            last = "null"
            if node.last_heard:
                last = _js_escape(
                    datetime.fromtimestamp(node.last_heard).strftime("%Y-%m-%d %H:%M")
                )

            js_parts.append(
                f"addNode({node.latitude},{node.longitude},"
                f"{name},{node_id},{bat},{last},{alt});"
            )

        js_parts.append("fitBounds();")
        self._web.page().runJavaScript("\n".join(js_parts))

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
        self._refresh_markers()

    @Slot(object)
    def on_node_updated(self, node: NodeEntry):
        self._nodes[node.node_id] = node
        self._refresh_markers()


def _js_escape(s: str) -> str:
    """Escape a string for safe embedding in JS as a quoted value."""
    return json.dumps(s)
