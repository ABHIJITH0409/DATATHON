import os
from dotenv import load_dotenv
load_dotenv()

RISK = {
    "CRITICAL": float(os.getenv("RISK_THRESHOLD_CRITICAL", 0.70)),
    "HIGH":     float(os.getenv("RISK_THRESHOLD_HIGH",     0.50)),
    "MEDIUM":   0.30,
    "LOW":      0.0,
}

FINANCIAL_IMPACT_THRESHOLD = float(os.getenv("FINANCIAL_IMPACT_THRESHOLD", -100000))

AGENCY_WEIGHT = {
    "CMS": 1.0, "HHS": 0.95, "FDA": 0.80,
    "CDC": 0.75, "OIG": 0.90, "DEFAULT": 0.70,
}

POLICY_TYPE_RISK = {
    "Compliance Requirement":  1.30,
    "Billing Rule Change":     1.25,
    "Reimbursement Update":    1.10,
    "Coding Guideline Update": 1.05,
    "Coverage Expansion":      0.85,
}

HIGH_VOLUME_CODES = [
    "99213","99214","99215","36415","85025",
    "80053","93000","71020","A0427","A0429",
]

WORKFLOW_STATUS = {
    "PENDING": "PENDING", "AGENT_REVIEWED": "AGENT_REVIEWED",
    "BLOCKED": "BLOCKED", "COMPLIANT": "COMPLIANT", "ESCALATED": "ESCALATED",
}

SCAN_INTERVAL_SECONDS  = int(os.getenv("SCAN_INTERVAL_MINUTES", 30)) * 60
COMPLIANCE_DEADLINE_DAYS = int(os.getenv("COMPLIANCE_DEADLINE_DAYS", 30))
BLAST_THRESHOLD          = int(os.getenv("MULTI_HOSPITAL_BLAST_THRESHOLD", 5))
ANTHROPIC_MODEL          = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
