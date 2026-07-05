from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QWidget

from zorma.core.models.classification import ClassificationResult, ClassificationStatus
from zorma.core.models.rule import Rule
from zorma.ui.shared.styles import COLORS
from zorma.ui.shared.widgets import Card, EmptyState, OnboardingWidget, SidebarButton, TimelineFeed, TimelineRow


class TestSidebarButton:
    def test_renders_text(self, qtbot):
        btn = SidebarButton("Inicio")
        qtbot.addWidget(btn)
        assert btn.text() == "Inicio"
        assert btn.accessibleName() == "Inicio"

    def test_toggle_active(self, qtbot):
        btn = SidebarButton("Reglas")
        qtbot.addWidget(btn)
        btn.set_active(True)
        assert btn.isChecked()
        btn.set_active(False)
        assert not btn.isChecked()

    def test_accepts_icon_path(self, qtbot):
        btn = SidebarButton("Test", icon_path=Path("/nonexistent/icon.svg"))
        qtbot.addWidget(btn)
        assert btn.text() == "Test"

    def test_click_emits_signal(self, qtbot):
        btn = SidebarButton("Inicio")
        qtbot.addWidget(btn)
        clicked = []
        btn.clicked.connect(lambda: clicked.append(True))
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert clicked == [True]


class TestCard:
    def test_renders_title_and_value(self, qtbot):
        card = Card("Clasificados", "42", COLORS["primary"])
        qtbot.addWidget(card)
        assert card.accessibleName() == "Card: Clasificados"

    def test_update_value(self, qtbot):
        card = Card("Errores", "0", COLORS["error"])
        qtbot.addWidget(card)
        card.update_value("5")
        # After update we can check accessible description
        assert card.accessibleDescription() == "Value: 0"


class TestEmptyState:
    def test_renders_with_button(self, qtbot):
        es = EmptyState(icon="📝", title="Sin datos", description="No hay datos aún", button_text="+ Crear")
        qtbot.addWidget(es)
        es.show()
        assert es.isVisible()

    def test_renders_without_button(self, qtbot):
        es = EmptyState(icon="📂", title="Vacío", description="No hay contenido")
        qtbot.addWidget(es)
        es.show()
        assert es.isVisible()

    def test_button_callback_invoked(self, qtbot):
        es = EmptyState(icon="📝", title="Test", description="Descripción", button_text="Click")
        qtbot.addWidget(es)
        callback = MagicMock()
        es.set_button_callback(callback)
        btn = es.findChild(QPushButton)
        assert btn is not None
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        callback.assert_called_once()


class TestOnboardingWidget:
    def test_renders(self, qtbot):
        ow = OnboardingWidget()
        qtbot.addWidget(ow)
        ow.show()
        assert ow.isVisible()

    def test_folder_requested_signal(self, qtbot):
        ow = OnboardingWidget()
        qtbot.addWidget(ow)
        with qtbot.waitSignal(ow.folder_requested, timeout=500):
            buttons = ow.findChildren(QPushButton)
            qtbot.mouseClick(buttons[0], Qt.MouseButton.LeftButton)

    def test_rules_requested_signal(self, qtbot):
        ow = OnboardingWidget()
        qtbot.addWidget(ow)
        with qtbot.waitSignal(ow.rules_requested, timeout=500):
            buttons = ow.findChildren(QPushButton)
            qtbot.mouseClick(buttons[1], Qt.MouseButton.LeftButton)

    def test_start_requested_signal(self, qtbot):
        ow = OnboardingWidget()
        qtbot.addWidget(ow)
        with qtbot.waitSignal(ow.start_requested, timeout=500):
            buttons = ow.findChildren(QPushButton)
            qtbot.mouseClick(buttons[2], Qt.MouseButton.LeftButton)


class TestTimelineRow:
    @pytest.fixture
    def sample_result(self) -> ClassificationResult:
        return ClassificationResult(
            file_name="test.txt",
            source_path=Path("/tmp/test.txt"),
            destination_path=Path("/tmp/dest/test.txt"),
            rule_applied=Rule(name="Docs"),
            status=ClassificationStatus.SUCCESS,
        )

    def test_renders_file_name(self, qtbot, sample_result):
        row = TimelineRow(sample_result)
        qtbot.addWidget(row)
        assert row.result().file_name == "test.txt"

    def test_no_undo_button_when_not_allowed(self, qtbot, sample_result):
        row = TimelineRow(sample_result, can_undo=False)
        qtbot.addWidget(row)
        # For SUCCESS with can_undo=False, no undo button
        buttons = row.findChildren(QPushButton)
        assert len(buttons) == 0

    def test_undo_button_when_allowed(self, qtbot, sample_result):
        row = TimelineRow(sample_result, can_undo=True)
        qtbot.addWidget(row)
        buttons = row.findChildren(QPushButton)
        assert len(buttons) >= 1

    def test_undo_emits_signal(self, qtbot, sample_result):
        row = TimelineRow(sample_result, can_undo=True)
        qtbot.addWidget(row)
        emitted = []
        row.undo_clicked.connect(lambda r: emitted.append(r))
        btn = row.findChild(QPushButton)
        assert btn is not None
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert len(emitted) == 1
        assert emitted[0].file_name == "test.txt"


class TestTimelineFeed:
    def test_shows_empty_state_initially(self, qtbot):
        feed = TimelineFeed()
        qtbot.addWidget(feed)
        feed.show()
        assert feed.isVisible()

    def test_add_result_shows_row(self, qtbot):
        feed = TimelineFeed()
        qtbot.addWidget(feed)
        result = ClassificationResult(
            file_name="doc.pdf",
            source_path=Path("/tmp/doc.pdf"),
            rule_applied=Rule(name="Docs"),
            status=ClassificationStatus.SUCCESS,
        )
        feed.add_result(result)
        rows = feed.findChildren(TimelineRow)
        assert len(rows) == 1
        assert rows[0].result().file_name == "doc.pdf"

    def test_clear_removes_rows(self, qtbot):
        feed = TimelineFeed()
        qtbot.addWidget(feed)
        result = ClassificationResult(
            file_name="doc.pdf",
            source_path=Path("/tmp/doc.pdf"),
            status=ClassificationStatus.SUCCESS,
        )
        feed.add_result(result)
        feed.clear()
        rows = feed.findChildren(TimelineRow)
        assert len(rows) == 0
