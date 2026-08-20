from __future__ import annotations

from PyQt6.QtCore import QPoint, QPropertyAnimation, QRect, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .styles import BORDER_RADIUS, COLORS, FONT_SIZES


class Toast(QWidget):
    _active_toasts: list[Toast] = []

    def __init__(self, parent: QWidget, text: str, color: str, duration: int = 3000) -> None:
        super().__init__(parent)
        self._color = color
        self._parent_widget = parent
        self._dismissing = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        container = QWidget(self)
        container.setObjectName("toast_container")

        row = QHBoxLayout(container)
        row.setContentsMargins(14, 10, 4, 10)
        row.setSpacing(10)

        self._label = QLabel(text)
        self._label.setStyleSheet(
            f"color: {color}; font-size: {FONT_SIZES['base']}; font-weight: 600; background: transparent;"
        )
        row.addWidget(self._label, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: none;
                font-size: 13px;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {color};
            }}
        """)
        close_btn.clicked.connect(self._dismiss)
        row.addWidget(close_btn)

        container.setStyleSheet(f"""
            #toast_container {{
                background-color: {COLORS['bg2']};
                border: 1px solid {COLORS['border_light']};
                border-left: 3px solid {color};
                border-radius: {BORDER_RADIUS['md']};
            }}
        """)
        container.adjustSize()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(container)

        self.adjustSize()

        pw = parent.width()
        tw = self.width()
        gap = 8
        parent_toasts = [t for t in Toast._active_toasts if t._parent_widget == parent]
        offset_y = 20 + sum(t.height() + gap for t in parent_toasts)

        self._start_x = pw - tw - 20
        self._start_y = offset_y

        self.move(self._start_x + 60, self._start_y)
        Toast._active_toasts.append(self)
        self._animate_in()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)
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
        if self._dismissing:
            return
        self._dismissing = True
        self._timer.stop()
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(200)
        start = self.geometry()
        end = QRect(self._start_x + 80, self._start_y, start.width(), start.height())
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.finished.connect(self._cleanup)
        self._anim.start()

    def _dismiss(self) -> None:
        self._animate_out()

    def _cleanup(self) -> None:
        self.hide()
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        Toast._reposition_all(self._parent_widget)

    @staticmethod
    def _reposition_all(parent: QWidget) -> None:
        gap = 8
        y = 20
        for t in Toast._active_toasts:
            if t._parent_widget != parent:
                continue
            target = QPoint(t._start_x, y)
            if t.pos() != target:
                anim = QPropertyAnimation(t, b"pos")
                anim.setDuration(200)
                anim.setStartValue(t.pos())
                anim.setEndValue(target)
                anim.start()
            y += t.height() + gap

    def closeEvent(self, event: object) -> None:
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        super().closeEvent(event)  # type: ignore[arg-type]


def show_toast(text: str, color: str = COLORS["success"], duration: int = 3000) -> None:
    parent: QWidget | None = None
    for w in QApplication.topLevelWidgets():
        if w.isVisible():
            parent = w
            break
    if parent is not None:
        Toast(parent, text, color, duration)
