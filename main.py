# main.py — SQLite version, no MySQL needed
import sys, os, threading, time
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from utils.logger import logger

def setup_database():
    """Create all tables in SQLite automatically."""
    from config.db_config import get_connection
    conn = get_connection()
    cur  = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS policies (
        id                              INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_id                       TEXT NOT NULL UNIQUE,
        policy_date                     TEXT NOT NULL,
        agency                          TEXT NOT NULL,
        policy_type                     TEXT NOT NULL,
        affected_hcpcs_code             TEXT NOT NULL,
        hospital_id                     TEXT NOT NULL,
        hospital_state                  TEXT NOT NULL,
        service_volume                  INTEGER NOT NULL DEFAULT 0,
        avg_reimbursement_before_usd    REAL NOT NULL DEFAULT 0.0,
        avg_reimbursement_after_usd     REAL NOT NULL DEFAULT 0.0,
        claim_rejection_risk_score      REAL NOT NULL DEFAULT 0.0,
        estimated_financial_impact_usd  REAL NOT NULL DEFAULT 0.0,
        scan_status     TEXT NOT NULL DEFAULT 'PENDING',
        clinical_intent TEXT,
        extracted_at    TEXT,
        agent1_notes    TEXT,
        workflow_status TEXT NOT NULL DEFAULT 'PENDING',
        last_policy_applied             TEXT,
        financial_impact_validated      REAL,
        alert_sent      INTEGER NOT NULL DEFAULT 0,
        alert_sent_at   TEXT,
        agent2_notes    TEXT,
        executed_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS billing_code_rules (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id       TEXT NOT NULL,
        hcpcs_code        TEXT NOT NULL,
        current_rate_usd  REAL NOT NULL,
        previous_rate_usd REAL,
        effective_date    TEXT NOT NULL,
        last_policy_id    TEXT,
        workflow_status   TEXT NOT NULL DEFAULT 'ACTIVE',
        updated_at        TEXT DEFAULT (datetime('now')),
        UNIQUE(hospital_id, hcpcs_code)
    );

    CREATE TABLE IF NOT EXISTS hospital_alerts (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id         TEXT NOT NULL UNIQUE,
        policy_id        TEXT NOT NULL,
        hospital_id      TEXT NOT NULL,
        hospital_state   TEXT,
        hcpcs_code       TEXT,
        alert_type       TEXT NOT NULL,
        message          TEXT NOT NULL,
        financial_impact REAL,
        risk_score       REAL,
        resolved         INTEGER NOT NULL DEFAULT 0,
        created_at       TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS claim_rejection_monitor (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_id             TEXT NOT NULL,
        hospital_id           TEXT NOT NULL,
        hcpcs_code            TEXT NOT NULL,
        predicted_risk_score  REAL NOT NULL,
        actual_rejection_rate REAL,
        claims_submitted      INTEGER DEFAULT 0,
        claims_rejected       INTEGER DEFAULT 0,
        monitoring_start      TEXT DEFAULT (datetime('now')),
        last_checked          TEXT,
        status                TEXT NOT NULL DEFAULT 'MONITORING'
    );

    CREATE TABLE IF NOT EXISTS agent_execution_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        agent       TEXT NOT NULL,
        action      TEXT NOT NULL,
        policy_id   TEXT,
        hospital_id TEXT,
        status      TEXT NOT NULL,
        duration_ms INTEGER,
        details     TEXT,
        error_msg   TEXT,
        executed_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()
    logger.info("[MAIN] ✅ SQLite database and tables ready")

def load_csv():
    """Auto-load CSV if database is empty."""
    from config.db_config import get_connection
    import csv as _csv

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM policies")
    count = cur.fetchone()[0]
    conn.close()

    if count > 0:
        logger.info(f"[MAIN] ✅ Database has {count:,} records")
        return

    csv_path = os.path.join(os.path.dirname(__file__), "data", "sample_policies.csv")
    if not os.path.exists(csv_path):
        logger.warning("[MAIN] ⚠  No CSV found. Put sample_policies.csv in the /data folder.")
        return

    logger.info("[MAIN] Loading CSV into database...")
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            rows.append((
                r["policy_id"], r["policy_date"], r["agency"], r["policy_type"],
                r["affected_hcpcs_code"], r["hospital_id"], r["hospital_state"],
                int(r["service_volume"] or 0),
                float(r["avg_reimbursement_before_usd"] or 0),
                float(r["avg_reimbursement_after_usd"]  or 0),
                float(r["claim_rejection_risk_score"]   or 0),
                float(r["estimated_financial_impact_usd"] or 0),
            ))

    conn = get_connection()
    cur  = conn.cursor()
    sql  = """INSERT OR IGNORE INTO policies
        (policy_id,policy_date,agency,policy_type,affected_hcpcs_code,
         hospital_id,hospital_state,service_volume,
         avg_reimbursement_before_usd,avg_reimbursement_after_usd,
         claim_rejection_risk_score,estimated_financial_impact_usd,
         scan_status,workflow_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'PENDING','PENDING')"""

    for i in range(0, len(rows), 200):
        cur.executemany(sql, rows[i:i+200])
        conn.commit()
        print(f"\r[MAIN] Loading... {min(i+200,len(rows))}/{len(rows)}", end="", flush=True)

    conn.close()
    print()
    logger.info(f"[MAIN] ✅ Loaded {len(rows):,} policy records")

def _start_agents():
    import schedule
    from agents.agent1_scanner import run_scan_cycle
    from agents.agent2_executor import monitor_claim_rejections
    from config.constants import SCAN_INTERVAL_SECONDS
    interval = max(SCAN_INTERVAL_SECONDS // 60, 1)
    try:
        run_scan_cycle()
    except Exception as e:
        logger.error(f"[MAIN] Agent1 first run: {e}")
    schedule.every(interval).minutes.do(run_scan_cycle)
    schedule.every(1).hours.do(monitor_claim_rejections)
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    print("\n" + "="*52)
    print("  Healthcare Reimbursement Agent System")
    print("  Powered by SQLite — no setup required")
    print("="*52 + "\n")

    setup_database()
    load_csv()

    t = threading.Thread(target=_start_agents, daemon=True)
    t.start()
    logger.info("[MAIN] Agents started. Opening dashboard...")

    from dashboard.dashboard import Dashboard
    Dashboard().mainloop()
