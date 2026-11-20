import os
from pathlib import Path
from zoneinfo import ZoneInfo

# Storage & Path Guarantees
if Path("/srv/storage").exists():
    _default_base = "/srv/storage/ai-companion"
    _default_tmp = "/srv/storage/tmp"
else:
    _default_base = str(Path.cwd().resolve())
    _default_tmp = "/tmp"

BASE_DIR = Path(os.getenv("BASE_DIR", _default_base)).resolve()
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(BASE_DIR / "models")))
CACHE_DIR = Path(os.getenv("CACHE_DIR", str(BASE_DIR / "cache")))
TMP_DIR = Path(os.getenv("TMPDIR", _default_tmp))

# Ensure storage directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Strict partition isolation
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TMPDIR"] = str(TMP_DIR)

# SQLite Database
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "companion.db")))

# Ollama Runtime Settings (GTX 1650 4GB VRAM envelope)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "aria:3b")
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "4096"))
COMPACTION_THRESHOLD_TOKENS = int(os.getenv("COMPACTION_THRESHOLD_TOKENS", "3072"))
NUM_PREDICT_CHAT = int(os.getenv("NUM_PREDICT_CHAT", "150"))
NUM_PREDICT_COMPACT = int(os.getenv("NUM_PREDICT_COMPACT", "400"))
COMPACTION_DEBOUNCE_SECONDS = int(os.getenv("COMPACTION_DEBOUNCE_SECONDS", "30"))

# Pacing & Timezone Settings
USER_TIMEZONE_STR = os.getenv("USER_TIMEZONE", "Asia/Riyadh")
try:
    USER_TIMEZONE = ZoneInfo(USER_TIMEZONE_STR)
except Exception:
    USER_TIMEZONE = ZoneInfo("UTC")

QUIET_HOURS_START = int(os.getenv("QUIET_HOURS_START", "23")) # 23:00
QUIET_HOURS_END = int(os.getenv("QUIET_HOURS_END", "8"))     # 08:00

# Server Binding
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
