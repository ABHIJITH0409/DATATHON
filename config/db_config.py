# config/db_config.py
# Uses SQLite — no installation, no password, no MySQL needed

import os
import sqlite3
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "healthcare.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_connection():
    conn = sqlite3.connect(os.path.abspath(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
