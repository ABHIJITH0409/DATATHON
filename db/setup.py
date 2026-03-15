import os, sys
import mysql.connector
from dotenv import load_dotenv
load_dotenv()

def setup():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST","localhost"), port=int(os.getenv("DB_PORT",3306)),
        user=os.getenv("DB_USER","root"), password=os.getenv("DB_PASSWORD",""),
    )
    cur = conn.cursor()
    db  = os.getenv("DB_NAME","healthcare_reimbursement")
    print(f"[SETUP] Creating database: {db}")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}`")
    cur.execute(f"USE `{db}`")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        policy_id VARCHAR(20) NOT NULL UNIQUE,
        policy_date DATE NOT NULL,
        agency VARCHAR(10) NOT NULL,
        policy_type VARCHAR(50) NOT NULL,
        affected_hcpcs_code VARCHAR(10) NOT NULL,
        hospital_id VARCHAR(15) NOT NULL,
        hospital_state CHAR(2) NOT NULL,
        service_volume INT NOT NULL DEFAULT 0,
        avg_reimbursement_before_usd DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        avg_reimbursement_after_usd  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        claim_rejection_risk_score   DECIMAL(5,3)  NOT NULL DEFAULT 0.000,
        estimated_financial_impact_usd DECIMAL(15,2) NOT NULL DEFAULT 0.00,
        scan_status ENUM('PENDING','SCANNED','INTERPRETED','COMPLETED','ERROR') NOT NULL DEFAULT 'PENDING',
        clinical_intent TEXT, extracted_at DATETIME, agent1_notes TEXT,
        workflow_status ENUM('PENDING','AGENT_REVIEWED','BLOCKED','COMPLIANT','ESCALATED') NOT NULL DEFAULT 'PENDING',
        last_policy_applied VARCHAR(20), financial_impact_validated DECIMAL(15,2),
        alert_sent TINYINT(1) NOT NULL DEFAULT 0, alert_sent_at DATETIME,
        agent2_notes TEXT, executed_at DATETIME,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_risk  (claim_rejection_risk_score),
        INDEX idx_scan  (scan_status),
        INDEX idx_wflow (workflow_status),
        INDEX idx_hosp  (hospital_id),
        INDEX idx_hcpcs (affected_hcpcs_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    print("[SETUP] ✓ policies")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS billing_code_rules (
        id INT AUTO_INCREMENT PRIMARY KEY,
        hospital_id VARCHAR(15) NOT NULL,
        hcpcs_code  VARCHAR(10) NOT NULL,
        current_rate_usd  DECIMAL(10,2) NOT NULL,
        previous_rate_usd DECIMAL(10,2),
        effective_date DATE NOT NULL,
        last_policy_id VARCHAR(20),
        workflow_status ENUM('ACTIVE','BLOCKED','REVIEW_REQUIRED') NOT NULL DEFAULT 'ACTIVE',
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_hc (hospital_id, hcpcs_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    print("[SETUP] ✓ billing_code_rules")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hospital_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        alert_id VARCHAR(36) NOT NULL UNIQUE,
        policy_id VARCHAR(20) NOT NULL,
        hospital_id VARCHAR(15) NOT NULL,
        hospital_state CHAR(2),
        hcpcs_code VARCHAR(10),
        alert_type ENUM('CRITICAL','HIGH','MEDIUM','COMPLIANCE_DEADLINE','BLAST_RADIUS') NOT NULL,
        message TEXT NOT NULL,
        financial_impact DECIMAL(15,2),
        risk_score DECIMAL(5,3),
        resolved TINYINT(1) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_hosp (hospital_id), INDEX idx_type (alert_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    print("[SETUP] ✓ hospital_alerts")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS claim_rejection_monitor (
        id INT AUTO_INCREMENT PRIMARY KEY,
        policy_id VARCHAR(20) NOT NULL,
        hospital_id VARCHAR(15) NOT NULL,
        hcpcs_code VARCHAR(10) NOT NULL,
        predicted_risk_score  DECIMAL(5,3) NOT NULL,
        actual_rejection_rate DECIMAL(5,3),
        claims_submitted INT DEFAULT 0,
        claims_rejected  INT DEFAULT 0,
        monitoring_start DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_checked DATETIME,
        status ENUM('MONITORING','RESOLVED','ESCALATED') NOT NULL DEFAULT 'MONITORING'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    print("[SETUP] ✓ claim_rejection_monitor")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS agent_execution_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        agent ENUM('AGENT1','AGENT2') NOT NULL,
        action VARCHAR(50) NOT NULL,
        policy_id VARCHAR(20), hospital_id VARCHAR(15),
        status ENUM('SUCCESS','FAILED','SKIPPED') NOT NULL,
        duration_ms INT, details JSON, error_msg TEXT,
        executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_agent (agent), INDEX idx_pol (policy_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    print("[SETUP] ✓ agent_execution_log")

    conn.commit(); cur.close(); conn.close()
    print("\n[SETUP] ✅ All tables created. Run: python db/seed.py")

if __name__ == "__main__":
    try:
        setup()
    except Exception as e:
        print(f"[SETUP] ❌ {e}"); sys.exit(1)
