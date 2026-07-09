from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ...core.models.classification import ClassificationResult, ClassificationStatus
from .styles import BORDER_RADIUS, COLORS, FONT_SIZES, SPACING, btn_secondary


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
        self.setAccessibleName(text)
        self.setObjectName("sidebar_btn")
        if icon_path and icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
            self.setIconSize(QSize(18, 18))

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)



class Card(QFrame):
    def __init__(
        self,
        title: str,
        value: str,
        level: str = "primary",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setProperty("level", level)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"Card: {title}")
        self.setAccessibleDescription(f"Value: {value}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"])
        layout.setSpacing(SPACING["sm"])

        title_label = QLabel(title.upper())
        title_label.setObjectName("card_title")
        layout.addWidget(title_label)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("card_value")
        self._value_label.setProperty("level", level)
        self._value_label.setWordWrap(True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        self.setMinimumWidth(200)
        self.setFixedHeight(110)

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

        self._empty_icon = EmptyState(
            icon="📂",
            title="Sin actividad aún",
            description="Seleccione una carpeta y clasifique archivos para ver la actividad aquí.",
        )
        self._layout.insertWidget(0, self._empty_icon)

    def add_result(self, result: ClassificationResult, can_undo: bool = False) -> None:
        self._empty_icon.hide()

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

        self._empty_icon.show()
        self._layout.insertWidget(0, self._empty_icon)


class EmptyState(QWidget):
    def __init__(
        self,
        icon: str,
        title: str,
        description: str,
        button_text: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._button_signal: Optional[pyqtSignal] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["3xl"], SPACING["3xl"], SPACING["3xl"])
        layout.setSpacing(SPACING["md"])
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 36px; background: transparent;"
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['lg']}; font-weight: 700; background: transparent;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['base']}; background: transparent;"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        if button_text:
            btn = QPushButton(button_text)
            btn.setStyleSheet(btn_secondary())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(btn)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)

            self._button = btn

    def set_button_callback(self, callback: object) -> None:
        if hasattr(self, "_button"):
            self._button.clicked.connect(callback)


class OnboardingWidget(QFrame):
    folder_requested = pyqtSignal()
    rules_requested = pyqtSignal()
    start_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("onboarding")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["3xl"], SPACING["3xl"], SPACING["3xl"])
        layout.setSpacing(SPACING["md"])

        title = QLabel("🎉 ¡Bienvenido a Zorma!")
        title.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['xl']}; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Organiza tus archivos automáticamente en 3 pasos:")
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['md']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        steps = [
            ("① Selecciona una carpeta a monitorear", self.folder_requested),
            ("② Revisa tus reglas de clasificación", self.rules_requested),
            ("③ Inicia la clasificación", self.start_requested),
        ]

        for text, callback in steps:
            btn = QPushButton(text)
            btn.setProperty("class", "onboarding_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(callback)
            layout.addWidget(btn)


