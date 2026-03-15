# dashboard/dashboard.py
# ═══════════════════════════════════════════════════════════════════════
#  Healthcare Reimbursement Agent — Live Dashboard
#  Pure Python / Tkinter — no browser required
#  Run: python dashboard/dashboard.py
# ═══════════════════════════════════════════════════════════════════════

import sys, os, threading, time
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
from tkinter import ttk, font as tkfont
from dotenv import load_dotenv
load_dotenv()

# ── Palette ────────────────────────────────────────────────────────────
BG       = "#0d1117"
SURFACE  = "#161b22"
CARD     = "#1c2128"
BORDER   = "#30363d"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
ACCENT   = "#388bfd"
GREEN    = "#3fb950"
AMBER    = "#d29922"
RED      = "#f85149"
PURPLE   = "#bc8cff"
TEAL     = "#39d3f2"
HEADER   = "#21262d"
ROW_ODD  = "#1c2128"
ROW_EVEN = "#161b22"

F_TITLE  = ("Consolas", 13, "bold")
F_HEAD   = ("Consolas", 10, "bold")
F_BODY   = ("Consolas", 10)
F_SMALL  = ("Consolas", 9)
F_KPI_N  = ("Consolas", 26, "bold")
F_KPI_L  = ("Consolas", 9)
F_BTN    = ("Consolas", 10, "bold")
F_NAV    = ("Consolas", 11)
F_LOG    = ("Consolas", 9)

# ── DB helpers (SQLite) ────────────────────────────────────────────────
def q(sql, params=()):
    try:
        from config.db_config import get_connection
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        conn.close()
        out = []
        for row in rows:
            c = {}
            for k, v in zip(cols, row):
                if v is None: c[k] = ""
                else: c[k] = v
            out.append(c)
        return out
    except Exception as e:
        return [{"__error__": str(e)}]

def qs(sql, params=()):
    r = q(sql, params)
    if r and "__error__" not in r[0]:
        v = list(r[0].values())[0]
        return v if v is not None else 0
    return 0


# ══════════════════════════════════════════════════════════════════════
class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Healthcare Reimbursement Agent  —  Live Dashboard")
        self.geometry("1440x880")
        self.configure(bg=BG)
        self.minsize(1100, 700)
        self.resizable(True, True)

        self._tab      = "overview"
        self._agent_running = False
        self._auto_on  = True

        self._setup_styles()
        self._build_topbar()
        self._build_body()
        self._show_tab("overview")
        self.after(400, self._refresh)
        self._schedule()

    # ── STYLES ─────────────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview",
            background=ROW_ODD, foreground=TEXT, fieldbackground=ROW_ODD,
            font=F_BODY, rowheight=26, borderwidth=0)
        s.configure("Treeview.Heading",
            background=HEADER, foreground=MUTED, font=F_HEAD,
            relief="flat", borderwidth=0)
        s.map("Treeview",
            background=[("selected", "#264f78")],
            foreground=[("selected", TEXT)])
        s.configure("Vertical.TScrollbar",
            background=CARD, troughcolor=BG, arrowcolor=MUTED, borderwidth=0)

    # ── TOP BAR ────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self, bg=SURFACE, height=52)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # Left — brand
        left = tk.Frame(bar, bg=SURFACE)
        left.pack(side=tk.LEFT, padx=20, pady=0, fill=tk.Y)

        dot = tk.Canvas(left, width=10, height=10, bg=SURFACE, highlightthickness=0)
        dot.pack(side=tk.LEFT, padx=(0, 10))
        dot.create_oval(1, 1, 9, 9, fill=GREEN, outline="")
        self._pulse_dot(dot)

        tk.Label(left, text="HEALTHCARE REIMBURSEMENT AGENT",
                 font=("Consolas", 12, "bold"), bg=SURFACE, fg=TEXT).pack(side=tk.LEFT)
        tk.Label(left, text="  |  Live Monitoring Dashboard",
                 font=("Consolas", 10), bg=SURFACE, fg=MUTED).pack(side=tk.LEFT)

        # Right — controls
        right = tk.Frame(bar, bg=SURFACE)
        right.pack(side=tk.RIGHT, padx=20, fill=tk.Y)

        self._clock_var = tk.StringVar(value="")
        tk.Label(right, textvariable=self._clock_var,
                 font=F_SMALL, bg=SURFACE, fg=MUTED).pack(side=tk.LEFT, padx=(0, 20))

        self._status_var = tk.StringVar(value="● IDLE")
        tk.Label(right, textvariable=self._status_var,
                 font=F_SMALL, bg=SURFACE, fg=GREEN).pack(side=tk.LEFT, padx=(0, 16))

        self._btn("⟳  Refresh",  right, self._refresh,      ACCENT).pack(side=tk.LEFT, padx=4)
        self._btn("▶  Run Agent 1", right, self._run_agent1, GREEN).pack(side=tk.LEFT, padx=4)
        self._btn("◉  Monitor",  right, self._run_monitor,  AMBER).pack(side=tk.LEFT, padx=4)

        self._update_clock()

    def _pulse_dot(self, canvas):
        def _toggle(on=True):
            canvas.create_oval(1,1,9,9, fill=GREEN if on else "#1a4a2a", outline="")
            canvas.after(900, lambda: _toggle(not on))
        _toggle()

    def _btn(self, text, parent, cmd, color):
        b = tk.Button(parent, text=text, font=F_BTN, bg=CARD, fg=color,
                      activebackground=BORDER, activeforeground=color,
                      relief="flat", bd=0, padx=12, pady=6, cursor="hand2", command=cmd,
                      highlightbackground=BORDER, highlightthickness=1)
        return b

    def _update_clock(self):
        self._clock_var.set(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._update_clock)

    # ── BODY (sidebar + content) ────────────────────────────────────────
    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        self._sidebar = tk.Frame(body, bg=SURFACE, width=200)
        self._sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._panels = {}
        for name, builder in [
            ("overview",  self._build_overview),
            ("policies",  self._build_policies),
            ("alerts",    self._build_alerts),
            ("billing",   self._build_billing),
            ("agencies",  self._build_agencies),
            ("log",       self._build_log),
        ]:
            p = builder()
            p.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._panels[name] = p

    # ── SIDEBAR ────────────────────────────────────────────────────────
    def _build_sidebar(self):
        tk.Label(self._sidebar, text="NAVIGATION", font=("Consolas", 8, "bold"),
                 bg=SURFACE, fg=MUTED, pady=14).pack(fill=tk.X, padx=16)

        nav = [
            ("overview",  "⬛  Overview"),
            ("policies",  "📋  Policies"),
            ("alerts",    "🔔  Alerts"),
            ("billing",   "💲  Billing Rules"),
            ("agencies",  "🏛   Agencies"),
            ("log",       "📜  Audit Log"),
        ]
        self._nav_btns = {}
        for key, label in nav:
            b = tk.Button(self._sidebar, text=label, font=F_NAV,
                          bg=SURFACE, fg=MUTED, activebackground=CARD,
                          activeforeground=ACCENT, relief="flat", bd=0,
                          padx=16, pady=11, anchor="w", cursor="hand2",
                          command=lambda k=key: self._show_tab(k))
            b.pack(fill=tk.X)
            self._nav_btns[key] = b

        # bottom last-refresh label
        tk.Frame(self._sidebar, bg=BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM, pady=(0,4))
        self._refresh_lbl = tk.Label(self._sidebar, text="Last refresh: —",
                                     font=F_SMALL, bg=SURFACE, fg=MUTED, wraplength=170)
        self._refresh_lbl.pack(side=tk.BOTTOM, pady=4, padx=10)

    def _show_tab(self, name):
        self._tab = name
        for k, b in self._nav_btns.items():
            b.configure(bg=CARD if k==name else SURFACE,
                        fg=ACCENT if k==name else MUTED)
        for k, p in self._panels.items():
            p.place_configure(x=-9999 if k!=name else 0)
        self._panels[name].place_configure(relx=0, rely=0, relwidth=1, relheight=1)

    # ═══════════════════════════════════════════════════════════════════
    # PANEL BUILDERS
    # ═══════════════════════════════════════════════════════════════════

    # ── OVERVIEW ───────────────────────────────────────────────────────
    def _build_overview(self):
        p = tk.Frame(self._content, bg=BG)

        tk.Label(p, text="System Overview", font=F_TITLE, bg=BG, fg=TEXT,
                 pady=14, padx=20, anchor="w").pack(fill=tk.X)

        # KPI row
        kpi_row = tk.Frame(p, bg=BG)
        kpi_row.pack(fill=tk.X, padx=20, pady=(0,16))

        self._kpi_vars = {}
        kpis = [
            ("total_policies",  "Total Policies",    TEXT,   "📋"),
            ("completed",       "Processed",         GREEN,  "✓"),
            ("pending",         "Pending",           AMBER,  "⧗"),
            ("blocked",         "Blocked Claims",    RED,    "⛔"),
            ("critical_alerts", "Critical Alerts",   RED,    "🔔"),
            ("total_alerts",    "Open Alerts",       AMBER,  "⚠"),
            ("avg_risk",        "Avg Risk Score",    PURPLE, "◈"),
            ("total_risk_usd",  "Total Risk ($M)",   RED,    "$"),
        ]
        for key, label, color, icon in kpis:
            v = tk.StringVar(value="—")
            self._kpi_vars[key] = v
            self._kpi_card(kpi_row, label, v, color, icon).pack(
                side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        # Middle row: risk breakdown + agency chart
        mid = tk.Frame(p, bg=BG)
        mid.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,16))

        # Risk distribution card
        risk_card = self._card(mid, "Risk Distribution")
        risk_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        self._risk_canvas = tk.Canvas(risk_card, bg=CARD, height=180,
                                      highlightthickness=0, bd=0)
        self._risk_canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Agency breakdown card
        ag_card = self._card(mid, "Agency Breakdown")
        ag_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8,0))
        self._agency_tree = self._make_tree(ag_card,
            cols=[("Agency",60,"w"),("Policies",70,"e"),("Avg Risk",80,"e"),("Loss ($)",100,"e")],
            height=7)
        self._agency_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Recent activity log strip
        log_card = self._card(p, "Live Agent Activity")
        log_card.pack(fill=tk.X, padx=20, pady=(0,16))
        self._mini_log = tk.Text(log_card, height=7, bg=CARD, fg=GREEN,
                                  font=F_LOG, relief="flat", bd=0,
                                  state="disabled", wrap="none")
        self._mini_log.pack(fill=tk.X, padx=10, pady=10)
        self._mini_log.tag_config("ERROR",   foreground=RED)
        self._mini_log.tag_config("WARNING", foreground=AMBER)
        self._mini_log.tag_config("INFO",    foreground=GREEN)

        return p

    def _kpi_card(self, parent, label, var, color, icon):
        f = tk.Frame(parent, bg=CARD, padx=14, pady=14,
                     highlightbackground=BORDER, highlightthickness=1)
        tk.Label(f, text=icon + "  " + label, font=F_KPI_L,
                 bg=CARD, fg=MUTED).pack(anchor="w")
        tk.Label(f, textvariable=var, font=F_KPI_N, bg=CARD, fg=color).pack(anchor="w", pady=(6,0))
        return f

    # ── POLICIES ───────────────────────────────────────────────────────
    def _build_policies(self):
        p = tk.Frame(self._content, bg=BG)
        tk.Label(p, text="Policy Records", font=F_TITLE, bg=BG, fg=TEXT,
                 pady=14, padx=20, anchor="w").pack(fill=tk.X)

        # Filter bar
        fbar = tk.Frame(p, bg=BG)
        fbar.pack(fill=tk.X, padx=20, pady=(0,10))
        tk.Label(fbar, text="Filter:", font=F_BODY, bg=BG, fg=MUTED).pack(side=tk.LEFT)
        self._pol_filter = tk.StringVar(value="ALL")
        for val, label in [("ALL","All"),("CRITICAL_ESCALATE","Critical"),
                           ("HIGH_PRIORITY","High"),("MEDIUM_REVIEW","Medium"),("LOW_MONITOR","Low")]:
            tk.Radiobutton(fbar, text=label, variable=self._pol_filter, value=val,
                           font=F_SMALL, bg=BG, fg=MUTED, selectcolor=CARD,
                           activebackground=BG, activeforeground=ACCENT,
                           command=self._refresh_policies).pack(side=tk.LEFT, padx=8)

        card = self._card(p, "")
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,16))

        cols = [
            ("Policy ID",   90, "w"), ("Date",       90, "center"),
            ("Agency",      55, "center"), ("Type",      140, "w"),
            ("HCPCS",       70, "center"), ("Hospital", 90, "center"),
            ("State",       45, "center"), ("Risk ▼",   70, "e"),
            ("Impact ($)",  110, "e"), ("Scan",        90, "center"),
            ("Workflow",    110, "center"),
        ]
        self._pol_tree = self._make_tree(card, cols, height=28)
        self._pol_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._pol_tree.tag_configure("critical", foreground=RED)
        self._pol_tree.tag_configure("high",     foreground=AMBER)
        self._pol_tree.tag_configure("medium",   foreground=PURPLE)
        self._pol_tree.tag_configure("blocked",  background="#2d1515")
        return p

    # ── ALERTS ─────────────────────────────────────────────────────────
    def _build_alerts(self):
        p = tk.Frame(self._content, bg=BG)
        tk.Label(p, text="Hospital Alerts", font=F_TITLE, bg=BG, fg=TEXT,
                 pady=14, padx=20, anchor="w").pack(fill=tk.X)

        card = self._card(p, "Active Alerts")
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,16))

        cols = [
            ("Alert Type",  120, "center"), ("Policy ID",   90, "w"),
            ("Hospital",     90, "center"), ("State",       50, "center"),
            ("HCPCS",        70, "center"), ("Risk Score",  80, "e"),
            ("Impact ($)",  120, "e"),      ("Timestamp",  130, "center"),
        ]
        self._alert_tree = self._make_tree(card, cols, height=32)
        self._alert_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._alert_tree.tag_configure("CRITICAL",          foreground=RED,    font=F_HEAD)
        self._alert_tree.tag_configure("HIGH",              foreground=AMBER)
        self._alert_tree.tag_configure("BLAST_RADIUS",      foreground=PURPLE)
        self._alert_tree.tag_configure("COMPLIANCE_DEADLINE", foreground=TEAL)
        return p

    # ── BILLING RULES ──────────────────────────────────────────────────
    def _build_billing(self):
        p = tk.Frame(self._content, bg=BG)
        tk.Label(p, text="Billing Code Rules", font=F_TITLE, bg=BG, fg=TEXT,
                 pady=14, padx=20, anchor="w").pack(fill=tk.X)

        card = self._card(p, "Active HCPCS Reimbursement Rules")
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,16))

        cols = [
            ("Hospital",     100, "w"),  ("HCPCS",       80, "center"),
            ("Prev Rate ($)", 110, "e"), ("Curr Rate ($)", 110, "e"),
            ("Change ($)",   100, "e"),  ("Status",      130, "center"),
            ("Policy Ref",    90, "w"),  ("Updated",     130, "center"),
        ]
        self._bill_tree = self._make_tree(card, cols, height=32)
        self._bill_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._bill_tree.tag_configure("BLOCKED",         foreground=RED)
        self._bill_tree.tag_configure("REVIEW_REQUIRED", foreground=AMBER)
        self._bill_tree.tag_configure("ACTIVE",          foreground=GREEN)
        self._bill_tree.tag_configure("neg_change",      foreground=RED)
        self._bill_tree.tag_configure("pos_change",      foreground=GREEN)
        return p

    # ── AGENCIES ───────────────────────────────────────────────────────
    def _build_agencies(self):
        p = tk.Frame(self._content, bg=BG)
        tk.Label(p, text="Agency & HCPCS Analysis", font=F_TITLE, bg=BG, fg=TEXT,
                 pady=14, padx=20, anchor="w").pack(fill=tk.X)

        row = tk.Frame(p, bg=BG)
        row.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,16))

        # Agency table
        ac = self._card(row, "By Agency")
        ac.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        cols_ag = [("Agency",60,"w"),("Total",60,"e"),("Avg Risk",80,"e"),
                   ("Compliance",90,"e"),("Total Loss ($M)",110,"e")]
        self._ag_tree = self._make_tree(ac, cols_ag, height=20)
        self._ag_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # HCPCS table
        hc = self._card(row, "Top HCPCS by Risk")
        hc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cols_hc = [("HCPCS",70,"w"),("Policies",70,"e"),("Avg Risk",80,"e"),
                   ("Total Impact ($)",120,"e"),("Blocked",70,"e")]
        self._hc_tree = self._make_tree(hc, cols_hc, height=20)
        self._hc_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # State distribution
        sc = self._card(p, "Policy Count by Hospital State")
        sc.pack(fill=tk.X, padx=20, pady=(0,16))
        self._state_canvas = tk.Canvas(sc, bg=CARD, height=110, highlightthickness=0)
        self._state_canvas.pack(fill=tk.X, padx=12, pady=12)
        return p

    # ── AUDIT LOG ──────────────────────────────────────────────────────
    def _build_log(self):
        p = tk.Frame(self._content, bg=BG)
        tk.Label(p, text="Agent Execution Log", font=F_TITLE, bg=BG, fg=TEXT,
                 pady=14, padx=20, anchor="w").pack(fill=tk.X)

        # Live log box
        live_card = self._card(p, "Live Agent Output")
        live_card.pack(fill=tk.X, padx=20, pady=(0,10))
        log_frame = tk.Frame(live_card, bg=CARD)
        log_frame.pack(fill=tk.X, padx=10, pady=10)
        self._live_log = tk.Text(log_frame, height=10, bg="#0a0e13", fg=GREEN,
                                  font=F_LOG, relief="flat", bd=0,
                                  state="disabled", wrap="none")
        sb = ttk.Scrollbar(log_frame, orient="vertical", command=self._live_log.yview)
        self._live_log.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._live_log.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._live_log.tag_config("ERROR",   foreground=RED)
        self._live_log.tag_config("WARNING", foreground=AMBER)
        self._live_log.tag_config("INFO",    foreground=GREEN)

        # DB audit table
        db_card = self._card(p, "Database Audit Trail")
        db_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,16))
        cols = [("Agent",60,"center"),("Action",110,"center"),("Policy ID",90,"w"),
                ("Hospital",90,"center"),("Status",70,"center"),("Duration",80,"e"),
                ("Timestamp",130,"center")]
        self._log_tree = self._make_tree(db_card, cols, height=18)
        self._log_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._log_tree.tag_configure("SUCCESS", foreground=GREEN)
        self._log_tree.tag_configure("FAILED",  foreground=RED)
        self._log_tree.tag_configure("SKIPPED", foreground=MUTED)
        return p

    # ── SHARED WIDGETS ──────────────────────────────────────────────────
    def _card(self, parent, title):
        outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        if title:
            tk.Label(outer, text=title, font=F_HEAD, bg=HEADER, fg=MUTED,
                     padx=14, pady=8, anchor="w").pack(fill=tk.X)
            tk.Frame(outer, bg=BORDER, height=1).pack(fill=tk.X)
        return outer

    def _make_tree(self, parent, cols, height=10):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(fill=tk.BOTH, expand=True)
        cols_ids = [c[0] for c in cols]
        tree = ttk.Treeview(frame, columns=cols_ids, show="headings",
                            height=height, style="Treeview")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for col_id, width, anchor in cols:
            tree.heading(col_id, text=col_id)
            tree.column(col_id, width=width, anchor=anchor, minwidth=40)
        tree.tag_configure("oddrow",  background=ROW_ODD)
        tree.tag_configure("evenrow", background=ROW_EVEN)
        return tree

    # ══════════════════════════════════════════════════════════════════
    # DATA REFRESH
    # ══════════════════════════════════════════════════════════════════
    def _refresh(self):
        self._status_var.set("● REFRESHING...")
        def _do():
            self._refresh_kpis()
            self._refresh_policies()
            self._refresh_alerts()
            self._refresh_billing()
            self._refresh_agencies()
            self._refresh_log()
            self._refresh_live_log()
            self._refresh_risk_chart()
            self._refresh_state_chart()
            now = datetime.now().strftime("%H:%M:%S")
            self._refresh_lbl.configure(text=f"Last refresh: {now}")
            self._status_var.set("● LIVE")
        threading.Thread(target=_do, daemon=True).start()

    def _schedule(self):
        self._refresh()
        self.after(30000, self._schedule)   # auto every 30 s

    # ── KPIs ───────────────────────────────────────────────────────────
    def _refresh_kpis(self):
        total   = qs("SELECT COUNT(*) FROM policies")
        done    = qs("SELECT COUNT(*) FROM policies WHERE scan_status='COMPLETED'")
        pend    = qs("SELECT COUNT(*) FROM policies WHERE scan_status='PENDING'")
        blocked = qs("SELECT COUNT(*) FROM policies WHERE workflow_status='BLOCKED'")
        crit    = qs("SELECT COUNT(*) FROM hospital_alerts WHERE alert_type='CRITICAL' AND resolved=0")
        alerts  = qs("SELECT COUNT(*) FROM hospital_alerts WHERE resolved=0")
        avg_r   = qs("SELECT ROUND(AVG(claim_rejection_risk_score),3) FROM policies") or 0
        t_risk  = qs("SELECT COALESCE(SUM(ABS(estimated_financial_impact_usd)),0) "
                     "FROM policies WHERE estimated_financial_impact_usd<0") or 0

        self._kpi_vars["total_policies"].set(f"{total:,}")
        self._kpi_vars["completed"].set(f"{done:,}")
        self._kpi_vars["pending"].set(f"{pend:,}")
        self._kpi_vars["blocked"].set(f"{blocked:,}")
        self._kpi_vars["critical_alerts"].set(f"{crit:,}")
        self._kpi_vars["total_alerts"].set(f"{alerts:,}")
        self._kpi_vars["avg_risk"].set(f"{float(avg_r):.3f}")
        self._kpi_vars["total_risk_usd"].set(f"${float(t_risk)/1_000_000:.2f}M")

    # ── POLICIES TABLE ──────────────────────────────────────────────────
    def _refresh_policies(self):
        rows = q("""SELECT policy_id, policy_date, agency, policy_type,
                           affected_hcpcs_code, hospital_id, hospital_state,
                           claim_rejection_risk_score, estimated_financial_impact_usd,
                           scan_status, workflow_status, agent1_notes
                    FROM policies
                    ORDER BY claim_rejection_risk_score DESC, updated_at DESC
                    LIMIT 500""")
        self._pol_tree.delete(*self._pol_tree.get_children())
        filt = self._pol_filter.get()
        for i, r in enumerate(rows):
            if "__error__" in r: continue
            notes = r.get("agent1_notes") or ""
            action = ""
            if '"action_class"' in notes:
                try:
                    import json as _j
                    action = _j.loads(notes).get("action_class","")
                except: pass
            if filt != "ALL" and action != filt: continue

            rs   = float(r.get("claim_rejection_risk_score") or 0)
            imp  = float(r.get("estimated_financial_impact_usd") or 0)
            wf   = r.get("workflow_status","")
            tag  = ("evenrow" if i%2==0 else "oddrow")
            if rs >= 0.70:   tag = "critical"
            elif rs >= 0.50: tag = "high"
            elif rs >= 0.30: tag = "medium"
            if wf == "BLOCKED": tag = "blocked"

            self._pol_tree.insert("", "end", tags=(tag,), values=(
                r.get("policy_id",""),
                str(r.get("policy_date",""))[:10],
                r.get("agency",""),
                r.get("policy_type",""),
                r.get("affected_hcpcs_code",""),
                r.get("hospital_id",""),
                r.get("hospital_state",""),
                f"{rs:.3f}",
                f"${imp:,.0f}",
                r.get("scan_status",""),
                wf,
            ))

    # ── ALERTS TABLE ───────────────────────────────────────────────────
    def _refresh_alerts(self):
        rows = q("""SELECT alert_type, policy_id, hospital_id, hospital_state,
                           hcpcs_code, risk_score, financial_impact, created_at
                    FROM hospital_alerts WHERE resolved=0
                    ORDER BY created_at DESC LIMIT 200""")
        self._alert_tree.delete(*self._alert_tree.get_children())
        for r in rows:
            if "__error__" in r: continue
            atype = r.get("alert_type","")
            rs    = float(r.get("risk_score") or 0)
            imp   = float(r.get("financial_impact") or 0)
            self._alert_tree.insert("", "end", tags=(atype,), values=(
                atype,
                r.get("policy_id",""),
                r.get("hospital_id",""),
                r.get("hospital_state",""),
                r.get("hcpcs_code",""),
                f"{rs:.3f}",
                f"${imp:,.0f}",
                r.get("created_at",""),
            ))

    # ── BILLING TABLE ──────────────────────────────────────────────────
    def _refresh_billing(self):
        rows = q("""SELECT hospital_id, hcpcs_code, previous_rate_usd, current_rate_usd,
                           workflow_status, last_policy_id, updated_at
                    FROM billing_code_rules ORDER BY updated_at DESC LIMIT 200""")
        self._bill_tree.delete(*self._bill_tree.get_children())
        for r in rows:
            if "__error__" in r: continue
            prev = float(r.get("previous_rate_usd") or 0)
            curr = float(r.get("current_rate_usd")  or 0)
            diff = curr - prev
            ws   = r.get("workflow_status","")
            tag  = ws if ws in ("BLOCKED","REVIEW_REQUIRED","ACTIVE") else "oddrow"
            diff_tag = "neg_change" if diff < 0 else "pos_change"
            self._bill_tree.insert("", "end", tags=(tag,), values=(
                r.get("hospital_id",""), r.get("hcpcs_code",""),
                f"${prev:,.2f}", f"${curr:,.2f}",
                f"{'+'if diff>=0 else ''}${diff:,.2f}",
                ws, r.get("last_policy_id",""), r.get("updated_at",""),
            ))

    # ── AGENCIES & HCPCS ───────────────────────────────────────────────
    def _refresh_agencies(self):
        ag = q("""SELECT agency, COUNT(*) total, ROUND(AVG(claim_rejection_risk_score),3) avg_risk,
                         SUM(CASE WHEN policy_type='Compliance Requirement' THEN 1 ELSE 0 END) compliance,
                         ROUND(SUM(CASE WHEN estimated_financial_impact_usd<0
                               THEN ABS(estimated_financial_impact_usd) ELSE 0 END)/1000000,2) loss_m
                  FROM policies GROUP BY agency ORDER BY avg_risk DESC""")
        self._ag_tree.delete(*self._ag_tree.get_children())
        for i, r in enumerate(ag):
            if "__error__" in r: continue
            self._ag_tree.insert("","end",tags=("evenrow"if i%2==0 else"oddrow",),values=(
                r["agency"], r["total"], r["avg_risk"],
                r["compliance"], f"${r['loss_m']}M"
            ))
        # also refresh overview agency tree
        self._agency_tree.delete(*self._agency_tree.get_children())
        for i, r in enumerate(ag):
            if "__error__" in r: continue
            self._agency_tree.insert("","end",tags=("evenrow"if i%2==0 else"oddrow",),values=(
                r["agency"], r["total"], r["avg_risk"], f"${r['loss_m']}M"
            ))

        hc = q("""SELECT affected_hcpcs_code hcpcs, COUNT(*) policies,
                         ROUND(AVG(claim_rejection_risk_score),3) avg_risk,
                         ROUND(SUM(estimated_financial_impact_usd),0) total_impact,
                         SUM(CASE WHEN workflow_status='BLOCKED' THEN 1 ELSE 0 END) blocked
                  FROM policies GROUP BY affected_hcpcs_code
                  ORDER BY avg_risk DESC LIMIT 15""")
        self._hc_tree.delete(*self._hc_tree.get_children())
        for i, r in enumerate(hc):
            if "__error__" in r: continue
            imp = float(r.get("total_impact") or 0)
            self._hc_tree.insert("","end",tags=("evenrow"if i%2==0 else"oddrow",),values=(
                r["hcpcs"], r["policies"], r["avg_risk"],
                f"${imp:,.0f}", r.get("blocked","0")
            ))

    # ── AUDIT LOG ──────────────────────────────────────────────────────
    def _refresh_log(self):
        rows = q("""SELECT agent, action, policy_id, hospital_id,
                           status, duration_ms, executed_at
                    FROM agent_execution_log ORDER BY executed_at DESC LIMIT 200""")
        self._log_tree.delete(*self._log_tree.get_children())
        for r in rows:
            if "__error__" in r: continue
            st  = r.get("status","")
            ms  = r.get("duration_ms","")
            self._log_tree.insert("","end",tags=(st,),values=(
                r.get("agent",""), r.get("action",""), r.get("policy_id",""),
                r.get("hospital_id",""), st,
                f"{ms}ms" if ms else "—",
                r.get("executed_at",""),
            ))

    # ── LIVE LOG ───────────────────────────────────────────────────────
    def _refresh_live_log(self):
        try:
            from agents.agent1_scanner import get_log_buffer
            buf = get_log_buffer()
        except: buf = []
        for widget in (self._mini_log, self._live_log):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            for entry in buf[-60:]:
                lv  = entry.get("level","INFO")
                msg = f"[{entry['ts']}] {entry['msg']}\n"
                widget.insert("end", msg, lv)
            widget.configure(state="disabled")
            widget.see("end")

    # ── RISK DISTRIBUTION CHART (canvas bar chart) ─────────────────────
    def _refresh_risk_chart(self):
        r = q("""SELECT
            SUM(CASE WHEN claim_rejection_risk_score>=0.70 THEN 1 ELSE 0 END) critical,
            SUM(CASE WHEN claim_rejection_risk_score>=0.50 AND claim_rejection_risk_score<0.70 THEN 1 ELSE 0 END) high,
            SUM(CASE WHEN claim_rejection_risk_score>=0.30 AND claim_rejection_risk_score<0.50 THEN 1 ELSE 0 END) medium,
            SUM(CASE WHEN claim_rejection_risk_score<0.30 THEN 1 ELSE 0 END) low_risk
        FROM policies""")
        if not r or "__error__" in r[0]: return
        d   = r[0]
        vals = [
            ("Critical ≥0.70", int(d.get("critical") or 0),  RED),
            ("High ≥0.50",     int(d.get("high")     or 0),  AMBER),
            ("Medium ≥0.30",   int(d.get("medium")   or 0),  PURPLE),
            ("Low <0.30",      int(d.get("low_risk")  or 0),  GREEN),
        ]
        c = self._risk_canvas
        c.delete("all")
        self.update_idletasks()
        W = c.winfo_width()  or 400
        H = c.winfo_height() or 180
        total = sum(v for _,v,_ in vals) or 1
        bar_h = 28; gap = 14; x0 = 120; max_w = W - x0 - 60
        for i, (label, val, color) in enumerate(vals):
            y = 20 + i*(bar_h+gap)
            w = int(val / total * max_w)
            c.create_text(x0-8, y+bar_h//2, text=label, fill=MUTED,
                          font=F_SMALL, anchor="e")
            if w > 0:
                c.create_rectangle(x0, y, x0+w, y+bar_h, fill=color, outline="")
            c.create_text(x0+w+6, y+bar_h//2, text=f"{val:,}",
                          fill=TEXT, font=F_SMALL, anchor="w")

    # ── STATE BAR CHART ────────────────────────────────────────────────
    def _refresh_state_chart(self):
        rows = q("""SELECT hospital_state, COUNT(*) cnt FROM policies
                    GROUP BY hospital_state ORDER BY cnt DESC LIMIT 15""")
        if not rows or "__error__" in rows[0]: return
        c = self._state_canvas
        c.delete("all")
        self.update_idletasks()
        W = c.winfo_width() or 800
        H = c.winfo_height() or 110
        n = len(rows)
        if n == 0: return
        total = max(r["cnt"] for r in rows) or 1
        bw    = max(int((W - 40) / n) - 4, 10)
        max_h = H - 40
        colors = [ACCENT, TEAL, GREEN, PURPLE, AMBER]
        for i, r in enumerate(rows):
            x   = 20 + i * (bw + 4)
            bh  = int(r["cnt"] / total * max_h)
            y1  = H - 24 - bh; y2 = H - 24
            cl  = colors[i % len(colors)]
            c.create_rectangle(x, y1, x+bw, y2, fill=cl, outline="")
            c.create_text(x+bw//2, H-12, text=r["hospital_state"],
                          fill=MUTED, font=("Consolas",8), anchor="center")
            c.create_text(x+bw//2, y1-4, text=str(r["cnt"]),
                          fill=TEXT, font=("Consolas",8), anchor="s")

    # ══════════════════════════════════════════════════════════════════
    # AGENT CONTROLS
    # ══════════════════════════════════════════════════════════════════
    def _run_agent1(self):
        if self._agent_running:
            return
        self._agent_running = True
        self._status_var.set("● AGENT 1 RUNNING...")
        def _do():
            try:
                from agents.agent1_scanner import run_scan_cycle
                run_scan_cycle()
            except Exception as e:
                _log_import = lambda m: None
                try:
                    from agents.agent1_scanner import _log
                    _log("ERROR", f"[DASHBOARD] Agent1 error: {e}")
                except: pass
            finally:
                self._agent_running = False
                self._status_var.set("● LIVE")
                self._refresh()
        threading.Thread(target=_do, daemon=True).start()

    def _run_monitor(self):
        self._status_var.set("● AGENT 2 MONITORING...")
        def _do():
            try:
                from agents.agent2_executor import monitor_claim_rejections
                monitor_claim_rejections()
            except Exception as e:
                try:
                    from agents.agent1_scanner import _log
                    _log("ERROR", f"[DASHBOARD] Monitor error: {e}")
                except: pass
            finally:
                self._status_var.set("● LIVE")
                self._refresh()
        threading.Thread(target=_do, daemon=True).start()


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()
