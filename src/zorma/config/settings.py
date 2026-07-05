"""
Configuración general de la aplicación Zorma.
Este módulo contiene las constantes de configuración y rutas de archivos necesarias para la ejecución de la aplicación.
"""
from pathlib import Path

APP_NAME = "Zorma"
APP_VERSION = "0.1.0"
AUTHOR = "Zorma Team"

DATA_DIR = Path.home() / ".zorma"
DEFAULT_OUTPUT_DIR = Path.home() / "Zorma"

WATCHDOG_TIMEOUT = 500  # ms, RF-001
SCAN_TIMEOUT = 30  # seconds for 10k files, RF-002
DEFAULT_DISK_ALERT_THRESHOLD = 1_000_000_000  # 1 GB, RF-019
DISK_CHECK_INTERVAL = 300  # 5 minutes
UNDO_STACK_LIMIT = 1000

LOGO_DIR = Path(__file__).parent.parent / "ui" / "shared"
ICONS_DIR = LOGO_DIR / "icons"
