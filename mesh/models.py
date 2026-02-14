from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    text: str
    from_id: str  # "!12345678"
    to_id: str  # "!12345678" or "^all"
    channel_index: int = 0
    from_name: str = ""
    rx_time: float = 0.0
    rx_snr: float = 0.0
    packet_id: int = 0
    is_outgoing: bool = False

    def __post_init__(self):
        if self.rx_time == 0.0:
            self.rx_time = time.time()


@dataclass
class NodeEntry:
    node_id: str  # "!12345678"
    node_num: int = 0
    long_name: str = ""
    short_name: str = ""
    hw_model: str = ""
    role: str = ""
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    channel_util: Optional[float] = None
    air_util_tx: Optional[float] = None
    uptime_seconds: Optional[int] = None
    snr: Optional[float] = None
    hops_away: Optional[int] = None
    last_heard: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[int] = None

    @classmethod
    def from_node_dict(cls, d: dict) -> NodeEntry:
        user = d.get("user", {})
        pos = d.get("position", {})
        dm = d.get("deviceMetrics", {})
        return cls(
            node_id=user.get("id", f"!{d.get('num', 0):08x}"),
            node_num=d.get("num", 0),
            long_name=user.get("longName", ""),
            short_name=user.get("shortName", ""),
            hw_model=user.get("hwModel", ""),
            role=user.get("role", ""),
            battery_level=dm.get("batteryLevel"),
            voltage=dm.get("voltage"),
            channel_util=dm.get("channelUtilization"),
            air_util_tx=dm.get("airUtilTx"),
            uptime_seconds=dm.get("uptimeSeconds"),
            snr=d.get("snr"),
            hops_away=d.get("hopsAway"),
            last_heard=d.get("lastHeard"),
            latitude=pos.get("latitude"),
            longitude=pos.get("longitude"),
            altitude=pos.get("altitude"),
        )
