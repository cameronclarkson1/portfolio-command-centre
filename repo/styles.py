"""styles.py — AI HedgeFund global CSS."""

CSS = """
[data-testid="stSidebarNav"] { display: none; }

/* ── TOP NAV: HIDE SIDEBAR, EXPAND MAIN ── */
[data-testid="stSidebar"]              { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="stMain"] { margin-left: 0 !important; width: 100% !important; }

/* ── TOP NAV BAR ── */
.tn-brand {
    background: linear-gradient(135deg, #07111F 0%, #0B1628 100%);
    margin: 0 -2.5rem;
    padding: 13px 2.5rem 12px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    display: flex; align-items: center; justify-content: space-between;
}
.tn-logo-box {
    background: linear-gradient(135deg, #1D4ED8 0%, #7C3AED 100%);
    border-radius: 10px; width: 34px; height: 34px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.tn-name    { font-size: 16px; font-weight: 800; color: #F1F5F9; letter-spacing: -0.02em; line-height: 1.2; }
.tn-tagline { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 1px; }
.tn-meta    { display: flex; align-items: center; gap: 14px; }
.tn-date    { font-size: 12px; color: #64748B; }
.tn-live-open   { background: rgba(22,163,74,0.15); color: #16A34A; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; border: 1px solid rgba(22,163,74,0.3); }
.tn-live-closed { background: rgba(220,38,38,0.12); color: #DC2626; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; border: 1px solid rgba(220,38,38,0.25); }

/* ── TOP NAV BUTTON ROW ── */
/* Target the 3rd div child of block-container (after CSS injection div + brand bar div) */
.block-container > div:nth-child(3) {
    background: #07111F;
    margin: 0 -2.5rem;
    padding: 0 2.5rem;
}
.block-container > div:nth-child(3) .stButton { margin-bottom: 0 !important; }
.block-container > div:nth-child(3) .stButton > button {
    background: transparent !important; border: none !important;
    border-radius: 0 !important; border-bottom: 2px solid transparent !important;
    color: rgba(248,250,252,0.6) !important; font-size: 13px !important;
    font-weight: 500 !important; padding: 10px 4px 12px !important;
    box-shadow: none !important; letter-spacing: 0.01em !important;
    transition: color 0.15s, border-bottom-color 0.15s !important;
}
.block-container > div:nth-child(3) .stButton > button:hover {
    color: #ffffff !important; background: transparent !important;
    border-bottom-color: rgba(255,255,255,0.25) !important;
}
.block-container > div:nth-child(3) .stButton > button[kind="primary"] {
    color: #ffffff !important; font-weight: 700 !important;
    background: transparent !important;
    border-bottom: 2px solid #2563EB !important;
}
.block-container > div:nth-child(3) .stButton > button[kind="primary"]:hover {
    border-bottom-color: #3B82F6 !important;
}
.block-container > div:nth-child(3) .stButton > button p,
.block-container > div:nth-child(3) .stButton > button span { color: inherit !important; }

/* ── NAV DIVIDER ── */
.tn-divider { height: 1px; background: #E2E8F0; margin: 0 0 24px; }

/* ── DASHBOARD PAGE ── */
.db-page-title { font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.03em; }
.db-page-sub   { font-size: 13px; color: #64748B; margin-top: 4px; }

.db-card {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px;
    padding: 20px; height: 100%;
    box-shadow: 0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04);
}
.db-card-title {
    font-size: 13px; font-weight: 700; color: #0F172A;
    margin-bottom: 14px; padding-bottom: 10px;
    border-bottom: 1px solid #F1F5F9;
    display: flex; align-items: center; gap: 6px;
}
.db-card-sub { font-size: 11px; color: #64748B; font-weight: 400; margin-left: 4px; }

.db-row { display: flex; align-items: center; padding: 9px 0; border-bottom: 1px solid #F8FAFC; }
.db-row:last-child { border-bottom: none; }

/* Regime banner (premium) */
.db-regime {
    border-radius: 16px; padding: 18px 22px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 16px; border: 1px solid;
}
.db-regime-risk-on  { background: #F0FDF4; border-color: #86EFAC; }
.db-regime-neutral  { background: #FEFCE8; border-color: #FDE047; }
.db-regime-risk-off { background: #FFF7ED; border-color: #FED7AA; }
.db-regime-crisis   { background: #FEF2F2; border-color: #FCA5A5; }
.db-regime-icon { font-size: 32px; flex-shrink: 0; }
.db-regime-body { flex: 1; min-width: 0; }
.db-regime-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px; opacity: 0.7; }
.db-regime-title { font-size: 18px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 4px; }
.db-regime-meta  { font-size: 13px; opacity: 0.8; }
.db-regime-right { flex-shrink: 0; text-align: right; }
.db-regime-risk-on  .db-regime-title { color: #14532D; }
.db-regime-neutral  .db-regime-title { color: #713F12; }
.db-regime-risk-off .db-regime-title { color: #7C2D12; }
.db-regime-crisis   .db-regime-title { color: #7F1D1D; }
.db-regime-risk-on  .db-regime-meta  { color: #166534; }
.db-regime-neutral  .db-regime-meta  { color: #854D0E; }
.db-regime-risk-off .db-regime-meta  { color: #9A3412; }
.db-regime-crisis   .db-regime-meta  { color: #991B1B; }
.db-regime-risk-on  .db-regime-label { color: #15803D; }
.db-regime-neutral  .db-regime-label { color: #A16207; }
.db-regime-risk-off .db-regime-label { color: #C2410C; }
.db-regime-crisis   .db-regime-label { color: #B91C1C; }

/* Market overview rows */
.db-mkt-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 0; border-bottom: 1px solid #F8FAFC; font-size: 13px;
}
.db-mkt-row:last-child { border-bottom: none; }
.db-mkt-name { font-weight: 600; color: #0F172A; }
.db-mkt-val  { color: #0F172A; font-weight: 600; min-width: 70px; text-align: right; }
.db-chg-pos  { background: #DCFCE7; color: #16A34A; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px; min-width: 64px; text-align: center; }
.db-chg-neg  { background: #FEE2E2; color: #DC2626; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px; min-width: 64px; text-align: center; }
.db-chg-neu  { background: #F1F5F9; color: #64748B; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px; min-width: 64px; text-align: center; }

/* Intelligence feed items */
.db-intel-item {
    padding: 12px 0; border-bottom: 1px solid #F1F5F9;
}
.db-intel-item:last-child { border-bottom: none; }
.db-intel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; flex-wrap: wrap; }
.db-intel-ticker { font-size: 12px; font-weight: 700; color: #0F172A; }
.db-intel-summary { font-size: 12px; color: #475569; line-height: 1.5; }

/* Decision / opp / alert placeholder */
.db-empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px 16px; text-align: center;
}
.db-empty-icon  { font-size: 28px; margin-bottom: 8px; opacity: 0.4; }
.db-empty-title { font-size: 13px; font-weight: 600; color: #64748B; margin-bottom: 4px; }
.db-empty-sub   { font-size: 12px; color: #94A3B8; line-height: 1.5; }

/* Decision rows */
.db-decision-row {
    display: flex; align-items: flex-start; padding: 10px 0;
    border-bottom: 1px solid #F8FAFC; gap: 10px;
}
.db-decision-row:last-child { border-bottom: none; }
.db-d-ticker { font-size: 13px; font-weight: 700; color: #0F172A; min-width: 44px; }
.db-d-name   { font-size: 11px; color: #64748B; margin-top: 1px; }
.db-d-reason { font-size: 12px; color: #475569; line-height: 1.45; flex: 1; }

/* Holdings rows */
.db-holding-row { display: flex; align-items: center; padding: 9px 0; border-bottom: 1px solid #F8FAFC; }
.db-holding-row:last-child { border-bottom: none; }
.db-h-circle { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #fff; flex-shrink: 0; }
.db-h-ticker { font-size: 13px; font-weight: 700; color: #0F172A; }
.db-h-sector { font-size: 11px; color: #64748B; }
.db-h-weight { font-size: 13px; font-weight: 600; color: #0F172A; }
.db-h-pnl-pos { font-size: 11px; color: #16A34A; font-weight: 600; }
.db-h-pnl-neg { font-size: 11px; color: #DC2626; font-weight: 600; }

.stApp {
    background-color: #F5F7FA;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.block-container {
    padding: 1.5rem 2.5rem 3rem 2.5rem !important;
    max-width: 100% !important;
}
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
hr { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020B18 0%, #061A33 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.04) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #94a3b8 !important; }

/* Nav group labels (RESEARCH, MARKET, etc.) */
.pcc-nav-group {
    font-size: 9px !important; font-weight: 700 !important;
    color: #334155 !important; text-transform: uppercase;
    letter-spacing: 0.10em; padding: 6px 16px 4px 16px;
    pointer-events: none;
}

/* Sidebar nav buttons — override global button styles */
[data-testid="stSidebar"] .stButton { margin-bottom: 0 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 9px 14px !important;
    line-height: 1.4 !important;
    letter-spacing: 0 !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    color: #f1f5f9 !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(255,255,255,0.10) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: rgba(255,255,255,0.14) !important;
}
/* Ensure button text inherits the button element's color */
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div { color: inherit !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important; font-size: 17px !important; font-weight: 700 !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: #475569 !important; font-size: 10px !important;
}
[data-testid="stSidebar"] [data-testid="metric-container"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 9px !important;
    padding: 10px 14px !important;
}

/* ── NATIVE STREAMLIT OVERRIDES ── */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.03);
    transition: box-shadow 0.15s ease;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important; font-weight: 600 !important;
    color: #5B6472 !important; text-transform: uppercase; letter-spacing: 0.06em;
}
[data-testid="stMetricValue"] {
    font-size: 24px !important; font-weight: 700 !important;
    color: #0B0B0F !important; letter-spacing: -0.02em;
}
[data-testid="stDataFrame"] {
    border-radius: 10px; overflow: hidden;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stButton > button {
    border-radius: 8px; font-size: 13px; font-weight: 500;
    border: 1px solid #E2E8F0; color: #374151; background: #F5F7FA;
    transition: all 0.15s ease; padding: 6px 16px; letter-spacing: 0.01em;
}
.stButton > button:hover {
    border-color: #061A33; color: #061A33; background: #F5F7FA;
    box-shadow: 0 0 0 3px rgba(6,26,51,0.08);
}
.stButton > button[kind="primary"] {
    background: #061A33; color: #ffffff; border: none;
}
.stButton > button[kind="primary"]:hover {
    background: #102A4C; box-shadow: 0 0 0 3px rgba(6,26,51,0.2);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #F5F7FA; padding: 5px;
    border-radius: 12px; border: 1px solid #E2E8F0;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; padding: 7px 20px; font-size: 13px;
    font-weight: 500; color: #5B6472; background: transparent;
    border: none; letter-spacing: 0.01em;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important; color: #0B0B0F !important;
    font-weight: 600 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.09);
}
[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important; border-radius: 12px !important;
    background: #FFFFFF !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    overflow: hidden; margin-bottom: 6px;
}
[data-testid="stExpander"] summary {
    font-weight: 500; font-size: 14px; color: #374151;
    padding: 13px 18px !important; background: #FFFFFF;
}
[data-testid="stExpander"] summary:hover { background: #F5F7FA !important; }
.stSelectbox > div > div,
.stTextInput > div > div,
.stNumberInput > div > div {
    border-radius: 8px !important; border: 1px solid #E2E8F0 !important;
    background: #FFFFFF !important; font-size: 13px; color: #0B0B0F !important;
}
.stAlert { border-radius: 10px !important; }
.stSpinner > div {
    border-color: #061A33 transparent transparent transparent !important;
}
.stCaption { color: #94a3b8 !important; font-size: 12px !important; }

/* ── PCC CUSTOM COMPONENTS ── */
.pcc-page-header {
    display: flex; align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #E2E8F0;
}
.pcc-page-title { font-size: 22px; font-weight: 700; color: #0B0B0F; letter-spacing: -0.02em; line-height: 1.2; }
.pcc-page-subtitle { font-size: 13px; color: #5B6472; margin-top: 3px; }
.pcc-page-meta { text-align: right; font-size: 11px; color: #94a3b8; margin-top: 4px; }

.pcc-section-header { margin-bottom: 14px; margin-top: 4px; }
.pcc-section-title {
    font-size: 14px; font-weight: 700; color: #0B0B0F;
    display: flex; align-items: center; gap: 7px; letter-spacing: -0.01em;
}
.pcc-section-subtitle { font-size: 12px; color: #94a3b8; margin-top: 2px; }

.pcc-card {
    background: #FFFFFF; border-radius: 12px; padding: 20px 22px;
    border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 16px;
}
.pcc-metric {
    background: #FFFFFF; border-radius: 12px; padding: 18px 20px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 6px rgba(0,0,0,0.03);
    height: 100%; position: relative; overflow: hidden; transition: box-shadow 0.15s ease;
}
.pcc-metric:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
}
.pcc-metric-accent {
    position: absolute; top: 0; left: 0; right: 0;
    height: 3px; background: #061A33; border-radius: 12px 12px 0 0;
}
.pcc-metric-icon { font-size: 17px; margin-bottom: 8px; display: block; }
.pcc-metric-label {
    font-size: 10px; color: #5B6472; text-transform: uppercase;
    letter-spacing: 0.07em; font-weight: 600; margin-bottom: 6px;
}
.pcc-metric-value {
    font-size: 22px; font-weight: 700; color: #0B0B0F;
    letter-spacing: -0.025em; line-height: 1.1;
}
.pcc-metric-delta { font-size: 11px; font-weight: 500; margin-top: 5px; display: flex; align-items: center; gap: 3px; }
.pcc-delta-pos  { color: #16A34A; }
.pcc-delta-neg  { color: #DC2626; }
.pcc-delta-neu  { color: #5B6472; }
.pcc-delta-warn { color: #B45309; }

.pcc-badge {
    display: inline-flex; align-items: center; padding: 2px 9px;
    border-radius: 20px; font-size: 10px; font-weight: 700;
    letter-spacing: 0.04em; text-transform: uppercase; white-space: nowrap;
}
.pcc-badge-buy      { background: #dcfce7; color: #15803d; }
.pcc-badge-add      { background: #dbeafe; color: #1d4ed8; }
.pcc-badge-hold     { background: #f3f4f6; color: #374151; }
.pcc-badge-watch    { background: #fef9c3; color: #92400e; }
.pcc-badge-trim     { background: #ffedd5; color: #9a3412; }
.pcc-badge-sell     { background: #fee2e2; color: #991b1b; }
.pcc-badge-avoid    { background: #f3f4f6; color: #6b7280; }
.pcc-badge-manual   { background: #ede9fe; color: #5b21b6; }
.pcc-badge-risk-on  { background: #dcfce7; color: #15803d; }
.pcc-badge-neutral  { background: #fef9c3; color: #92400e; }
.pcc-badge-risk-off { background: #ffedd5; color: #9a3412; }
.pcc-badge-crisis   { background: #fee2e2; color: #991b1b; }
.pcc-badge-positive { background: #dcfce7; color: #15803d; }
.pcc-badge-negative { background: #fee2e2; color: #991b1b; }
.pcc-badge-mixed    { background: #fef9c3; color: #92400e; }
.pcc-badge-intact   { background: #dcfce7; color: #15803d; }
.pcc-badge-weakening{ background: #fef9c3; color: #92400e; }
.pcc-badge-broken   { background: #fee2e2; color: #991b1b; }
.pcc-badge-info     { background: #dbeafe; color: #1d4ed8; }
.pcc-badge-warning  { background: #fef9c3; color: #92400e; }
.pcc-badge-critical { background: #fee2e2; color: #991b1b; }
.pcc-badge-high     { background: #dcfce7; color: #15803d; }
.pcc-badge-medium   { background: #fef9c3; color: #92400e; }
.pcc-badge-low      { background: #f3f4f6; color: #6b7280; }
.pcc-badge-complete { background: #dcfce7; color: #15803d; }
.pcc-badge-planned  { background: #f3f4f6; color: #374151; }

.pcc-decision {
    background: #FFFFFF; border-radius: 10px; padding: 13px 16px;
    border: 1px solid #E2E8F0; border-left: 4px solid #E2E8F0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04); margin-bottom: 8px;
    transition: box-shadow 0.15s ease;
}
.pcc-decision:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.08); }
.pcc-decision-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; flex-wrap: wrap; }
.pcc-decision-ticker { font-size: 13px; font-weight: 700; color: #0B0B0F; }
.pcc-decision-name   { font-size: 12px; color: #5B6472; }
.pcc-decision-score  { font-size: 11px; color: #94a3b8; margin-left: auto; }
.pcc-decision-reason { font-size: 12px; color: #374151; line-height: 1.5; margin-top: 3px; }

.pcc-alert {
    border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
    border: 1px solid; display: flex; align-items: flex-start; gap: 10px;
}
.pcc-alert-info     { background: #eff6ff; border-color: #bfdbfe; }
.pcc-alert-warning  { background: #fffbeb; border-color: #fde68a; }
.pcc-alert-critical { background: #fef2f2; border-color: #fecaca; }
.pcc-alert-icon { font-size: 14px; margin-top: 1px; flex-shrink: 0; line-height: 1.5; }
.pcc-alert-body { flex: 1; }
.pcc-alert-message { font-size: 13px; color: #1f2937; line-height: 1.45; }
.pcc-alert-action  { font-size: 11px; font-weight: 600; margin-top: 3px; }
.pcc-alert-action-info     { color: #1d4ed8; }
.pcc-alert-action-warning  { color: #b45309; }
.pcc-alert-action-critical { color: #991b1b; }

.pcc-regime {
    border-radius: 12px; padding: 14px 18px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 14px; border: 1px solid;
}
.pcc-regime-icon   { font-size: 26px; flex-shrink: 0; }
.pcc-regime-body   { flex: 1; min-width: 0; }
.pcc-regime-title  { font-size: 14px; font-weight: 700; margin-bottom: 3px; }
.pcc-regime-detail { font-size: 12px; opacity: 0.75; line-height: 1.4; }
.pcc-regime-badge  { flex-shrink: 0; }
.pcc-regime-risk-on  { background: #f0fdf4; border-color: #86efac; }
.pcc-regime-neutral  { background: #fefce8; border-color: #fde047; }
.pcc-regime-risk-off { background: #fff7ed; border-color: #fed7aa; }
.pcc-regime-crisis   { background: #fef2f2; border-color: #fca5a5; }
.pcc-regime-risk-on  .pcc-regime-title  { color: #14532d; }
.pcc-regime-neutral  .pcc-regime-title  { color: #713f12; }
.pcc-regime-risk-off .pcc-regime-title  { color: #7c2d12; }
.pcc-regime-crisis   .pcc-regime-title  { color: #7f1d1d; }
.pcc-regime-risk-on  .pcc-regime-detail { color: #166534; }
.pcc-regime-neutral  .pcc-regime-detail { color: #854d0e; }
.pcc-regime-risk-off .pcc-regime-detail { color: #9a3412; }
.pcc-regime-crisis   .pcc-regime-detail { color: #991b1b; }

.pcc-score-wrap { margin-bottom: 10px; }
.pcc-score-label-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
.pcc-score-label { font-size: 12px; color: #5B6472; }
.pcc-score-num   { font-size: 12px; font-weight: 600; }
.pcc-score-num-green { color: #16A34A; }
.pcc-score-num-amber { color: #B45309; }
.pcc-score-num-red   { color: #DC2626; }
.pcc-score-bar  { height: 5px; border-radius: 3px; background: #E2E8F0; overflow: hidden; }
.pcc-score-fill { height: 100%; border-radius: 3px; }
.pcc-score-fill-green { background: #16A34A; }
.pcc-score-fill-amber { background: #B45309; }
.pcc-score-fill-red   { background: #DC2626; }

.pcc-opp-item {
    display: flex; align-items: center; padding: 10px 14px;
    border-radius: 9px; border: 1px solid #E2E8F0; background: #FFFFFF;
    margin-bottom: 6px; gap: 12px; transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.pcc-opp-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.07); border-color: #d1d5db; }
.pcc-opp-rank   { font-size: 11px; color: #d1d5db; font-weight: 700; width: 18px; flex-shrink: 0; }
.pcc-opp-ticker { font-size: 13px; font-weight: 700; color: #0B0B0F; min-width: 52px; }
.pcc-opp-name   { font-size: 12px; color: #5B6472; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pcc-opp-price  { font-size: 13px; font-weight: 600; color: #374151; }
.pcc-opp-up-pos { font-size: 12px; font-weight: 600; color: #16A34A; min-width: 56px; text-align: right; }
.pcc-opp-up-neg { font-size: 12px; font-weight: 600; color: #DC2626; min-width: 56px; text-align: right; }
.pcc-opp-score  { font-size: 11px; color: #94a3b8; min-width: 36px; text-align: right; }

.pcc-sidebar-block {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 9px; padding: 10px 14px; margin-bottom: 8px;
}
.pcc-sidebar-label { font-size: 9px; color: #475569; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 700; }
.pcc-sidebar-value { font-size: 16px; font-weight: 700; color: #f1f5f9; margin-top: 2px; letter-spacing: -0.01em; }
.pcc-sidebar-delta { font-size: 11px; margin-top: 1px; }
.pcc-sd-pos { color: #4ade80; }
.pcc-sd-neg { color: #f87171; }
.pcc-sd-neu { color: #475569; }

.pcc-placeholder {
    background: #F5F7FA; border-radius: 16px; border: 2px dashed #E2E8F0;
    padding: 60px 40px; text-align: center; margin: 40px 0;
}
.pcc-placeholder-icon  { font-size: 44px; margin-bottom: 16px; }
.pcc-placeholder-title { font-size: 18px; font-weight: 700; color: #374151; margin-bottom: 8px; }
.pcc-placeholder-body  { font-size: 13px; color: #94a3b8; max-width: 400px; margin: 0 auto; line-height: 1.6; }
.pcc-placeholder-stage { display: inline-block; margin-top: 14px; padding: 4px 14px; background: #E2E8F0; border-radius: 20px; font-size: 11px; font-weight: 600; color: #6b7280; }

/* ── WATCHLIST PAGE ─────────────────────────────────────────────── */
.wl-page-title    { font-size:28px; font-weight:800; color:#0F172A; letter-spacing:-0.03em; line-height:1.1; }
.wl-page-subtitle { font-size:14px; color:#64748B; margin-top:5px; line-height:1.4; }

.wl-card {
    background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px;
    overflow:hidden; margin-bottom:20px;
    box-shadow:0 1px 3px rgba(15,23,42,0.08),0 1px 2px rgba(15,23,42,0.04);
}
.wl-thead {
    display:flex; align-items:center; padding:10px 20px;
    background:#F8FAFC; border-bottom:1px solid #E2E8F0;
    font-size:11px; font-weight:600; color:#64748B;
    text-transform:uppercase; letter-spacing:0.07em;
}
.wl-row {
    display:flex; align-items:center; padding:11px 20px;
    border-bottom:1px solid #F1F5F9; transition:background 0.12s ease;
}
.wl-row:last-child { border-bottom:none; }
.wl-row:hover { background:#F8FAFC; }

.wl-c-ticker { flex:0 0 220px; display:flex; align-items:center; gap:10px; min-width:0; }
.wl-c-price  { flex:0 0 92px;  font-size:13px; font-weight:600; color:#0F172A; }
.wl-c-change { flex:0 0 100px; }
.wl-c-value  { flex:0 0 100px; font-size:13px; font-weight:600; color:#0F172A; }
.wl-c-pnl    { flex:0 0 90px; }
.wl-c-fv     { flex:0 0 100px; font-size:13px; color:#0F172A; }
.wl-c-upside { flex:0 0 88px; }
.wl-c-score  { flex:0 0 72px; }
.wl-c-sector { flex:1; font-size:12px; color:#475569; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:8px; }
.wl-c-weight { flex:0 0 70px; font-size:13px; color:#475569; }
.wl-c-action { flex:0 0 82px; }
.wl-c-status { flex:0 0 92px; }

.wl-circle {
    width:34px; height:34px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; color:#fff; flex-shrink:0;
}
.wl-ticker-name  { font-size:13px; font-weight:700; color:#0F172A; line-height:1.2; }
.wl-company-name { font-size:11px; color:#64748B; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:160px; }

.wl-chg { display:inline-flex; align-items:center; gap:2px; font-size:12px; font-weight:600; padding:2px 8px; border-radius:999px; }
.wl-chg-pos { background:#DCFCE7; color:#16A34A; }
.wl-chg-neg { background:#FEE2E2; color:#DC2626; }
.wl-chg-neu { background:#F1F5F9; color:#64748B; }

.wl-pill { display:inline-block; font-size:12px; font-weight:700; padding:3px 10px; border-radius:999px; }
.wl-pill-green { background:#DCFCE7; color:#15803D; }
.wl-pill-blue  { background:#DBEAFE; color:#1D4ED8; }
.wl-pill-grey  { background:#F1F5F9; color:#475569; }
.wl-pill-red   { background:#FEE2E2; color:#DC2626; }
.wl-pill-muted { background:#F1F5F9; color:#94A3B8; font-weight:500; }

.wl-act { display:inline-block; font-size:11px; font-weight:700; padding:3px 9px; border-radius:999px; white-space:nowrap; }
.wl-act-buy   { background:#DCFCE7; color:#15803D; }
.wl-act-add   { background:#DBEAFE; color:#1D4ED8; }
.wl-act-hold  { background:#F1F5F9; color:#475569; }
.wl-act-watch { background:#FEF3C7; color:#D97706; }
.wl-act-trim  { background:#FED7AA; color:#C2410C; }
.wl-act-sell  { background:#FEE2E2; color:#DC2626; }
.wl-act-avoid { background:#F1F5F9; color:#64748B; }

.wl-status { display:inline-block; font-size:11px; font-weight:600; padding:2px 9px; border-radius:999px; white-space:nowrap; }
.wl-status-portfolio { background:#0B1628; color:#fff; }
.wl-status-watchlist { background:#E2E8F0; color:#475569; }
.wl-status-research  { background:#F3E8FF; color:#7C3AED; }

.wl-caption { font-size:11px; color:#94A3B8; padding:8px 4px 0; line-height:1.5; }

.wl-insight-card {
    background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px;
    padding:18px 20px;
    box-shadow:0 1px 3px rgba(15,23,42,0.08),0 1px 2px rgba(15,23,42,0.04);
    height:100%;
}
.wl-insight-title {
    font-size:13px; font-weight:700; color:#0F172A;
    margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid #F1F5F9;
    display:flex; align-items:center; gap:6px;
}
.wl-insight-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:7px 0; border-bottom:1px solid #F8FAFC; font-size:13px;
}
.wl-insight-row:last-child { border-bottom:none; }
.wl-insight-ticker { font-weight:700; color:#0F172A; min-width:46px; font-size:13px; }
.wl-insight-name   { color:#64748B; font-size:12px; flex:1; padding:0 8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

@media (max-width:900px) {
    .wl-c-sector { display:none; }
    .wl-c-fv, .wl-c-upside { display:none; }
    .wl-company-name { display:none; }
}

/* ── SLIDERS ── */
[data-testid="stSlider"] > div > div > div > div { background: #061A33 !important; }
[data-testid="stSlider"] [role="slider"] {
    background: #061A33 !important; border: 2px solid #FFFFFF !important;
    box-shadow: 0 1px 4px rgba(6,26,51,0.4) !important;
}

/* ── MOBILE ── */
@media (max-width: 768px) {
    .block-container { padding: 1rem 1rem 2rem 1rem !important; }
    .pcc-page-title { font-size: 18px; }
    .pcc-metric-value { font-size: 18px; }
    .pcc-opp-name { display: none; }
    [data-testid="stSidebar"] .stButton > button {
        font-size: 12px !important; padding: 8px 10px !important;
    }
}
@media (max-width: 480px) {
    .block-container { padding: 0.75rem 0.75rem 1.5rem 0.75rem !important; }
    .pcc-metric { padding: 12px 14px; }
    .pcc-metric-value { font-size: 16px; }
    .pcc-opp-price { display: none; }
}
"""
