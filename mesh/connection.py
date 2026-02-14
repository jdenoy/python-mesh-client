from __future__ import annotations

import logging
import time
import traceback
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot

from pubsub import pub

from .models import Message, NodeEntry

log = logging.getLogger(__name__)


class MeshtasticBridge(QObject):
    """Lives on a QThread worker. Bridges meshtastic pypubsub events to Qt signals."""

    # --- Signals (thread-safe, connected to GUI slots) ---

    # Connection
    connected = Signal(dict)  # {"my_node_id": str, "my_node_num": int, "node_name": str, "hw_model": str}
    disconnected = Signal()
    connection_error = Signal(str)  # error message

    # Messages
    text_received = Signal(object)  # Message dataclass
    text_sent = Signal(object)  # Message dataclass

    # Nodes
    nodes_updated = Signal(list)  # List[NodeEntry]
    node_updated = Signal(object)  # single NodeEntry

    # Channels (after connect)
    channels_loaded = Signal(list)  # list of channel dicts

    # Config loaded (after connect or on request)
    config_loaded = Signal(str, object)  # (config_name, protobuf object)

    # --- Requests (emitted by GUI, handled here) ---
    request_connect = Signal(str, int)  # (hostname, port)
    request_disconnect = Signal()
    request_send_text = Signal(str, str, int)  # (text, destination, channelIndex)
    request_refresh_nodes = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._interface = None
        self._my_node_id: str = ""
        self._my_node_num: int = 0

        # Connect request signals to handler slots
        self.request_connect.connect(self.do_connect)
        self.request_disconnect.connect(self.do_disconnect)
        self.request_send_text.connect(self.do_send_text)
        self.request_refresh_nodes.connect(self.do_refresh_nodes)

    @property
    def interface(self):
        return self._interface

    @property
    def is_connected(self) -> bool:
        return self._interface is not None

    # ---- pypubsub callbacks (called on meshtastic's publishingThread) ----

    def _on_connection(self, interface, topic=pub.AUTO_TOPIC):
        try:
            self._interface = interface
            my_info = getattr(interface, "myInfo", None)
            my_node_num = getattr(my_info, "my_node_num", 0) if my_info else 0
            self._my_node_num = my_node_num
            self._my_node_id = f"!{my_node_num:08x}" if my_node_num else ""

            node_name = ""
            hw_model = ""
            nodes = getattr(interface, "nodes", None) or {}
            for n in nodes.values():
                user = n.get("user", {})
                if user.get("id") == self._my_node_id:
                    node_name = user.get("longName", "")
                    hw_model = user.get("hwModel", "")
                    break

            self.connected.emit({
                "my_node_id": self._my_node_id,
                "my_node_num": self._my_node_num,
                "node_name": node_name,
                "hw_model": hw_model,
            })

            # Emit initial node list
            self._emit_all_nodes()

            # Emit channels
            self._emit_channels()
        except Exception:
            log.exception("Error in _on_connection")

    def _on_disconnect(self, interface, topic=pub.AUTO_TOPIC):
        self._interface = None
        self.disconnected.emit()

    def _on_text(self, packet, interface, topic=pub.AUTO_TOPIC):
        try:
            decoded = packet.get("decoded", {})
            from_num = packet.get("from", 0)
            to_num = packet.get("to", 0)
            from_id = packet.get("fromId", f"!{from_num:08x}")
            to_id = packet.get("toId", f"!{to_num:08x}")

            from_name = ""
            nodes = getattr(interface, "nodes", None) or {}
            for n in nodes.values():
                if n.get("user", {}).get("id") == from_id:
                    from_name = n["user"].get("longName", "")
                    break

            msg = Message(
                text=decoded.get("text", ""),
                from_id=from_id,
                to_id=to_id,
                channel_index=packet.get("channel", 0),
                from_name=from_name,
                rx_time=packet.get("rxTime", time.time()),
                rx_snr=packet.get("rxSnr", 0.0),
                packet_id=packet.get("id", 0),
                is_outgoing=(from_id == self._my_node_id),
            )
            self.text_received.emit(msg)
        except Exception:
            log.exception("Error in _on_text")

    def _on_node(self, node, interface, topic=pub.AUTO_TOPIC):
        try:
            entry = NodeEntry.from_node_dict(node)
            self.node_updated.emit(entry)
        except Exception:
            log.exception("Error in _on_node")

    # ---- Internal helpers ----

    def _emit_all_nodes(self):
        if not self._interface:
            return
        nodes = getattr(self._interface, "nodes", None) or {}
        entries = [NodeEntry.from_node_dict(n) for n in nodes.values()]
        self.nodes_updated.emit(entries)

    def _emit_channels(self):
        if not self._interface:
            return
        local_node = getattr(self._interface, "localNode", None)
        if not local_node:
            return
        channels_raw = getattr(local_node, "channels", None)
        if not channels_raw:
            return
        channels = []
        for ch in channels_raw:
            ch_dict = {
                "index": ch.index,
                "role": str(ch.role),  # enum -> string
                "name": ch.settings.name if ch.settings else "",
            }
            channels.append(ch_dict)
        self.channels_loaded.emit(channels)

    def _subscribe(self):
        pub.subscribe(self._on_connection, "meshtastic.connection.established")
        pub.subscribe(self._on_disconnect, "meshtastic.connection.lost")
        pub.subscribe(self._on_text, "meshtastic.receive.text")
        pub.subscribe(self._on_node, "meshtastic.node.updated")

    def _unsubscribe(self):
        pub.unsubscribe(self._on_connection, "meshtastic.connection.established")
        pub.unsubscribe(self._on_disconnect, "meshtastic.connection.lost")
        pub.unsubscribe(self._on_text, "meshtastic.receive.text")
        pub.unsubscribe(self._on_node, "meshtastic.node.updated")

    # ---- Slots (called on worker QThread via signal connections) ----

    @Slot(str, int)
    def do_connect(self, hostname: str, port: int):
        if self._interface:
            try:
                self._interface.close()
            except Exception:
                pass
            self._interface = None

        self._subscribe()
        try:
            from meshtastic.tcp_interface import TCPInterface
            # TCPInterface blocks until config is downloaded
            TCPInterface(hostname=hostname, portNumber=port)
            # _on_connection will be fired via pypubsub when config arrives
        except Exception as e:
            log.exception("Connection failed")
            self._unsubscribe()
            self.connection_error.emit(str(e))

    @Slot()
    def do_disconnect(self):
        if self._interface:
            try:
                self._interface.close()
            except Exception:
                pass
            self._interface = None
        try:
            self._unsubscribe()
        except Exception:
            pass
        self.disconnected.emit()

    @Slot(str, str, int)
    def do_send_text(self, text: str, destination: str, channel_index: int):
        if not self._interface:
            return
        try:
            self._interface.sendText(
                text,
                destinationId=destination or "^all",
                channelIndex=channel_index,
            )
            msg = Message(
                text=text,
                from_id=self._my_node_id,
                to_id=destination or "^all",
                channel_index=channel_index,
                from_name="Me",
                rx_time=time.time(),
                is_outgoing=True,
            )
            self.text_sent.emit(msg)
        except Exception as e:
            log.exception("Send failed")

    @Slot()
    def do_refresh_nodes(self):
        self._emit_all_nodes()

    # ---- Config read/write helpers (Phase 2) ----

    def get_local_config(self, config_name: str):
        """Read a config section from the connected node."""
        if not self._interface:
            return
        local = self._interface.localNode
        if not local:
            return
        cfg = getattr(local, "localConfig", None)
        if cfg and hasattr(cfg, config_name):
            self.config_loaded.emit(config_name, getattr(cfg, config_name))

    def get_module_config(self, config_name: str):
        if not self._interface:
            return
        local = self._interface.localNode
        if not local:
            return
        cfg = getattr(local, "moduleConfig", None)
        if cfg and hasattr(cfg, config_name):
            self.config_loaded.emit(config_name, getattr(cfg, config_name))

    def write_config(self, config_name: str):
        """Write a config section to the device."""
        if not self._interface:
            return
        try:
            self._interface.localNode.writeConfig(config_name)
        except Exception as e:
            log.exception(f"writeConfig({config_name}) failed")

    def write_channel(self, channel_index: int):
        if not self._interface:
            return
        try:
            self._interface.localNode.writeChannel(channel_index)
        except Exception as e:
            log.exception(f"writeChannel({channel_index}) failed")
