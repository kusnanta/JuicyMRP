"""ui/styles.py — global CSS injected into Streamlit."""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background:rgba(0,0,0,0.04); border-radius:10px; padding:3px; gap:2px; }
.stTabs [data-baseweb="tab"] { border-radius:8px; font-weight:600; font-size:0.84rem; letter-spacing:.02em; padding:7px 18px; }
.stTabs [aria-selected="true"] { background:#1a56db !important; color:white !important; }

/* ── Metric cards ── */
[data-testid="metric-container"] { background:rgba(0,0,0,0.03); border:0.5px solid rgba(0,0,0,.08); border-radius:10px; padding:14px 18px; }
[data-testid="metric-container"] label { font-size:.72rem !important; letter-spacing:.08em; text-transform:uppercase; font-weight:600; }
[data-testid="metric-container"] [data-testid="metric-value"] { font-size:1.7rem !important; font-weight:700; }

/* ── Section labels ── */
.section-label { font-size:.65rem; letter-spacing:.14em; text-transform:uppercase; font-weight:600; color:#6b7280; margin-bottom:8px; margin-top:20px; }

/* ── Upload hints ── */
.upload-hint { font-size:.72rem; font-family:'IBM Plex Mono',monospace; color:#9ca3af; margin-bottom:8px; }

/* ── Method radio ── */
.method-radio-row { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }

/* ── Accuracy pivot ── */
.acc-pivot th { background:#f3f4f6; font-size:.72rem; font-weight:600; padding:6px 10px; border-bottom:1px solid #e5e7eb; white-space:nowrap; text-align:center; }
.acc-pivot th.prod-h { text-align:left; position:sticky; left:0; z-index:2; }
.acc-pivot td { font-size:.78rem; padding:6px 10px; text-align:center; border-bottom:1px solid #f3f4f6; }
.acc-pivot td.prod-cell { text-align:left; font-weight:500; position:sticky; left:0; background:inherit; z-index:1; white-space:nowrap; }
.acc-pivot tr:nth-child(even) { background:#fafafa; }
.acc-pivot tr:hover { background:#eff6ff; }
.best-badge { background:#dcfce7; color:#15803d; font-weight:600; border-radius:6px; padding:2px 8px; font-size:.72rem; }
.other-val  { color:#6b7280; font-size:.72rem; }
.na-val     { color:#d1d5db; font-size:.72rem; }
.active-col { background:rgba(26,86,219,0.06) !important; border-left:2px solid #1a56db; border-right:2px solid #1a56db; }

/* ── MRP pivot ── */
.mrp-pivot th { background:#f3f4f6; font-size:.72rem; font-weight:600; padding:6px 10px; border-bottom:1px solid #e5e7eb; text-align:right; white-space:nowrap; }
.mrp-pivot th.mat-h { text-align:left; position:sticky; left:0; z-index:2; }
.mrp-pivot td { font-size:.72rem; font-family:'IBM Plex Mono',monospace; padding:5px 10px; text-align:right; border-bottom:1px solid #f3f4f6; }
.mrp-pivot td.mat-cell { text-align:left; font-family:'IBM Plex Sans',sans-serif; font-weight:500; font-size:.78rem; position:sticky; left:0; background:inherit; z-index:1; white-space:nowrap; }
.mrp-pivot td.total-col { font-weight:600; color:#1a56db; }
.mrp-pivot tr:nth-child(even) { background:#fafafa; }
.mrp-pivot tr:hover { background:#eff6ff; }
.pivot-wrap { overflow-x:auto; border:0.5px solid #e5e7eb; border-radius:8px; margin-bottom:1rem; }

/* ── MRP total inline bar ── */
.mrp-total-bar-wrap { display:flex; align-items:center; gap:6px; }
.mrp-total-bar-track { flex:1; height:10px; background:#f3f4f6; border-radius:3px; overflow:hidden; min-width:50px; }
.mrp-total-bar-fill  { height:100%; border-radius:3px; background:#1a56db; }
.pct-label { font-size:.68rem; color:#9ca3af; font-family:'IBM Plex Mono',monospace; width:30px; flex-shrink:0; }
</style>
"""
