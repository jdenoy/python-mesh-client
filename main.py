#!/usr/bin/env python3
"""Meshtastic Mesh Client - PySide6 desktop GUI."""

import logging
import sys

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from mesh.connection import MeshtasticBridge
from mesh.database import init_db
from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main():
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Mesh Client")

    # Worker thread for meshtastic operations
    worker_thread = QThread()
    worker_thread.setObjectName("MeshtasticWorker")

    # Bridge lives on the worker thread
    bridge = MeshtasticBridge()
    bridge.moveToThread(worker_thread)
    worker_thread.start()

    # Main window
    window = MainWindow(bridge)
    window.show()

    ret = app.exec()

    # Cleanup
    if bridge.is_connected:
        bridge.do_disconnect()
    worker_thread.quit()
    worker_thread.wait(5000)

    sys.exit(ret)


if __name__ == "__main__":
    main()
