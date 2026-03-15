import os, sys, csv
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.db_config import get_connection

CSV_PATH   = os.path.join(os.path.dirname(__file__), "../data/sample_policies.csv")
BATCH_SIZE = 200

def seed():
    path = os.path.abspath(CSV_PATH)
    if not os.path.exists(path):
        print(f"[SEED] ❌ CSV not found: {path}")
        print("[SEED]    Put sample_policies.csv in the /data folder"); sys.exit(1)

    records = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append(row)
    print(f"[SEED] {len(records)} records found. Inserting...")

    conn = get_connection(); cur = conn.cursor()
    sql = ("INSERT IGNORE INTO policies "
           "(policy_id,policy_date,agency,policy_type,affected_hcpcs_code,"
           "hospital_id,hospital_state,service_volume,"
           "avg_reimbursement_before_usd,avg_reimbursement_after_usd,"
           "claim_rejection_risk_score,estimated_financial_impact_usd,"
           "scan_status,workflow_status) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','PENDING')")

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        vals  = [(r["policy_id"],r["policy_date"],r["agency"],r["policy_type"],
                  r["affected_hcpcs_code"],r["hospital_id"],r["hospital_state"],
                  int(r["service_volume"] or 0),
                  float(r["avg_reimbursement_before_usd"] or 0),
                  float(r["avg_reimbursement_after_usd"] or 0),
                  float(r["claim_rejection_risk_score"] or 0),
                  float(r["estimated_financial_impact_usd"] or 0)) for r in batch]
        cur.executemany(sql, vals); conn.commit()
        print(f"\r[SEED] {min(i+BATCH_SIZE,len(records))}/{len(records)}", end="", flush=True)

    print(f"\n[SEED] ✅ Done. {len(records)} rows loaded.")
    cur.close(); conn.close()

if __name__ == "__main__":
    try: seed()
    except Exception as e: print(f"\n[SEED] ❌ {e}"); sys.exit(1)
