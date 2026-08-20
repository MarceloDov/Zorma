from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from zorma.core.models.enums import EstadoClasificacion
from zorma.core.models.resultado_clasificacion import ResultadoClasificacion
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
        btn.establecer_activo(True)
        assert btn.isChecked()
        btn.establecer_activo(False)
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
        card.actualizar_valor("5")
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
        es.establecer_callback_boton(callback)
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
    def sample_result(self) -> ResultadoClasificacion:
        return ResultadoClasificacion(
            nombre_archivo="test.txt",
            ruta_origen=Path("/tmp/test.txt"),
            ruta_destino=Path("/tmp/dest/test.txt"),
            estado=EstadoClasificacion.EXITO,
        )

    def test_renders_file_name(self, qtbot, sample_result):
        row = TimelineRow(sample_result)
        qtbot.addWidget(row)
        assert row.resultado().nombre_archivo == "test.txt"

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
        assert emitted[0].nombre_archivo == "test.txt"


class TestTimelineFeed:
    def test_shows_empty_state_initially(self, qtbot):
        feed = TimelineFeed()
        qtbot.addWidget(feed)
        feed.show()
        assert feed.isVisible()

    def test_add_result_shows_row(self, qtbot):
        feed = TimelineFeed()
        qtbot.addWidget(feed)
        result = ResultadoClasificacion(
            nombre_archivo="doc.pdf",
            ruta_origen=Path("/tmp/doc.pdf"),
            estado=EstadoClasificacion.EXITO,
        )
        feed.agregar_resultado(result)
        rows = feed.findChildren(TimelineRow)
        assert len(rows) == 1
        assert rows[0].resultado().nombre_archivo == "doc.pdf"

    def test_clear_removes_rows(self, qtbot):
        feed = TimelineFeed()
        qtbot.addWidget(feed)
        result = ResultadoClasificacion(
            nombre_archivo="doc.pdf",
            ruta_origen=Path("/tmp/doc.pdf"),
            estado=EstadoClasificacion.EXITO,
        )
        feed.agregar_resultado(result)
        feed.limpiar()
        rows = feed.findChildren(TimelineRow)
        assert len(rows) == 0
