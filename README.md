# Healthcare Reimbursement Agent Dashboard

Autonomous dual-agent system with a live Python/Tkinter dashboard.

## Quick Start

```bash
# 1. Create & activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DB_PASSWORD and ANTHROPIC_API_KEY

# 4. Create database tables
python db/setup.py

# 5. Load dataset (place sample_policies.csv in /data first)
python db/seed.py

# 6. Launch dashboard + agents
python main.py
```

## Project Structure

```
healthcare-dashboard-app/
├── main.py                     ← Starts agents + opens dashboard
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── agent1_scanner.py       ← SCAN→EXTRACT→INTERPRET→MAP→OUTPUT
│   └── agent2_executor.py      ← RECEIVE→ANALYZE→RISK→EXECUTE→MONITOR
│
├── config/
│   ├── constants.py            ← Thresholds, weights, risk levels
│   └── db_config.py            ← MySQL connection pool
│
├── db/
│   ├── setup.py                ← Creates all 5 MySQL tables
│   └── seed.py                 ← Loads sample_policies.csv
│
├── utils/
│   ├── logger.py               ← Structured logger
│   ├── audit.py                ← DB audit trail writer
│   └── llm_client.py           ← Anthropic API wrapper
│
├── dashboard/
│   └── dashboard.py            ← Full Tkinter dashboard UI
│
└── data/
    └── sample_policies.csv     ← Put your CSV here
```

## Dashboard Tabs

| Tab | Contents |
|---|---|
| Overview | KPI cards, risk distribution chart, agency table, live log |
| Policies | All 5000 policies with risk colour coding and filter |
| Alerts | All hospital alerts by severity |
| Billing Rules | Live HCPCS rates per hospital |
| Agencies | Agency & HCPCS breakdown tables + state bar chart |
| Audit Log | Full agent execution log + live output stream |

## Dashboard Buttons

- **⟳ Refresh** — manually refresh all data
- **▶ Run Agent 1** — trigger a policy scan cycle immediately
- **◉ Monitor** — trigger Agent 2 monitoring check

## Tuning (.env)

| Variable | Default | Effect |
|---|---|---|
| `RISK_THRESHOLD_CRITICAL` | `0.70` | Triggers Agent 2 immediately |
| `RISK_THRESHOLD_HIGH` | `0.50` | Triggers Agent 2 |
| `FINANCIAL_IMPACT_THRESHOLD` | `-100000` | Extra risk penalty below this |
| `SCAN_INTERVAL_MINUTES` | `30` | Agent 1 scan frequency |
