"""Auto-generate Qt form fields from protobuf message descriptors."""

from __future__ import annotations

import logging
from typing import Any, Dict

from google.protobuf.descriptor import FieldDescriptor

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

# protobuf field type constants
_BOOL = FieldDescriptor.TYPE_BOOL
_STRING = FieldDescriptor.TYPE_STRING
_FLOAT = FieldDescriptor.TYPE_FLOAT
_DOUBLE = FieldDescriptor.TYPE_DOUBLE
_BYTES = FieldDescriptor.TYPE_BYTES
_ENUM = FieldDescriptor.TYPE_ENUM
_MESSAGE = FieldDescriptor.TYPE_MESSAGE
_INT_TYPES = {
    FieldDescriptor.TYPE_INT32,
    FieldDescriptor.TYPE_INT64,
    FieldDescriptor.TYPE_SINT32,
    FieldDescriptor.TYPE_SINT64,
    FieldDescriptor.TYPE_SFIXED32,
    FieldDescriptor.TYPE_SFIXED64,
}
_UINT_TYPES = {
    FieldDescriptor.TYPE_UINT32,
    FieldDescriptor.TYPE_UINT64,
    FieldDescriptor.TYPE_FIXED32,
    FieldDescriptor.TYPE_FIXED64,
}


def _field_label(name: str) -> str:
    """Convert protobuf field name to a human-readable label."""
    return name.replace("_", " ").title()


class ConfigForm(QWidget):
    """Dynamically generates a form from a protobuf message object.

    Usage:
        form = ConfigForm()
        form.load(node.localConfig.lora)
        # ... user edits ...
        form.apply(node.localConfig.lora)  # writes values back
    """

    values_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields: Dict[str, QWidget] = {}  # field_name -> widget
        self._enum_maps: Dict[str, Dict[str, int]] = {}  # field_name -> {label: value}

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; }")

        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setSpacing(8)
        self._form_layout.setContentsMargins(12, 12, 12, 12)
        self._scroll.setWidget(self._form_container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)

    def load(self, proto_msg):
        """Populate form fields from a protobuf message."""
        # Clear existing
        self._fields.clear()
        self._enum_maps.clear()
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)

        if proto_msg is None:
            return

        descriptor = proto_msg.DESCRIPTOR
        for field in descriptor.fields:
            self._add_field(field, getattr(proto_msg, field.name, None))

    def _add_field(self, field: FieldDescriptor, value: Any):
        name = field.name
        label = _field_label(name)

        # Skip repeated/map fields and nested messages for now
        if field.label == FieldDescriptor.LABEL_REPEATED:
            return
        if field.type == _MESSAGE:
            return
        if field.type == _BYTES:
            # Show as hex string, read-only for safety
            w = QLineEdit()
            if isinstance(value, bytes):
                w.setText(value.hex())
            w.setReadOnly(True)
            w.setStyleSheet("color: #888;")
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)
            return

        if field.type == _BOOL:
            w = QCheckBox()
            w.setChecked(bool(value))
            w.stateChanged.connect(lambda: self.values_changed.emit())
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)

        elif field.type == _ENUM:
            w = QComboBox()
            enum_type = field.enum_type
            enum_map = {}
            current_idx = 0
            for i, v in enumerate(enum_type.values):
                enum_map[v.name] = v.number
                w.addItem(v.name, v.number)
                if v.number == value:
                    current_idx = i
            w.setCurrentIndex(current_idx)
            w.currentIndexChanged.connect(lambda: self.values_changed.emit())
            self._fields[name] = w
            self._enum_maps[name] = enum_map
            self._form_layout.addRow(label + ":", w)

        elif field.type == _STRING:
            w = QLineEdit()
            w.setText(str(value) if value else "")
            w.textChanged.connect(lambda: self.values_changed.emit())
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)

        elif field.type in (_FLOAT, _DOUBLE):
            w = QDoubleSpinBox()
            w.setRange(-1e9, 1e9)
            w.setDecimals(4)
            w.setValue(float(value) if value else 0.0)
            w.valueChanged.connect(lambda: self.values_changed.emit())
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)

        elif field.type in _INT_TYPES:
            w = QSpinBox()
            w.setRange(-2147483648, 2147483647)
            w.setValue(int(value) if value else 0)
            w.valueChanged.connect(lambda: self.values_changed.emit())
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)

        elif field.type in _UINT_TYPES:
            w = QSpinBox()
            w.setRange(0, 2147483647)  # QSpinBox max is int32
            w.setValue(int(value) if value else 0)
            w.valueChanged.connect(lambda: self.values_changed.emit())
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)

        else:
            # Fallback: string representation
            w = QLineEdit(str(value))
            self._fields[name] = w
            self._form_layout.addRow(label + ":", w)

    def apply(self, proto_msg) -> bool:
        """Write form values back to the protobuf message. Returns True if any value changed."""
        changed = False
        descriptor = proto_msg.DESCRIPTOR

        for field in descriptor.fields:
            name = field.name
            widget = self._fields.get(name)
            if widget is None:
                continue

            old_val = getattr(proto_msg, name, None)

            if field.type == _BOOL:
                new_val = widget.isChecked()
            elif field.type == _ENUM:
                new_val = widget.currentData()
            elif field.type == _STRING:
                new_val = widget.text()
            elif field.type in (_FLOAT, _DOUBLE):
                new_val = widget.value()
            elif field.type in (_INT_TYPES | _UINT_TYPES):
                new_val = widget.value()
            else:
                continue

            if new_val != old_val:
                try:
                    setattr(proto_msg, name, new_val)
                    changed = True
                except Exception:
                    log.exception("Failed to set %s", name)

        return changed
