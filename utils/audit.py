import json
from config.db_config import get_connection
from utils.logger import logger

def audit_log(agent, action, status, policy_id=None, hospital_id=None,
              duration_ms=None, details=None, error_msg=None):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO agent_execution_log "
            "(agent,action,policy_id,hospital_id,status,duration_ms,details,error_msg) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (agent, action, policy_id, hospital_id, status,
             duration_ms, json.dumps(details) if details else None, error_msg))
        conn.commit(); conn.close()
    except Exception as e:
        logger.error(f"[AUDIT] {e}")
