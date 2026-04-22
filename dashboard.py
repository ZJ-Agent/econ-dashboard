import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from fredapi import Fred
from datetime import datetime
import numpy as np

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded", # Opened this so you can see the new controls
)

# ── Power BI–style CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] {
      font-family: 'Segoe UI', sans-serif;
      background-color: #1a1a2e;
      color: #e0e0e0;
  }
  .main { background-color: #1a1a2e; }
  .block-container { padding: 1rem 1.5rem 2rem 1.5rem; max-width: 100%; }

  /* KPI Cards */
  .kpi-card {
      background: #16213e;
      border: 1px solid #0f3460;
      border-radius: 4px;
      padding: 16px 18px 12px 18px;
      margin-bottom: 8px;
      border-left: 4px solid #0078d4;
  }
  .kpi-card.green  { border-left-color: #107c10; }
  .kpi-card.yellow { border-left-color: #ffb900; }
  .kpi-card.red    { border-left-color: #d13438; }
  .kpi-card.neutral{ border-left-color: #0078d4; }

  .kpi-label { font-size: 11px; color: #8a8a9a; font-weight: 600;
               text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .kpi-value { font-size: 26px; font-weight: 700; line-height: 1.1; }
  .kpi-value.green  { color: #6ccb5f; }
  .kpi-value.yellow { color: #ffb900; }
  .kpi-value.red    { color: #f1707a; }
  .kpi-value.neutral{ color: #4fc3f7; }
  .kpi-unit  { font-size: 12px; color: #8a8a9a; margin-left: 3px; }
  .kpi-delta { font-size: 11px; margin-top: 4px; }
  .kpi-delta.up   { color: #6ccb5f; }
  .kpi-delta.down { color: #f1707a; }
  .kpi-note  { font-size: 10px; color: #5a5a6a; margin-top: 4px; }
  .kpi-date  { font-size: 9px;  color: #3a3a4a; margin-top: 2px; }

  /* Section headers */
  .section-header {
      background: #16213e;
      border-left: 4px solid #0078d4;
      padding: 8px 14px;
      margin: 18px 0 10px 0;
      font-size: 13px;
      font-weight: 700;
      color: #c8d0e0;
      letter-spacing: 0.3px;
      text-transform: uppercase;
  }

  /* Streamlit tweaks */
  div[data-testid="stMetricValue"] { font-size: 26px !important; }
  div[data-testid="column"] { padding: 0 4px !important; }
  .stTabs [data-baseweb="tab-list"] { background: #16213e; border-radius: 4px; padding: 4px; }
  .stTabs [data-baseweb="tab"] { color: #8a8a9a; font-weight: 600; font-size: 12px; }
  .stTabs [aria-selected="true"] { background: #0078d4 !important; color: #fff !important; border-radius: 3px; }
  div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
  footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Plotly theme ──────────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="#16213e",
    plot_bgcolor="#16213e",
    font=dict(family="Segoe UI", color="#c8d0e0", size=11),
    margin=dict(l=48, r=16, t=36, b=36),
    xaxis=dict(showgrid=False, zeroline=False, linecolor="#2a2a4a"),
    yaxis=dict(gridcolor="#1e2a3a", zeroline=False, linecolor="#2a2a4a"),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
)

LINE_COLORS = ["#0078d4", "#6ccb5f", "#ffb900", "#f1707a", "#4fc3f7", "#c586c0"]

# ── Indicators config (Full set restored) ─────────────────────────────────────
INDICATORS = {
    "leading": {
        "label": "Leading Indicators", "color": "#0078d4", "desc": "Forward-looking · 6–18 mo ahead",
        "items": [
            dict(id="NAPM",    label="ISM Mfg PMI",        unit="",       dec=1, mode="value", note=">50 expansion",    status="pmi"      ),
            dict(id="USSLIND", label="Conference Board LEI", unit="index",  dec=1, mode="value", note="Composite leading",   status="mom_dir"  ),
            dict(id="HOUST",   label="Housing Starts",       unit="K/yr",   dec=0, mode="value", note="New residential",    status="housing"  ),
            dict(id="PERMIT",  label="Building Permits",     unit="K/yr",   dec=0, mode="value", note="Fwd construction",   status="permits"  ),
            dict(id="DGORDER", label="Durable Goods Orders", unit="$B",     dec=1, mode="value", note="Business investment",status="mom_dir"  ),
            dict(id="UMCSENT", label="Consumer Sentiment",   unit="",       dec=1, mode="value", note="U of Michigan",      status="sentiment"),
            dict(id="M2SL",    label="M2 Money Supply",      unit="$B",     dec=0, mode="value", note="Watch YoY%",          status="neutral"  ),
        ]
    },
    "coincident": {
        "label": "Coincident Indicators", "color": "#8764b8", "desc": "Real-time economic health",
        "items": [
            dict(id="PAYEMS",          label="Nonfarm Payrolls",      unit="K MoM",  dec=0, mode="diff",  note="Jobs added",        status="payrolls"),
            dict(id="UNRATE",          label="Unemployment Rate",      unit="%",      dec=1, mode="value", note="",                  status="unemp"   ),
            dict(id="AHETPI",          label="Avg Hourly Earnings",   unit="% YoY",  dec=1, mode="yoy",   note="Wage inflation",    status="wages"   ),
            dict(id="RSAFS",           label="Retail Sales",          unit="% YoY",  dec=1, mode="yoy",   note="Consumer spending", status="retail"  ),
            dict(id="A191RL1Q225SBEA", label="Real GDP Growth",       unit="% ann.", dec=1, mode="value", note="Quarterly",          status="gdp"     ),
            dict(id="INDPRO",          label="Industrial Production", unit="% YoY",  dec=1, mode="yoy",   note="Factory output",    status="mom_dir" ),
        ]
    },
    "lagging": {
        "label": "Lagging Indicators", "color": "#e04b7a", "desc": "Confirm trends · Fed watches these",
        "items": [
            dict(id="CPIAUCSL",  label="CPI Headline",  unit="% YoY", dec=1, mode="yoy",   note="Consumer prices",  status="inflation"),
            dict(id="CPILFESL",  label="Core CPI",      unit="% YoY", dec=1, mode="yoy",   note="Ex food & energy", status="inflation"),
            dict(id="PCEPI",     label="PCE Inflation", unit="% YoY", dec=1, mode="yoy",   note="Fed preferred",    status="inflation"),
            dict(id="PCEPILFE",  label="Core PCE",      unit="% YoY", dec=1, mode="yoy",   note="Fed 2% target",    status="inflation"),
            dict(id="FEDFUNDS",  label="Fed Funds Rate",unit="%",     dec=2, mode="value", note="FOMC benchmark",   status="neutral"  ),
        ]
    },
    "market": {
        "label": "Market Indicators", "color": "#ffb900", "desc": "Investor sentiment & risk",
        "items": [
            dict(id="DGS10",        label="10-Yr Treasury",      unit="%", dec=2, mode="value", note="Long-term rate",    status="neutral"),
            dict(id="DGS2",         label="2-Yr Treasury",       unit="%", dec=2, mode="value", note="Short-term rate",  status="neutral"),
            dict(id="T10Y2Y",       label="Yield Curve 2s/10s",  unit="%", dec=2, mode="value", note="<0 = inverted",    status="spread2"),
            dict(id="VIXCLS",       label="VIX Fear Gauge",      unit="",  dec=1, mode="value", note="<15 calm >25 stress",status="vix"  ),
            dict(id="BAMLH0A0HYM2", label="HY Credit Spread",   unit="%", dec=2, mode="value", note="Widen = stress",    status="spread"),
            dict(id="DTWEXBGS",     label="Trade-Wtd USD Index", unit="",  dec=1, mode="value", note="Broad dollar",      status="neutral"),
        ]
    },
    "energy": {
        "label": "Energy & Feedstock", "color": "#107c10", "desc": "Resin cost chain foundation",
        "items": [
            dict(id="DCOILWTICO",   label="WTI Crude Oil",        unit="$/bbl",   dec=2, mode="value", note="Global benchmark",        status="oil"    ),
            dict(id="DCOILBRENTEU", label="Brent Crude",          unit="$/bbl",   dec=2, mode="value", note="Intl benchmark",          status="oil"    ),
            dict(id="DHHNGSP",      label="Henry Hub Nat Gas",    unit="$/MMBtu", dec=2, mode="value", note="U.S. cracker feedstock", status="gas"    ),
            dict(id="DPROPANEMBTX", label="Propane Mont Belvieu", unit="$/gal",   dec=3, mode="value", note="NGL proxy",               status="neutral"),
        ]
    },
    "resin_ppi": {
        "label": "Resin PPI", "color": "#00b294", "desc": "BLS official indices · ~4–6 wk lag",
        "items": [
            dict(id="PCU325211325211",  label="Resin Mfg PPI",          unit="% YoY", dec=1, mode="yoy", note="PCU325211325211",  status="ppi_dir"),
            dict(id="WPU0662",          label="Thermoplastic PPI",      unit="% YoY", dec=1, mode="yoy", note="WPU0662",          status="ppi_dir"),
            dict(id="PCU3252113252111", label="Thermoplastic Ind PPI", unit="% YoY", dec=1, mode="yoy", note="PCU3252113252111", status="ppi_dir"),
        ]
    },
    "demand": {
        "label": "Resin Demand Signals", "color": "#498205", "desc": "End-market consumption drivers",
        "items": [
            dict(id="TOTALSA",  label="Auto Sales SAAR",       unit="M/yr",  dec=2, mode="value", note="Eng. resin signal",  status="auto"   ),
            dict(id="ISRATIO",  label="Inventory/Sales Ratio", unit="",      dec=2, mode="value", note="Low = tight supply", status="neutral"),
            dict(id="CMRMTSPL", label="Mfg Real Sales",        unit="% YoY", dec=1, mode="yoy",   note="Industrial demand",  status="mom_dir"),
        ]
    },
}

# ── Status Functions (Unchanged) ──────────────────────────────────────────────
STATUS_FNS = {
    "pmi":       lambda v, s: "green"  if v > 55 else ("yellow" if v > 50 else "red"),
    "housing":   lambda v, s: "green"  if v > 1400 else ("yellow" if v > 1000 else "red"),
    "permits":   lambda v, s: "green"  if v > 1500 else ("yellow" if v > 1100 else "red"),
    "sentiment": lambda v, s: "green"  if v > 80 else ("yellow" if v > 60 else "red"),
    "payrolls":  lambda v, s: "green"  if s.get("diff",0) > 150 else ("yellow" if s.get("diff",0) > 50 else "red"),
    "unemp":     lambda v, s: "green"  if v < 4.5 else ("yellow" if v < 6 else "red"),
    "wages":     lambda v, s: "green"  if s.get("yoy",v) < 4 else ("yellow" if s.get("yoy",v) < 6 else "red"),
    "retail":    lambda v, s: "green"  if s.get("yoy",v) > 3 else ("yellow" if s.get("yoy",v) > 0 else "red"),
    "gdp":       lambda v, s: "green"  if v > 2 else ("yellow" if v > 0 else "red"),
    "inflation": lambda v, s: "green"  if s.get("yoy",v) < 2.5 else ("yellow" if s.get("yoy",v) < 4 else "red"),
    "vix":       lambda v, s: "green"  if v < 15 else ("yellow" if v < 25 else "red"),
    "spread":    lambda v, s: "green"  if v < 4 else ("yellow" if v < 6 else "red"),
    "spread2":   lambda v, s: "green"  if v > 0 else "red",
    "oil":       lambda v, s: "green"  if v < 70 else ("yellow" if v < 90 else "red"),
    "gas":       lambda v, s: "green"  if v < 3 else ("yellow" if v < 5 else "red"),
    "auto":      lambda v, s: "green"  if v > 15 else ("yellow" if v > 13 else "red"),
    "mom_dir":   lambda v, s: "green"  if s.get("mom_pct",0) > 0 else ("yellow" if s.get("mom_pct",0) > -2 else "red"),
    "ppi_dir":   lambda v, s: "green"  if abs(s.get("yoy",0)) < 5 else ("red" if s.get("yoy",0) > 10 else "yellow"),
    "neutral":   lambda v, s: "neutral",
}

# ── Data Loading Logic (Updated for 1950s search) ─────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_series(api_key: str, series_id: str, start_date: datetime) -> pd.Series:
    try:
        fred = Fred(api_key=api_key)
        s = fred.get_series(series_id, observation_start=start_date)
        return s.dropna()
    except Exception:
        return pd.Series(dtype=float)

def compute_stats(s: pd.Series, mode: str) -> dict:
    if s.empty or len(s) < 2: return {}
    latest = float(s.iloc[-1])
    prev   = float(s.iloc[-2])
    y12    = float(s.iloc[-13]) if len(s) >= 13 else None
    diff    = latest - prev
    mom_pct = ((latest - prev) / abs(prev) * 100) if prev != 0 else None
    yoy     = ((latest - y12) / abs(y12) * 100) if y12 and y12 != 0 else None
    display = yoy if mode == "yoy" else (diff if mode == "diff" else latest)
    return dict(latest=latest, diff=diff, mom_pct=mom_pct, yoy=yoy, display=display, date=str(s.index[-1])[:10])

def fmt(v, dec):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v:,.{dec}f}"

def color_class(ind, stats):
    fn = STATUS_FNS.get(ind["status"], STATUS_FNS["neutral"])
    return fn(stats.get("latest", 0), stats)

def kpi_html(ind, stats):
    if not stats:
        return f'<div class="kpi-card neutral"><div class="kpi-label">{ind["label"]}</div><div class="kpi-value neutral">—</div><div class="kpi-note">No data</div></div>'
    cls, val, d = color_class(ind, stats), fmt(stats.get("display"), ind["dec"]), stats.get("mom_pct")
    delta = f'<div class="kpi-delta {"up" if d >= 0 else "down"}">{"▲" if d >= 0 else "▼"} {abs(d):.1f}% MoM</div>' if d is not None else ""
    return f'<div class="kpi-card {cls}"><div class="kpi-label">{ind["label"]}</div><div class="kpi-value {cls}">{val}<span class="kpi-unit">{ind["unit"]}</span></div>{delta}<div class="kpi-note">{ind["note"]}</div><div class="kpi-date">{stats.get("date","")}</div></div>'

# ── Chart Helpers ─────────────────────────────────────────────────────────────
def make_line_chart(series_dict: dict, title: str, yformat=".2f") -> go.Figure:
    fig = go.Figure()
    for i, (name, s) in enumerate(series_dict.items()):
        if s.empty: continue
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, line=dict(color=LINE_COLORS[i % len(LINE_COLORS)], width=2), hovertemplate=f"<b>{name}</b>: %{{y:{yformat}}}<extra></extra>"))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=title, font=dict(size=13), x=0))
    return fig

def make_bar_chart(s: pd.Series, title: str, color_pos="#6ccb5f", color_neg="#f1707a") -> go.Figure:
    colors = [color_pos if v >= 0 else color_neg for v in s.values]
    fig = go.Figure(go.Bar(x=s.index, y=s.values, marker_color=colors))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=title, font=dict(size=13), x=0))
    fig.add_hline(y=0, line_width=1, line_color="#3a3a5a")
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Sidebar Filter ────────────────────────────────────────────────────────
    st.sidebar.markdown("### 📅 Time Horizon")
    start_year = st.sidebar.slider("Start Year", 1947, 2024, 2015)
    global_start_date = datetime(start_year, 1, 1)

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.markdown(f"""<div style="padding:8px 0 4px 0"><span style="font-size:20px;font-weight:700;color:#e0e0e0">📊 Market Intelligence Dashboard</span><br><span style="font-size:11px;color:#5a5a7a">FRED Economic Data · Since {start_year}</span></div>""", unsafe_allow_html=True)
    with col_refresh:
        if st.button("↻ Refresh", use_container_width=True): st.cache_data.clear()

    # ── API Key ───────────────────────────────────────────────────────────────
    try: api_key = st.secrets["FRED_API_KEY"]
    except Exception:
        api_key = st.text_input("FRED API Key", type="password")
        if not api_key: st.stop()

    # ── Load Series ───────────────────────────────────────────────────────────
    all_items = [item for sec in INDICATORS.values() for item in sec["items"]]
    id_list   = [i["id"] for i in all_items]

    with st.spinner(f"Loading data back to {start_year}..."):
        raw = {sid: load_series(api_key, sid, global_start_date) for sid in id_list}

    stats_map = {}
    for item in all_items:
        s = raw[item["id"]]
        if s.empty: continue
        mode = item["mode"]
        s_display = s.pct_change(12).dropna()*100 if mode == "yoy" else (s.diff().dropna() if mode == "diff" else s)
        stats_map[item["id"]] = compute_stats(s_display, mode)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📋 Overview", "📈 Charts", "🛢 Resin Chain", "📊 Comparisons"])

    with tabs[0]: # Overview
        for sec_id, sec in INDICATORS.items():
            st.markdown(f'<div class="section-header" style="border-left-color:{sec["color"]}">{sec["label"]}<span style="font-size:10px;color:#5a5a7a;font-weight:400;margin-left:10px">{sec["desc"]}</span></div>', unsafe_allow_html=True)
            cols = st.columns(4)
            for j, item in enumerate(sec["items"]):
                with cols[j % 4]: st.markdown(kpi_html(item, stats_map.get(item["id"], {})), unsafe_allow_html=True)

    with tabs[1]: # Charts
        chart_cols = st.columns(2)
        with chart_cols[0]:
            yc = raw.get("T10Y2Y", pd.Series(dtype=float))
            if not yc.empty:
                fig = make_line_chart({"2s/10s Spread": yc}, "Yield Curve Full History")
                fig.add_hline(y=0, line_width=1.5, line_color="#d13438", line_dash="dot")
                st.plotly_chart(fig, use_container_width=True)
        
        with chart_cols[1]:
            inf_data = {lbl: (raw[sid].pct_change(12)*100).dropna() for sid, lbl in [("CPIAUCSL", "CPI"), ("CPILFESL", "Core CPI")] if not raw[sid].empty}
            st.plotly_chart(make_line_chart(inf_data, "Inflation YoY%"), use_container_width=True)

    with tabs[2]: # Resin Chain
        st.markdown('<div class="section-header">Resin PPI & Feedstocks</div>', unsafe_allow_html=True)
        rc_cols = st.columns(2)
        with rc_cols[0]:
            ppi_data = {lbl: (raw[sid].pct_change(12)*100).dropna() for sid, lbl in [("PCU325211325211", "Resin PPI"), ("WPU0662", "Thermoplastic PPI")] if not raw[sid].empty}
            st.plotly_chart(make_line_chart(ppi_data, "Resin Industry PPI YoY%"), use_container_width=True)
        with rc_cols[1]:
            energy = {lbl: raw[sid] for sid, lbl in [("DCOILWTICO", "WTI Crude"), ("DHHNGSP", "Nat Gas")] if not raw[sid].empty}
            st.plotly_chart(make_line_chart(energy, "Energy Prices"), use_container_width=True)

if __name__ == "__main__":
    main()    st.sidebar.markdown("### 🛠 Global Settings")
    start_year = st.sidebar.slider(
        "Historical Lookback (Start Year)", 
        min_value=1947, 
        max_value=2024, 
        value=2015,
        help="Select how far back to pull economic data. Note: Some series may not exist before the 1990s."
    )
    global_start_date = datetime(start_year, 1, 1)

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.markdown(f"""
        <div style="padding:8px 0 4px 0">
          <span style="font-size:20px;font-weight:700;color:#e0e0e0">📊 Market Intelligence Dashboard</span><br>
          <span style="font-size:11px;color:#5a5a7a">Data from {start_year} to Present</span>
        </div>""", unsafe_allow_html=True)
    
    with col_refresh:
        if st.button("↻ Refresh", use_container_width=True):
            st.cache_data.clear()

    # ── API Key Handling ──────────────────────────────────────────────────────
    # [Your existing API key logic here...]
    api_key = st.secrets.get("FRED_API_KEY") or "YOUR_KEY_HERE"

    # ── Load all series using the new start date ──────────────────────────────
    all_items = [item for sec in INDICATORS.values() for item in sec["items"]]
    id_list   = [i["id"] for i in all_items]

    with st.spinner(f"Fetching data back to {start_year}..."):
        # All data is now fetched based on the slider
        raw = {sid: load_series(api_key, sid, global_start_date) for sid in id_list}

    stats_map = {}
    for item in all_items:
        s = raw[item["id"]]
        if s.empty: continue
        
        mode = item["mode"]
        # Transform the whole series for charting
        if mode == "yoy":
            s_display = s.pct_change(12).dropna() * 100
        elif mode == "diff":
            s_display = s.diff().dropna()
        else:
            s_display = s
            
        stats_map[item["id"]] = compute_stats(s_display, mode)

    # ── Layout: Tabs & Charts ────────────────────────────────────────────────
    tabs = st.tabs(["📋 Overview", "📈 Charts", "🛢 Resin Chain"])

    with tabs[0]:
        # KPI Grid (Logic remains same, but uses expanded 'raw' data)
        # ... [Your existing KPI rendering code] ...

    with tabs[1]:
        chart_cols = st.columns(2)
        
        with chart_cols[0]:
            # Yield Curve History - Now uses the full selected range
            yc_full = raw.get("T10Y2Y", pd.Series(dtype=float))
            if not yc_full.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=yc_full.index, y=yc_full.values, name="2s/10s Spread", fill="tozeroy"))
                # ... [Your existing styling] ...
                st.plotly_chart(fig, use_container_width=True)

        # ... [Rest of your charts, they will automatically use the expanded series] ...

if __name__ == "__main__":
    main()
