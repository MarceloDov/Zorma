"""
Configuración general de la aplicación Zorma.
"""

from pathlib import Path

APP_NAME = "Zorma"

DATA_DIR = Path.home() / ".zorma"

DEFAULT_DISK_ALERT_THRESHOLD = 1_000_000_000  # 1 GB
DISK_CHECK_INTERVAL = 300  # 5 minutes
UNDO_STACK_LIMIT = 1000

ICONS_DIR = Path(__file__).parent.parent / "ui" / "shared" / "icons"
