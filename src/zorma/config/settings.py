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
LOG_FILE = DATA_DIR / "history.jsonl"
UNDO_FILE = DATA_DIR / "undo_stack.json"
CONFIG_FILE = DATA_DIR / "app_config.json"

WATCHDOG_TIMEOUT = 500  # ms, RF-001
SCAN_TIMEOUT = 30  # seconds for 10k files, RF-002
BATCH_SIZE = 100  # RF-012
BATCH_WINDOW = 5  # seconds
DEFAULT_DISK_ALERT_THRESHOLD = 1_000_000_000  # 1 GB, RF-019
DISK_CHECK_INTERVAL = 300  # 5 minutes
RAM_PASSIVE_LIMIT = 150  # MB, RNF-001
RAM_ACTIVE_LIMIT = 300  # MB, RNF-001
CPU_PASSIVE_LIMIT = 2  # %, RNF-002
UNDO_STACK_LIMIT = 1000
RETRY_INTERVAL = 5  # seconds, RNF-009
RETRY_MAX_ATTEMPTS = 3

LOGO_DIR = Path(__file__).parent.parent / "ui" / "shared"
ICONS_DIR = LOGO_DIR / "icons"
