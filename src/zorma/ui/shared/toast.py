from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPropertyAnimation, QRect, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from .styles import COLORS


class Toast(QWidget):
    def __init__(self, parent: QWidget, text: str, color: str, duration: int = 3000) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self._label = QLabel(text, self)
        self._label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['bg2']};
                color: {color};
                border: 1px solid {COLORS['border_light']};
                border-left: 3px solid {color};
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
        """)
        self._label.adjustSize()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self.adjustSize()

        pw = parent.width()
        tw = self.width()

        self._start_x = pw - tw - 20
        self._start_y = 20
        self._end_x = self._start_x
        self._end_y = self._start_y

        self.move(self._start_x + 60, self._start_y)
        self._animate_in()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._animate_out)
        self._timer.start(duration)

        self.show()

    def _animate_in(self) -> None:
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(300)
        start = self.geometry()
        end = QRect(self._start_x, self._start_y, start.width(), start.height())
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def _animate_out(self) -> None:
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(200)
        start = self.geometry()
        end = QRect(self._start_x + 80, self._start_y, start.width(), start.height())
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.finished.connect(self.hide)
        self._anim.start()


def show_toast(text: str, color: str = COLORS["success"], duration: int = 3000) -> None:
    parent: Optional[QWidget] = None
    for w in QApplication.topLevelWidgets():
        if w.isVisible():
            parent = w
            break
    if parent is not None:
        Toast(parent, text, color, duration)
