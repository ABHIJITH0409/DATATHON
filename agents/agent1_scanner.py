# agents/agent1_scanner.py — Agent 1: Policy Intelligence Scanner
import json, time
from datetime import datetime, date
from config.constants import (RISK, AGENCY_WEIGHT, POLICY_TYPE_RISK,
                               HIGH_VOLUME_CODES, FINANCIAL_IMPACT_THRESHOLD)
from config.db_config import get_connection
from utils.logger import logger
from utils.audit import audit_log
from utils.llm_client import call_llm

_log_buffer = []

def _log(level, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    _log_buffer.append({"ts": ts, "level": level, "msg": msg})
    if len(_log_buffer) > 500:
        _log_buffer.pop(0)
    getattr(logger, level.lower(), logger.info)(msg)

def get_log_buffer():
    return list(_log_buffer)

def scan_for_new_policies():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT * FROM policies WHERE scan_status='PENDING'
                   ORDER BY claim_rejection_risk_score DESC LIMIT 100""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    _log("INFO", f"[AGENT1:SCAN] Found {len(rows)} pending policies")
    return rows

def extract_policy_data(p):
    rate_before = float(p.get("avg_reimbursement_before_usd") or 0)
    rate_after  = float(p.get("avg_reimbursement_after_usd")  or 0)
    fin_impact  = float(p.get("estimated_financial_impact_usd") or 0)
    risk_score  = float(p.get("claim_rejection_risk_score") or 0)
    svc_vol     = int(p.get("service_volume") or 0)
    hcpcs       = p.get("affected_hcpcs_code","")
    policy_type = p.get("policy_type","")
    pd = p.get("policy_date","")
    if isinstance(pd, (date, datetime)):
        eff = pd if isinstance(pd, date) else pd.date()
    else:
        try: eff = datetime.strptime(str(pd)[:10], "%Y-%m-%d").date()
        except: eff = date.today()
    days = (eff - date.today()).days
    is_high_vol   = hcpcs in HIGH_VOLUME_CODES
    is_negative   = fin_impact < 0
    is_compliance = policy_type == "Compliance Requirement"
    is_billing    = policy_type == "Billing Rule Change"
    return {
        "policy_id": p.get("policy_id",""), "agency": p.get("agency",""),
        "policy_type": policy_type, "hcpcs_code": hcpcs,
        "hospital_id": p.get("hospital_id",""), "hospital_state": p.get("hospital_state",""),
        "service_volume": svc_vol, "rate_before": rate_before, "rate_after": rate_after,
        "reimbursement_delta": round(rate_after - rate_before, 2),
        "risk_score": risk_score, "financial_impact": fin_impact,
        "policy_date": str(eff), "days_until_effective": days,
        "is_high_volume_code": is_high_vol, "is_negative_impact": is_negative,
        "is_compliance_type": is_compliance, "is_billing_change": is_billing,
        "extraction_flags": {
            "highVolume": is_high_vol, "negativeImpact": is_negative,
            "complianceRisk": is_compliance, "billingRisk": is_billing,
            "urgentDeadline": 0 < days <= 30, "pastDeadline": days < 0,
        },
    }

def interpret_clinical_intent(ex):
    system = ("You are a US healthcare compliance expert in HCPCS billing codes. "
              "Interpret policy changes in 2-3 sentences. Be specific.")
    sign = "+" if ex["reimbursement_delta"] >= 0 else ""
    user = (f"Policy:{ex['policy_id']} Agency:{ex['agency']} Type:{ex['policy_type']}\n"
            f"HCPCS:{ex['hcpcs_code']} Rate:${ex['rate_before']}→${ex['rate_after']} "
            f"(Δ{sign}{ex['reimbursement_delta']}) Vol:{ex['service_volume']} "
            f"Impact:${ex['financial_impact']:,.2f} Risk:{ex['risk_score']}\n"
            f"What does this mean clinically? What must the billing team do?")
    try:
        return call_llm(system, user, 300)
    except Exception as e:
        _log("WARNING", f"[AGENT1:INTERPRET] LLM fallback: {e}")
        d = "increased" if ex["reimbursement_delta"] >= 0 else "decreased"
        return (f"{ex['policy_type']} from {ex['agency']} on HCPCS {ex['hcpcs_code']}. "
                f"Reimbursement {d} by ${abs(ex['reimbursement_delta']):.2f}. "
                f"Estimated impact: ${ex['financial_impact']:,.2f}.")

def map_and_score(ex):
    aw = AGENCY_WEIGHT.get(ex["agency"], AGENCY_WEIGHT["DEFAULT"])
    pm = POLICY_TYPE_RISK.get(ex["policy_type"], 1.0)
    cs = ex["risk_score"] * aw * pm
    if ex["is_high_volume_code"]:                            cs *= 1.15
    if ex["financial_impact"] < FINANCIAL_IMPACT_THRESHOLD: cs *= 1.20
    if ex["extraction_flags"]["urgentDeadline"]:             cs *= 1.10
    cs = round(min(cs, 1.0), 3)
    if   cs >= RISK["CRITICAL"]: action = "CRITICAL_ESCALATE"
    elif cs >= RISK["HIGH"]:     action = "HIGH_PRIORITY"
    elif cs >= RISK["MEDIUM"]:   action = "MEDIUM_REVIEW"
    else:                        action = "LOW_MONITOR"
    return {"composite_score": cs, "action_class": action,
            "agency_weight": aw, "policy_multiplier": pm}

def output_and_escalate(ex, scored, intent):
    notes = json.dumps({"composite_score": scored["composite_score"],
                        "action_class": scored["action_class"],
                        "flags": ex["extraction_flags"]})
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE policies SET scan_status='COMPLETED', clinical_intent=?, "
                "extracted_at=datetime('now'), agent1_notes=? WHERE policy_id=?",
                (intent, notes, ex["policy_id"]))
    conn.commit(); conn.close()
    _log("INFO", f"[AGENT1:OUTPUT] {ex['policy_id']} → {scored['action_class']} "
                 f"(score={scored['composite_score']}) impact=${ex['financial_impact']:,.0f}")
    if scored["action_class"] in ("CRITICAL_ESCALATE", "HIGH_PRIORITY"):
        _log("WARNING", f"[AGENT1:ESCALATE] → Agent 2 for {ex['policy_id']}")
        from agents.agent2_executor import receive_escalation
        try:
            receive_escalation({**ex, "risk_score": scored["composite_score"],
                                 "action_class": scored["action_class"],
                                 "clinical_intent": intent})
        except Exception as e:
            _log("ERROR", f"[AGENT1:ESCALATE] {ex['policy_id']}: {e}")

def run_scan_cycle():
    t0 = time.time()
    _log("INFO", "=" * 50)
    _log("INFO", "[AGENT1] Starting scan cycle")
    processed = escalated = errors = 0
    policies = scan_for_new_policies()
    if not policies:
        _log("INFO", "[AGENT1] No pending policies.")
        return {"processed": 0, "escalated": 0, "errors": 0}
    for p in policies:
        pid = p["policy_id"]; t1 = time.time()
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("UPDATE policies SET scan_status='SCANNED' WHERE policy_id=?", (pid,))
            conn.commit(); conn.close()
            ex     = extract_policy_data(p)
            intent = interpret_clinical_intent(ex)
            scored = map_and_score(ex)
            output_and_escalate(ex, scored, intent)
            if scored["action_class"] in ("CRITICAL_ESCALATE", "HIGH_PRIORITY"):
                escalated += 1
            audit_log("AGENT1","FULL_PIPELINE","SUCCESS", pid, p.get("hospital_id"),
                      int((time.time()-t1)*1000),
                      {"score": scored["composite_score"], "impact": ex["financial_impact"]})
            processed += 1
        except Exception as e:
            errors += 1
            _log("ERROR", f"[AGENT1] Error {pid}: {e}")
            try:
                conn = get_connection(); cur = conn.cursor()
                cur.execute("UPDATE policies SET scan_status='ERROR', agent1_notes=? WHERE policy_id=?",
                            (str(e), pid))
                conn.commit(); conn.close()
            except: pass
            audit_log("AGENT1","FULL_PIPELINE","FAILED", pid, error_msg=str(e))
    elapsed = round(time.time()-t0, 1)
    _log("INFO", f"[AGENT1] Done. processed={processed} escalated={escalated} errors={errors} ({elapsed}s)")
    return {"processed": processed, "escalated": escalated, "errors": errors}
