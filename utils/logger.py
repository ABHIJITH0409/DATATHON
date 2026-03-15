import os, logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
load_dotenv()

LOG_DIR   = os.getenv("LOG_DIR", "./logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
os.makedirs(LOG_DIR, exist_ok=True)

def _build(name):
    lg = logging.getLogger(name)
    if lg.handlers:
        return lg
    lg.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    fmt = logging.Formatter("[%(asctime)s] %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(); ch.setFormatter(fmt); lg.addHandler(ch)
    fh = RotatingFileHandler(f"{LOG_DIR}/combined.log", maxBytes=10*1024*1024, backupCount=3)
    fh.setFormatter(fmt); lg.addHandler(fh)
    return lg

logger = _build("healthcare_agents")
