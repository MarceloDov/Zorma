from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ...core.models.classification import ClassificationResult, ClassificationStatus
from .styles import BORDER_RADIUS, COLORS, FONT_SIZES, SPACING


class SidebarButton(QPushButton):
    def __init__(
        self,
        text: str,
        icon_path: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(text)
        self.setFixedHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_path and icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
            self.setIconSize(QSize(18, 18))
        self.setStyleSheet(self._style(False))

    def _style(self, active: bool) -> str:
        if active:
            return f"""
                QPushButton {{
                    background-color: {COLORS["primary"]};
                    color: {COLORS["bg"]};
                    border: none;
                    border-radius: {BORDER_RADIUS["md"]};
                    padding-left: 14px;
                    text-align: left;
                    font-size: {FONT_SIZES["md"]};
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {COLORS["primary"]};
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS["text_muted"]};
                border: none;
                border-radius: {BORDER_RADIUS["md"]};
                padding-left: 14px;
                text-align: left;
                font-size: {FONT_SIZES["md"]};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS["card_hover"]};
                color: {COLORS["text"]};
            }}
        """

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setStyleSheet(self._style(active))


class Card(QFrame):
    def __init__(
        self,
        title: str,
        value: str,
        color: str = COLORS["primary"],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"])
        layout.setSpacing(SPACING["sm"])

        title_label = QLabel(title.upper())
        title_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['xs']}; font-weight: 600; letter-spacing: 1.2px;"
        )
        layout.addWidget(title_label)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: {FONT_SIZES['xl']}; font-weight: 800;"
        )
        self._value_label.setWordWrap(True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        self.setMinimumWidth(200)
        self.setFixedHeight(110)

    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            #card {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: {BORDER_RADIUS["lg"]};
                border-bottom: 3px solid {self._color};
            }}
            #card:hover {{
                border-color: {self._color};
                background-color: {COLORS["card_hover"]};
            }}
        """)

    def update_value(self, value: str) -> None:
        self._value_label.setText(value)


class TimelineRow(QWidget):
    undo_clicked = pyqtSignal(object)

    def __init__(self, result: ClassificationResult, can_undo: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result = result
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING["md"], 4, SPACING["md"], 4)
        layout.setSpacing(SPACING["sm"])

        icon_map = {
            ClassificationStatus.SUCCESS: "✓",
            ClassificationStatus.ERROR: "✗",
            ClassificationStatus.SKIPPED: "–",
            ClassificationStatus.CONFLICT: "⚠",
        }
        icon_text = icon_map.get(result.status, "•")
        color_map = {
            ClassificationStatus.SUCCESS: COLORS["success"],
            ClassificationStatus.ERROR: COLORS["error"],
            ClassificationStatus.SKIPPED: COLORS["text_muted"],
            ClassificationStatus.CONFLICT: COLORS["warning"],
        }
        icon_color = color_map.get(result.status, COLORS["text_muted"])

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(f"color: {icon_color}; font-size: 14px; font-weight: 700; min-width: 20px;")
        layout.addWidget(icon_label)

        file_label = QLabel(result.file_name)
        file_label.setStyleSheet(
            f"color: {COLORS['text']}; font-size: {FONT_SIZES['base']}; font-weight: 500;"
        )
        file_label.setWordWrap(False)
        layout.addWidget(file_label, 1)

        if result.rule_applied:
            rule_label = QLabel(f"→ {result.rule_applied.name}")
            rule_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['sm']};"
            )
            layout.addWidget(rule_label)

        action_text = "Movido"
        if result.status == ClassificationStatus.ERROR:
            action_text = "Error"
        elif result.status == ClassificationStatus.SKIPPED:
            action_text = "Omitido"

        action_label = QLabel(action_text)
        action_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['sm']}; min-width: 50px;"
        )
        layout.addWidget(action_label)

        time_label = QLabel(result.timestamp.strftime("%H:%M:%S"))
        time_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['xs']}; min-width: 55px;"
        )
        layout.addWidget(time_label)

        if can_undo and result.status == ClassificationStatus.SUCCESS:
            undo_btn = QPushButton("↩")
            undo_btn.setFixedSize(28, 28)
            undo_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['warning']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 14px;
                    font-size: 14px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['warning']}30;
                    border-color: {COLORS['warning']};
                }}
            """)
            undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            undo_btn.setToolTip("Deshacer movimiento")
            undo_btn.clicked.connect(self._on_undo)
            layout.addWidget(undo_btn)

        self.setStyleSheet(f"""
            TimelineRow {{
                background-color: transparent;
                border-bottom: 1px solid {COLORS['border']};
            }}
            TimelineRow:hover {{
                background-color: {COLORS['card_hover']};
            }}
        """)

    def _on_undo(self) -> None:
        self.undo_clicked.emit(self._result)

    def result(self) -> ClassificationResult:
        return self._result


class TimelineFeed(QScrollArea):
    undo_requested = pyqtSignal(ClassificationResult)
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._max_rows = 100
        self._empty_label: Optional[QLabel] = None

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: {BORDER_RADIUS["md"]};
            }}
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background-color: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addStretch()

        self.setWidget(self._container)

        self._empty_label = QLabel("Sin actividad aún.\nSeleccione una carpeta para iniciar.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['md']}; padding: {SPACING['3xl']}px;"
        )
        self._empty_label.setWordWrap(True)
        self._layout.insertWidget(0, self._empty_label)

    def add_result(self, result: ClassificationResult, can_undo: bool = False) -> None:
        if self._empty_label is not None:
            self._empty_label.setParent(None)
            self._empty_label.deleteLater()
            self._empty_label = None

        row = TimelineRow(result, can_undo)
        row.undo_clicked.connect(self.undo_requested)
        self._layout.insertWidget(self._layout.count() - 1, row)

        while self._layout.count() - 1 > self._max_rows:
            item = self._layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if isinstance(w, QWidget):
                    w.hide()
                    w.deleteLater()

        scroll_bar = self.verticalScrollBar()
        if scroll_bar is not None:
            scroll_bar.setValue(0)

    def clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if isinstance(w, QWidget):
                    w.hide()
                    w.deleteLater()

        self._empty_label = QLabel("Sin actividad aún.\nSeleccione una carpeta para iniciar.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['md']}; padding: {SPACING['3xl']}px;"
        )
        self._empty_label.setWordWrap(True)
        self._layout.insertWidget(0, self._empty_label)
