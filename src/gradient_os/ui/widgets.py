from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QObject


def set_label_text(label: QLabel, text: str):
    if label.text() != text:
        label.setText(text)

def coalesce_text(label: QLabel, new_text: str):
    """Only updates the label when text changes; alias for clarity in hot paths."""
    set_label_text(label, new_text)


