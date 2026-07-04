from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config.settings import DEFAULT_DISK_ALERT_THRESHOLD, DISK_CHECK_INTERVAL
from ...core.ports.notification_service import NotificationService, NotificationUrgency
from ..shared.styles import COLORS, FONT_SIZES, SPACING, btn_primary
from ..shared.toast import show_toast
from ..shared.widgets import Card


class SettingsView(QWidget):
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._config_file = self._data_dir / "app_config.json"
        self._notification_service: Optional[NotificationService] = None
        self._disk_threshold = DEFAULT_DISK_ALERT_THRESHOLD
        self._notifications_enabled = True
        self._sound_enabled = True
        self._config: Dict[str, Any] = {}
        self._load_config()

        self._disk_timer = QTimer(self)
        self._disk_timer.timeout.connect(self._check_disk_space)
        self._disk_timer.start(DISK_CHECK_INTERVAL * 1000)

        self._setup_ui()
        self._check_disk_space()

    def set_notification_service(self, service: NotificationService) -> None:
        self._notification_service = service

    def _load_config(self) -> None:
        if self._config_file.exists():
            try:
                self._config = json.loads(self._config_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._config = {}

    def _save_config(self) -> None:
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            self._config_file.write_text(
                json.dumps(self._config, indent=2, default=str), encoding="utf-8"
            )
        except OSError:
            pass

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["xl"], SPACING["3xl"], SPACING["xl"])
        layout.setSpacing(SPACING["lg"])

        header = QLabel("Configuración")
        header.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['2xl']}; font-weight: 800;"
        )
        layout.addWidget(header)

        disk_header = QLabel("Estado del Disco")
        disk_header.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['lg']}; font-weight: 700; margin-top: 8px;"
        )
        layout.addWidget(disk_header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self._disk_card = Card("Espacio Libre", "Verificando...", COLORS["primary"])
        self._alerts_card = Card("Alertas Activas", "0", COLORS["warning"])
        cards_row.addWidget(self._disk_card)
        cards_row.addWidget(self._alerts_card)
        layout.addLayout(cards_row)

        self._no_alerts_label = QLabel("Sin alertas activas. Su sistema funciona con normalidad.")
        self._no_alerts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_alerts_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['md']}; padding: {SPACING['xl']}px;"
        )
        layout.addWidget(self._no_alerts_label)

        form_header = QLabel("Preferencias")
        form_header.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['lg']}; font-weight: 700; margin-top: 8px;"
        )
        layout.addWidget(form_header)

        form = QFormLayout()
        form.setSpacing(SPACING["md"])
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._startup_cb = QCheckBox("Iniciar minimizado en la bandeja del sistema")
        self._startup_cb.setChecked(self._config.get("start_minimized", False))
        form.addRow("General:", self._startup_cb)

        self._notif_check = QCheckBox("Mostrar notificaciones de escritorio")
        self._notif_check.setChecked(self._config.get("notifications_enabled", True))
        self._notif_check.toggled.connect(self._on_notif_toggled)
        form.addRow("Notificaciones:", self._notif_check)

        self._sound_check = QCheckBox("Reproducir sonido al notificar")
        self._sound_check.setChecked(self._config.get("sound_enabled", True))
        self._sound_check.toggled.connect(self._on_sound_toggled)
        form.addRow("", self._sound_check)

        self._disk_spin = QSpinBox()
        self._disk_spin.setRange(100, 100_000)
        self._disk_spin.setValue(
            self._config.get("disk_alert_threshold_mb", DEFAULT_DISK_ALERT_THRESHOLD // (1024**2))
        )
        self._disk_spin.setSuffix(" MB")
        self._disk_spin.valueChanged.connect(self._on_threshold_changed)
        form.addRow("Umbral de alerta de disco:", self._disk_spin)

        layout.addLayout(form)

        self._save_btn = QPushButton("Guardar Configuración")
        self._save_btn.setStyleSheet(btn_primary())
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

        self._data_label = QLabel(f"Directorio de datos: {self._data_dir}")
        self._data_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['xs']};"
        )
        layout.addWidget(self._data_label)

    def _on_threshold_changed(self, value: int) -> None:
        self._disk_threshold = value * (1024**2)

    def _on_notif_toggled(self, enabled: bool) -> None:
        self._notifications_enabled = enabled
        if self._notification_service is not None:
            self._notification_service.configure(enabled, self._sound_enabled)

    def _on_sound_toggled(self, enabled: bool) -> None:
        self._sound_enabled = enabled
        if self._notification_service is not None:
            self._notification_service.configure(self._notifications_enabled, enabled)

    def _check_disk_space(self) -> None:
        try:
            _total, _used, free = shutil.disk_usage(Path.home())
            free_gb = free / (1024**3)
            self._disk_card.update_value(f"{free_gb:.1f} GB")

            if free < self._disk_threshold:
                self._alerts_card.update_value("1")
                self._no_alerts_label.setText("⚠ Espacio de disco bajo")
                self._no_alerts_label.setStyleSheet(
                    f"color: {COLORS['warning']}; font-size: {FONT_SIZES['md']}; padding: {SPACING['xl']}px;"
                )
                self._disk_card.setStyleSheet("""
                    QFrame#card {
                        background-color: #1e1e2e;
                        border: 1px solid #f38ba8;
                        border-radius: 12px;
                        border-bottom: 3px solid #f38ba8;
                    }
                """)
                if self._notification_service is not None:
                    drive = getattr(Path.home(), "drive", "system")
                    self._notification_service.notify(
                        "Low Disk Space",
                        f"Only {free_gb:.1f} GB remaining on {drive} drive.",
                        NotificationUrgency.CRITICAL,
                    )
            else:
                self._alerts_card.update_value("0")
                self._no_alerts_label.setText("Sin alertas activas. Su sistema funciona con normalidad.")
                self._no_alerts_label.setStyleSheet(
                    f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['md']}; padding: {SPACING['xl']}px;"
                )
                self._disk_card.setStyleSheet("""
                    QFrame#card {
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 12px;
                        border-bottom: 3px solid #89b4fa;
                    }
                """)
        except OSError:
            self._disk_card.update_value("Desconocido")

    def _save(self) -> None:
        self._config["start_minimized"] = self._startup_cb.isChecked()
        self._config["notifications_enabled"] = self._notif_check.isChecked()
        self._config["sound_enabled"] = self._sound_check.isChecked()
        self._config["disk_alert_threshold_mb"] = self._disk_spin.value()
        self._save_config()
        show_toast("Configuración guardada", COLORS["success"])
