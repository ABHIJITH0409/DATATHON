# agents/agent2_executor.py — Agent 2: Reimbursement Impact Executor
import json, uuid, time
from datetime import datetime, date
from config.constants import (RISK, FINANCIAL_IMPACT_THRESHOLD,
                               WORKFLOW_STATUS, COMPLIANCE_DEADLINE_DAYS, BLAST_THRESHOLD)
from config.db_config import get_connection
from utils.audit import audit_log
from agents.agent1_scanner import _log

def receive_escalation(payload):
    if not all(k in payload for k in ("policy_id","hospital_id","hcpcs_code")):
        _log("ERROR","[AGENT2:RECEIVE] Invalid payload"); return
    _log("INFO", f"[AGENT2:RECEIVE] {payload['policy_id']} hosp={payload['hospital_id']} "
                 f"hcpcs={payload['hcpcs_code']} action={payload.get('action_class')}")
    run_execution_pipeline(payload)

def analyze_financial_impact(payload):
    rb, ra, sv = float(payload["rate_before"]), float(payload["rate_after"]), int(payload["service_volume"])
    reported   = float(payload["financial_impact"])
    computed   = sv * (ra - rb)
    variance   = abs(computed - reported)
    var_pct    = (variance / abs(reported) * 100) if reported != 0 else 0
    _log("INFO", f"[AGENT2:ANALYZE] {payload['policy_id']} impact=${computed:,.2f} validated={var_pct<1}")
    return {
        "computed_impact": round(computed, 2), "reported_impact": reported,
        "variance_pct": round(var_pct, 2), "validated": var_pct < 1.0,
        "rate_delta": round(ra - rb, 2), "is_revenue_loss": computed < 0,
        "is_material": abs(computed) > abs(FINANCIAL_IMPACT_THRESHOLD),
    }

def risk_assess(payload, analysis):
    hcpcs, hosp = payload["hcpcs_code"], payload["hospital_id"]
    policy_type = payload["policy_type"]
    risk_score  = float(payload["risk_score"])
    pd = payload.get("policy_date","")
    try: eff = datetime.strptime(str(pd)[:10], "%Y-%m-%d").date()
    except: eff = date.today()
    days = (eff - date.today()).days

    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM policies WHERE affected_hcpcs_code=? "
                "AND policy_date >= date(?, '-90 days') AND hospital_id!=?",
                (hcpcs, str(eff), hosp))
    blast = cur.fetchone()[0]; conn.close()

    is_blast  = blast >= BLAST_THRESHOLD
    is_urgent = policy_type == "Compliance Requirement" and 0 < days <= COMPLIANCE_DEADLINE_DAYS
    if   risk_score >= RISK["CRITICAL"] or (is_blast and analysis["is_material"]): sev = "CRITICAL"
    elif risk_score >= RISK["HIGH"]     or is_urgent:                               sev = "HIGH"
    elif risk_score >= RISK["MEDIUM"]:                                              sev = "MEDIUM"
    else:                                                                            sev = "LOW"
    _log("INFO", f"[AGENT2:RISK] {payload['policy_id']} → {sev} blast={blast}")
    return {"severity": sev, "risk_score": risk_score, "blast_radius": blast,
            "is_blast_event": is_blast, "days_to_effective": days,
            "is_compliance_urgent": is_urgent, "is_past_deadline": days < 0,
            "requires_claim_block": sev == "CRITICAL" or is_urgent}

def run_execution_pipeline(payload):
    t0   = time.time()
    conn = get_connection(); cur = conn.cursor()
    try:
        analysis   = analyze_financial_impact(payload)
        assessment = risk_assess(payload, analysis)
        status     = "BLOCKED" if assessment["requires_claim_block"] else "REVIEW_REQUIRED"

        # 4a: billing_code_rules
        cur.execute("""INSERT INTO billing_code_rules
            (hospital_id,hcpcs_code,current_rate_usd,previous_rate_usd,
             effective_date,last_policy_id,workflow_status)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(hospital_id,hcpcs_code) DO UPDATE SET
            previous_rate_usd=current_rate_usd,
            current_rate_usd=excluded.current_rate_usd,
            effective_date=excluded.effective_date,
            last_policy_id=excluded.last_policy_id,
            workflow_status=excluded.workflow_status""",
            (payload["hospital_id"], payload["hcpcs_code"], payload["rate_after"],
             payload["rate_before"], payload["policy_date"], payload["policy_id"], status))

        # 4b: hospital alert
        impact = analysis["computed_impact"]
        sign   = "+" if impact >= 0 else ""
        lbl    = "REVENUE LOSS" if impact < 0 else "REVENUE GAIN"
        block  = (f"BLOCKED: Claims for {payload['hcpcs_code']} at {payload['hospital_id']} BLOCKED."
                  if assessment["requires_claim_block"]
                  else f"REVIEW: Update billing templates for {payload['hcpcs_code']}.")
        msg    = (f"[{assessment['severity']}] {payload['hospital_id']} ({payload['hospital_state']})\n"
                  f"Policy:{payload['policy_id']} Agency:{payload['agency']} {payload['policy_type']}\n"
                  f"HCPCS:{payload['hcpcs_code']} ${payload['rate_before']}→${payload['rate_after']}\n"
                  f"Impact:{sign}${abs(impact):,.2f} ({lbl}) Risk:{payload['risk_score']}\n{block}")
        atype  = ("CRITICAL" if assessment["severity"]=="CRITICAL" else
                  "BLAST_RADIUS" if assessment["is_blast_event"] else
                  "COMPLIANCE_DEADLINE" if assessment["is_compliance_urgent"] else
                  "HIGH" if assessment["severity"]=="HIGH" else "MEDIUM")
        cur.execute("INSERT OR IGNORE INTO hospital_alerts "
                    "(alert_id,policy_id,hospital_id,hospital_state,hcpcs_code,"
                    "alert_type,message,financial_impact,risk_score) VALUES (?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), payload["policy_id"], payload["hospital_id"],
                     payload["hospital_state"], payload["hcpcs_code"],
                     atype, msg, impact, payload["risk_score"]))
        cur.execute("UPDATE policies SET alert_sent=1, alert_sent_at=datetime('now') WHERE policy_id=?",
                    (payload["policy_id"],))

        # 4c: workflow status
        wf_status = WORKFLOW_STATUS["BLOCKED"] if assessment["requires_claim_block"] else WORKFLOW_STATUS["AGENT_REVIEWED"]
        cur.execute("UPDATE policies SET workflow_status=?, last_policy_applied=?, "
                    "financial_impact_validated=?, agent2_notes=?, executed_at=datetime('now') "
                    "WHERE policy_id=?",
                    (wf_status, payload["policy_id"], payload["financial_impact"],
                     json.dumps({"severity": assessment["severity"], "blast": assessment["blast_radius"]}),
                     payload["policy_id"]))

        # 4d: monitoring record
        cur.execute("INSERT OR IGNORE INTO claim_rejection_monitor "
                    "(policy_id,hospital_id,hcpcs_code,predicted_risk_score,status) "
                    "VALUES (?,?,?,?,'MONITORING')",
                    (payload["policy_id"], payload["hospital_id"],
                     payload["hcpcs_code"], payload["risk_score"]))

        conn.commit()
        ms = int((time.time()-t0)*1000)
        _log("INFO", f"[AGENT2] ✅ {payload['policy_id']} done {ms}ms sev={assessment['severity']}")
        audit_log("AGENT2","FULL_PIPELINE","SUCCESS",payload["policy_id"],payload["hospital_id"],ms,
                  {"severity":assessment["severity"],"impact":analysis["computed_impact"],
                   "blocked":assessment["requires_claim_block"]})
    except Exception as e:
        conn.rollback()
        _log("ERROR", f"[AGENT2] ❌ {payload['policy_id']}: {e}")
        audit_log("AGENT2","FULL_PIPELINE","FAILED",payload["policy_id"],error_msg=str(e))
        raise
    finally:
        conn.close()

def monitor_claim_rejections():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM claim_rejection_monitor WHERE status='MONITORING' LIMIT 50")
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            sub = r.get("claims_submitted") or 0
            rej = r.get("claims_rejected")  or 0
            if sub > 0:
                actual = rej / sub
                cur.execute("UPDATE claim_rejection_monitor SET actual_rejection_rate=?, "
                            "last_checked=datetime('now') WHERE id=?", (round(actual,3), r["id"]))
                if actual > float(r["predicted_risk_score"]) * 1.5:
                    _log("ERROR", f"[AGENT2:MONITOR] ⚠ {r['policy_id']} actual={actual:.2f}")
                    cur.execute("UPDATE claim_rejection_monitor SET status='ESCALATED' WHERE id=?", (r["id"],))
            cur.execute("UPDATE claim_rejection_monitor SET last_checked=datetime('now') WHERE id=?", (r["id"],))
        conn.commit()
        _log("INFO", f"[AGENT2:MONITOR] Checked {len(rows)} records")
    finally:
        conn.close()
