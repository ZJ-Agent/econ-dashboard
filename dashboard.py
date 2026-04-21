import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from fredapi import Fred
from datetime import datetime, timedelta
import numpy as np

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
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

  /* Yield curve hero */
  .yc-hero {
      background: #16213e;
      border: 1px solid #0f3460;
      border-radius: 4px;
      padding: 18px 24px;
      margin-bottom: 14px;
  }

  /* Streamlit tweaks */
  div[data-testid="stMetricValue"] { font-size: 26px !important; }
  div[data-testid="column"] { padding: 0 4px !important; }
  .stTabs [data-baseweb="tab-list"] { background: #16213e; border-radius: 4px; padding: 4px; }
  .stTabs [data-baseweb="tab"] { color: #8a8a9a; font-weight: 600; font-size: 12px; }
  .stTabs [aria-selected="true"] { background: #0078d4 !important; color: #fff !important; border-radius: 3px; }
  div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
  .stAlert { border-radius: 4px; }
  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Plotly theme ──────────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="#16213e",
    plot_bgcolor="#16213e",
    font=dict(family="Segoe UI", color="#c8d0e0", size=11),
    margin=dict(l=48, r=16, t=36, b=36),
    xaxis=dict(
        showgrid=False, zeroline=False,
        linecolor="#2a2a4a", tickcolor="#2a2a4a", tickfont=dict(size=10)
    ),
    yaxis=dict(
        gridcolor="#1e2a3a", zeroline=False,
        linecolor="#2a2a4a", tickfont=dict(size=10)
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
    ),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#0f3460", font_size=11, bordercolor="#0078d4"),
)

LINE_COLORS = ["#0078d4", "#6ccb5f", "#ffb900", "#f1707a", "#4fc3f7",
               "#c586c0", "#e06c75", "#56b6c2", "#d19a66"]

# ── Indicators config ─────────────────────────────────────────────────────────
INDICATORS = {
    "leading": {
        "label": "Leading Indicators",
        "color": "#0078d4",
        "desc": "Forward-looking · 6–18 mo ahead",
        "items": [
            dict(id="NAPM",    label="ISM Mfg PMI",          unit="",       dec=1, mode="value", note=">50 expansion",      status="pmi"      ),
            dict(id="USSLIND", label="Conference Board LEI", unit="index",  dec=1, mode="value", note="Composite leading",   status="mom_dir"  ),
            dict(id="HOUST",   label="Housing Starts",       unit="K/yr",   dec=0, mode="value", note="New residential",    status="housing"  ),
            dict(id="PERMIT",  label="Building Permits",     unit="K/yr",   dec=0, mode="value", note="Fwd construction",   status="permits"  ),
            dict(id="DGORDER", label="Durable Goods Orders", unit="$B",     dec=1, mode="value", note="Business investment",status="mom_dir"  ),
            dict(id="UMCSENT", label="Consumer Sentiment",   unit="",       dec=1, mode:"value", note="U of Michigan",      status="sentiment"),
            dict(id="M2SL",    label="M2 Money Supply",      unit="$B",     dec=0, mode="value", note="Watch YoY%",         status="neutral"  ),
        ]
    },
    "coincident": {
        "label": "Coincident Indicators",
        "color": "#8764b8",
        "desc": "Real-time economic health",
        "items": [
            dict(id="PAYEMS",          label="Nonfarm Payrolls",      unit="K MoM",  dec=0, mode="diff",  note="Jobs added",        status="payrolls"),
            dict(id="UNRATE",          label="Unemployment Rate",     unit="%",      dec=1, mode="value", note="",                  status="unemp"   ),
            dict(id="AHETPI",          label="Avg Hourly Earnings",   unit="% YoY",  dec=1, mode="yoy",   note="Wage inflation",    status="wages"   ),
            dict(id="RSAFS",           label="Retail Sales",          unit="% YoY",  dec=1, mode="yoy",   note="Consumer spending", status="retail"  ),
            dict(id="A191RL1Q225SBEA", label="Real GDP Growth",       unit="% ann.", dec=1, mode="value", note="Quarterly",         status="gdp"     ),
            dict(id="INDPRO",          label="Industrial Production", unit="% YoY",  dec=1, mode="yoy",   note="Factory output",    status="mom_dir" ),
        ]
    },
    "lagging": {
        "label": "Lagging Indicators",
        "color": "#e04b7a",
        "desc": "Confirm trends · Fed watches these",
        "items": [
            dict(id="CPIAUCSL",  label="CPI Headline",  unit="% YoY", dec=1, mode="yoy",   note="Consumer prices",  status="inflation"),
            dict(id="CPILFESL",  label="Core CPI",      unit="% YoY", dec=1, mode="yoy",   note="Ex food & energy", status="inflation"),
            dict(id="PCEPI",     label="PCE Inflation", unit="% YoY", dec=1, mode="yoy",   note="Fed preferred",    status="inflation"),
            dict(id="PCEPILFE",  label="Core PCE",      unit="% YoY", dec=1, mode="yoy",   note="Fed 2% target",    status="inflation"),
            dict(id="FEDFUNDS",  label="Fed Funds Rate",unit="%",     dec=2, mode="value", note="FOMC benchmark",   status="neutral"  ),
        ]
    },
    "market": {
        "label": "Market Indicators",
        "color": "#ffb900",
        "desc": "Investor sentiment & risk",
        "items": [
            dict(id="DGS10",        label="10-Yr Treasury",      unit="%", dec=2, mode="value", note="Long-term rate",    status="neutral"),
            dict(id="DGS2",         label="2-Yr Treasury",       unit="%", dec=2, mode="value", note="Short-term rate",  status="neutral"),
            dict(id="T10Y2Y",       label="Yield Curve 2s/10s",  unit="%", dec=2, mode="value", note="<0 = inverted",    status="spread2"),
            dict(id="VIXCLS",       label="VIX Fear Gauge",      unit="",  dec=1, mode="value", note="<15 calm >25 stress",status="vix"  ),
            dict(id="BAMLH0A0HYM2", label="HY Credit Spread",   unit="%", dec=2, mode="value", note="Widen = stress",   status="spread"),
            dict(id="DTWEXBGS",     label="Trade-Wtd USD Index", unit="",  dec=1, mode="value", note="Broad dollar",     status="neutral"),
        ]
    },
    "energy": {
        "label": "Energy & Feedstock",
        "color": "#107c10",
        "desc": "Resin cost chain foundation",
        "items": [
            dict(id="DCOILWTICO",   label="WTI Crude Oil",       unit="$/bbl",   dec=2, mode="value", note="Global benchmark",       status="oil"    ),
            dict(id="DCOILBRENTEU", label="Brent Crude",         unit="$/bbl",   dec=2, mode="value", note="Intl benchmark",         status="oil"    ),
            dict(id="DHHNGSP",      label="Henry Hub Nat Gas",   unit="$/MMBtu", dec=2, mode="value", note="U.S. cracker feedstock", status="gas"    ),
            dict(id="DPROPANEMBTX", label="Propane Mont Belvieu",unit="$/gal",   dec=3, mode="value", note="NGL proxy",              status="neutral"),
        ]
    },
    "resin_ppi": {
        "label": "Resin PPI",
        "color": "#00b294",
        "desc": "BLS official indices · ~4–6 wk lag",
        "items": [
            dict(id="PCU325211325211",  label="PPI: Resin Mfg",         unit="% YoY", dec=1, mode="yoy", note="PCU325211325211",  status="ppi_dir"),
            dict(id="WPU0662",          label="PPI: Thermoplastic",     unit="% YoY", dec=1, mode="yoy", note="WPU0662",          status="ppi_dir"),
            dict(id="PCU3252113252111", label="PPI: Thermoplastic Ind", unit="% YoY", dec=1, mode="yoy", note="PCU3252113252111", status="ppi_dir"),
        ]
    },
    "demand": {
        "label": "Resin Demand Signals",
        "color": "#498205",
        "desc": "End-market consumption drivers",
        "items": [
            dict(id="TOTALSA",  label="Auto Sales SAAR",       unit="M/yr",  dec=2, mode="value", note="Eng. resin signal",  status="auto"   ),
            dict(id="ISRATIO",  label="Inventory/Sales Ratio", unit="",      dec=2, mode="value", note="Low = tight supply", status="neutral"),
            dict(id="CMRMTSPL", label="Mfg Real Sales",        unit="% YoY", dec=1, mode="yoy",   note="Industrial demand",  status="mom_dir"),
        ]
    },
}

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

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_series(api_key: str, series_id: str, periods: int = 60) -> pd.Series:
    try:
        fred = Fred(api_key=api_key)
        s = fred.get_series(series_id)
        return s.dropna().iloc[-periods:]
    except Exception:
        return pd.Series(dtype=float)

def compute_stats(s: pd.Series, mode: str) -> dict:
    if s.empty:
        return {}
    latest = float(s.iloc[-1])
    prev   = float(s.iloc[-2]) if len(s) >= 2 else None
    y12    = float(s.iloc[-13]) if len(s) >= 13 else None

    diff    = latest - prev if prev is not None else None
    mom_pct = ((latest - prev) / abs(prev) * 100) if prev and prev != 0 else None
    yoy     = ((latest - y12) / abs(y12) * 100) if y12 and y12 != 0 else None

    display = yoy if mode == "yoy" else (diff if mode == "diff" else latest)
    return dict(latest=latest, diff=diff, mom_pct=mom_pct, yoy=yoy,
                display=display, date=str(s.index[-1])[:10])

def fmt(v, dec):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:,.{dec}f}"

def color_class(ind, stats):
    fn = STATUS_FNS.get(ind["status"], STATUS_FNS["neutral"])
    return fn(stats.get("latest", 0), stats)

# ── KPI card HTML ─────────────────────────────────────────────────────────────
def kpi_html(ind, stats):
    if not stats:
        return f"""
        <div class="kpi-card neutral">
          <div class="kpi-label">{ind['label']}</div>
          <div class="kpi-value neutral">—</div>
          <div class="kpi-note">No data</div>
        </div>"""

    cls    = color_class(ind, stats)
    val    = fmt(stats.get("display"), ind["dec"])
    d      = stats.get("mom_pct")
    delta  = ""
    if d is not None:
        arrow = "▲" if d >= 0 else "▼"
        dcls  = "up" if d >= 0 else "down"
        delta = f'<div class="kpi-delta {dcls}">{arrow} {abs(d):.1f}% MoM</div>'

    return f"""
    <div class="kpi-card {cls}">
      <div class="kpi-label">{ind['label']}</div>
      <div class="kpi-value {cls}">{val}<span class="kpi-unit">{ind['unit']}</span></div>
      {delta}
      <div class="kpi-note">{ind['note']}</div>
      <div class="kpi-date">{stats.get('date','')}</div>
    </div>"""

# ── Chart helpers ─────────────────────────────────────────────────────────────
def make_line_chart(series_dict: dict, title: str, yformat=".2f") -> go.Figure:
    fig = go.Figure()
    for i, (name, s) in enumerate(series_dict.items()):
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=LINE_COLORS[i % len(LINE_COLORS)], width=2),
            hovertemplate=f"<b>{name}</b>: %{{y:{yformat}}}<extra></extra>"
        ))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=title, font=dict(size=13), x=0))
    return fig

def make_bar_chart(s: pd.Series, title: str, color_pos="#6ccb5f", color_neg="#f1707a") -> go.Figure:
    colors = [color_pos if v >= 0 else color_neg for v in s.values]
    fig = go.Figure(go.Bar(
        x=s.index, y=s.values, marker_color=colors,
        hovertemplate="%{x}: %{y:.1f}<extra></extra>"
    ))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=title, font=dict(size=13), x=0))
    fig.add_hline(y=0, line_width=1, line_color="#3a3a5a")
    return fig

def yoy_series(s: pd.Series) -> pd.Series:
    return s.pct_change(12) * 100

def diff_series(s: pd.Series) -> pd.Series:
    return s.diff()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.markdown("""
        <div style="padding:8px 0 4px 0">
          <span style="font-size:20px;font-weight:700;color:#e0e0e0;letter-spacing:0.3px">
            📊 Market Intelligence Dashboard
          </span><br>
          <span style="font-size:11px;color:#5a5a7a">
            FRED Economic Data · Econ + Resin Industry Indicators
          </span>
        </div>""", unsafe_allow_html=True)
    with col_refresh:
        st.markdown("<div style='padding-top:14px'>", unsafe_allow_html=True)
        refresh = st.button("↻ Refresh", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if refresh:
        st.cache_data.clear()

    # ── API Key ───────────────────────────────────────────────────────────────
    try:
        api_key = st.secrets["FRED_API_KEY"]
    except Exception:
        st.markdown("""
        <div style="background:#1a1a2e;border:1px solid #0f3460;border-left:4px solid #0078d4;
                    border-radius:4px;padding:20px 24px;margin:20px 0">
          <div style="font-size:14px;font-weight:700;color:#4fc3f7;margin-bottom:10px">
            🔑 FRED API Key Required
          </div>
          <div style="font-size:12px;color:#8a8a9a;line-height:1.8">
            Add your free FRED API key to Streamlit Cloud's <b style="color:#c8d0e0">Secrets</b> tab:<br><br>
            <code style="background:#0f3460;padding:6px 12px;border-radius:3px;display:inline-block">
              FRED_API_KEY = "your_key_here"
            </code><br><br>
            Get a free key at <a href="https://fred.stlouisfed.org/docs/api/api_key.html"
              style="color:#0078d4">fred.stlouisfed.org</a>
          </div>
        </div>""", unsafe_allow_html=True)

        with st.expander("▶  Running locally? Enter your key here"):
            api_key = st.text_input("FRED API Key", type="password", placeholder="Paste key…")
            if not api_key:
                st.stop()
        if not api_key:
            st.stop()

    # ── Load all series ───────────────────────────────────────────────────────
    all_items = [item for sec in INDICATORS.values() for item in sec["items"]]
    id_list   = [i["id"] for i in all_items]

    with st.spinner("Loading market data from FRED…"):
        raw = {sid: load_series(api_key, sid, 60) for sid in id_list}

    stats_map = {}
    for item in all_items:
        s    = raw[item["id"]]
        mode = item["mode"]
        if mode == "yoy":
            s_display = yoy_series(raw[item["id"]])
        elif mode == "diff":
            s_display = diff_series(raw[item["id"]])
        else:
            s_display = s
        stats_map[item["id"]] = compute_stats(s_display.dropna(), mode)

    # ── Yield Curve Hero ──────────────────────────────────────────────────────
    yc = raw.get("T10Y2Y", pd.Series(dtype=float))
    if not yc.empty:
        yc_val  = float(yc.iloc[-1])
        yc_date = str(yc.index[-1])[:10]
        inv     = yc_val < 0
        hero_color  = "#d13438" if inv else "#107c10"
        hero_bg     = "rgba(209,52,56,0.08)" if inv else "rgba(16,124,16,0.08)"
        badge_color = "#f1707a" if inv else "#6ccb5f"
        badge_label = "⚠ INVERTED — Recession Signal" if inv else "✓ NORMAL — Upward Slope"
        note        = "Historically precedes recession by ~12–18 months" if inv else "No inversion signal"

        dgs10_val = float(raw["DGS10"].iloc[-1]) if "DGS10" in raw and not raw["DGS10"].empty else 0
        dgs2_val  = float(raw["DGS2"].iloc[-1])  if "DGS2"  in raw and not raw["DGS2"].empty  else 0

        st.markdown(f"""
        <div style="background:{hero_bg};border:1px solid {hero_color}33;
                    border-left:4px solid {hero_color};border-radius:4px;
                    padding:16px 22px;margin:12px 0 16px 0;
                    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
          <div>
            <div style="font-size:10px;color:#8a8a9a;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px">
              YIELD CURVE · 2s/10s SPREAD
            </div>
            <div style="font-size:42px;font-weight:700;color:{badge_color};line-height:1">
              {'+' if yc_val >= 0 else ''}{yc_val:.2f}%
            </div>
            <div style="font-size:11px;color:#8a8a9a;margin-top:4px">
              10yr {dgs10_val:.2f}% &nbsp;·&nbsp; 2yr {dgs2_val:.2f}% &nbsp;·&nbsp; {yc_date}
            </div>
          </div>
          <div style="text-align:right">
            <div style="display:inline-block;background:{badge_color};color:#fff;
                        font-weight:700;font-size:12px;padding:6px 18px;border-radius:20px;letter-spacing:0.5px">
              {badge_label}
            </div>
            <div style="font-size:11px;color:#8a8a9a;margin-top:6px">{note}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📋 Overview", "📈 Charts", "🛢 Resin Chain", "📊 Comparisons"])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 — OVERVIEW (KPI grid)
    # ════════════════════════════════════════════════════════════════
    with tabs[0]:
        for sec_id, sec in INDICATORS.items():
            st.markdown(f"""
            <div class="section-header" style="border-left-color:{sec['color']}">
              {sec['label']}
              <span style="font-size:10px;color:#5a5a7a;font-weight:400;margin-left:10px">
                {sec['desc']}
              </span>
            </div>""", unsafe_allow_html=True)

            cols = st.columns(min(len(sec["items"]), 4))
            for j, item in enumerate(sec["items"]):
                with cols[j % 4]:
                    st.markdown(kpi_html(item, stats_map.get(item["id"], {})),
                                unsafe_allow_html=True)
            if len(sec["items"]) > 4:
                cols2 = st.columns(min(len(sec["items"]) - 4, 4))
                for j, item in enumerate(sec["items"][4:]):
                    with cols2[j % 4]:
                        st.markdown(kpi_html(item, stats_map.get(item["id"], {})),
                                    unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 2 — CHARTS
    # ════════════════════════════════════════════════════════════════
    with tabs[1]:
        chart_cols = st.columns(2)

        # Yield Curve history
        with chart_cols[0]:
            yc_full = load_series(api_key, "T10Y2Y", 600)
            if not yc_full.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=yc_full.index, y=yc_full.values, name="2s/10s Spread",
                    line=dict(color="#0078d4", width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(0,120,212,0.08)"
                ))
                fig.add_hline(y=0, line_width=1.5, line_color="#d13438",
                              line_dash="dot", annotation_text="0% — Inversion line",
                              annotation_font_color="#d13438", annotation_font_size=10)
                fig.update_layout(**PLOT_LAYOUT,
                                  title=dict(text="Yield Curve (2s/10s) — Full History", font=dict(size=13), x=0))
                st.plotly_chart(fig, use_container_width=True)

        # Inflation dashboard
        with chart_cols[1]:
            inf_ids  = ["CPIAUCSL", "CPILFESL", "PCEPI", "PCEPILFE"]
            inf_lbls = ["CPI Headline", "Core CPI", "PCE", "Core PCE"]
            inf_data = {}
            for sid, lbl in zip(inf_ids, inf_lbls):
                s = load_series(api_key, sid, 60)
                if not s.empty:
                    inf_data[lbl] = yoy_series(s).dropna()
            fig = make_line_chart(inf_data, "Inflation Metrics — YoY %", yformat=".1f")
            fig.add_hline(y=2, line_width=1, line_dash="dash", line_color="#ffb900",
                          annotation_text="Fed 2% target",
                          annotation_font_color="#ffb900", annotation_font_size=10)
            st.plotly_chart(fig, use_container_width=True)

        # Payrolls bar
        with chart_cols[0]:
            pay = load_series(api_key, "PAYEMS", 36)
            if not pay.empty:
                st.plotly_chart(
                    make_bar_chart(diff_series(pay).dropna().iloc[-24:],
                                   "Nonfarm Payrolls — MoM Change (K)"),
                    use_container_width=True
                )

        # Energy prices
        with chart_cols[1]:
            energy_data = {}
            for sid, lbl in [("DCOILWTICO","WTI Crude"), ("DCOILBRENTEU","Brent"),
                             ("DHHNGSP","Henry Hub NG"), ("DPROPANEMBTX","Propane")]:
                s = load_series(api_key, sid, 60)
                if not s.empty:
                    energy_data[lbl] = s

            if energy_data:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                for i, (name, s) in enumerate(energy_data.items()):
                    use_secondary = name in ("Henry Hub NG", "Propane")
                    fig.add_trace(
                        go.Scatter(x=s.index, y=s.values, name=name,
                                   line=dict(color=LINE_COLORS[i], width=2)),
                        secondary_y=use_secondary
                    )
                fig.update_layout(**PLOT_LAYOUT, title=dict(text="Energy & Feedstock Prices", font=dict(size=13), x=0))
                fig.update_yaxes(title_text="$/bbl", secondary_y=False,
                                 gridcolor="#1e2a3a", tickfont=dict(size=10))
                fig.update_yaxes(title_text="$/MMBtu / $/gal", secondary_y=True,
                                 tickfont=dict(size=10))
                st.plotly_chart(fig, use_container_width=True)

        # PMI + Housing
        with chart_cols[0]:
            pmi_data = {}
            for sid, lbl in [("NAPM","ISM PMI"), ("UMCSENT","Consumer Sentiment")]:
                s = load_series(api_key, sid, 60)
                if not s.empty:
                    pmi_data[lbl] = s
            fig = make_line_chart(pmi_data, "PMI & Consumer Sentiment", yformat=".1f")
            fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="#ffb900",
                          annotation_text="50 = Expansion/Contraction",
                          annotation_font_color="#ffb900", annotation_font_size=10)
            st.plotly_chart(fig, use_container_width=True)

        # GDP
        with chart_cols[1]:
            gdp = load_series(api_key, "A191RL1Q225SBEA", 40)
            if not gdp.empty:
                st.plotly_chart(
                    make_bar_chart(gdp.iloc[-20:], "Real GDP Growth — Annualized %"),
                    use_container_width=True
                )

    # ════════════════════════════════════════════════════════════════
    # TAB 3 — RESIN CHAIN
    # ════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown("""
        <div style="background:#16213e;border:1px solid #0f3460;border-radius:4px;
                    padding:14px 18px;margin-bottom:16px;font-size:12px;color:#8a8a9a">
          <b style="color:#c8d0e0">Feedstock Cost Chain:</b>
          &nbsp; Energy &nbsp;→&nbsp; Feedstock &nbsp;→&nbsp; Monomer &nbsp;→&nbsp; Resin
          <span style="margin-left:18px;color:#5a5a7a">
            WTI/Nat Gas → Ethane/Propane → Ethylene/PGP → PE/PP/PVC
          </span>
        </div>""", unsafe_allow_html=True)

        rc_cols = st.columns(2)

        with rc_cols[0]:
            # Resin PPI
            ppi_data = {}
            for sid, lbl in [("PCU325211325211","Resin Mfg PPI"),
                             ("WPU0662","Thermoplastic PPI"),
                             ("PCU3252113252111","Thermoplastic Ind PPI")]:
                s = load_series(api_key, sid, 60)
                if not s.empty:
                    ppi_data[lbl] = yoy_series(s).dropna()
            fig = make_line_chart(ppi_data, "Resin PPI Indices — YoY %", yformat=".1f")
            fig.add_hline(y=0, line_width=1, line_color="#3a3a5a")
            st.plotly_chart(fig, use_container_width=True)

        with rc_cols[1]:
            # WTI vs Nat Gas (dual axis)
            wti  = load_series(api_key, "DCOILWTICO", 60)
            ngas = load_series(api_key, "DHHNGSP",    60)
            if not wti.empty and not ngas.empty:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(x=wti.index, y=wti.values, name="WTI Crude ($/bbl)",
                                         line=dict(color="#0078d4", width=2)), secondary_y=False)
                fig.add_trace(go.Scatter(x=ngas.index, y=ngas.values, name="Henry Hub ($/MMBtu)",
                                         line=dict(color="#ffb900", width=2)), secondary_y=True)
                fig.update_layout(**PLOT_LAYOUT,
                                  title=dict(text="Primary Feedstock Costs", font=dict(size=13), x=0))
                fig.update_yaxes(title_text="WTI $/bbl", secondary_y=False,
                                 gridcolor="#1e2a3a", tickfont=dict(size=10))
                fig.update_yaxes(title_text="NG $/MMBtu", secondary_y=True, tickfont=dict(size=10))
                st.plotly_chart(fig, use_container_width=True)

        with rc_cols[0]:
            # Auto sales + inv/sales ratio
            auto = load_series(api_key, "TOTALSA",  36)
            inv  = load_series(api_key, "ISRATIO",  36)
            if not auto.empty:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(x=auto.index, y=auto.values, name="Auto Sales SAAR (M)",
                                         line=dict(color="#6ccb5f", width=2)), secondary_y=False)
                if not inv.empty:
                    fig.add_trace(go.Scatter(x=inv.index, y=inv.values, name="Inventory/Sales Ratio",
                                             line=dict(color="#f1707a", width=2)), secondary_y=True)
                fig.update_layout(**PLOT_LAYOUT,
                                  title=dict(text="Resin Demand — Auto Sales & Inv Ratio", font=dict(size=13), x=0))
                fig.update_yaxes(title_text="M/yr SAAR", secondary_y=False,
                                 gridcolor="#1e2a3a", tickfont=dict(size=10))
                fig.update_yaxes(title_text="Ratio", secondary_y=True, tickfont=dict(size=10))
                st.plotly_chart(fig, use_container_width=True)

        with rc_cols[1]:
            # Housing → PVC demand lead
            houst  = load_series(api_key, "HOUST",  60)
            permit = load_series(api_key, "PERMIT", 60)
            if not houst.empty:
                fig = make_line_chart(
                    {"Housing Starts (K)": houst, "Building Permits (K)": permit},
                    "Housing Starts & Permits — PVC Demand Lead (60–90d)",
                    yformat=",.0f"
                )
                st.plotly_chart(fig, use_container_width=True)

        # Paid data info cards
        st.markdown("""
        <div class="section-header" style="border-left-color:#5a5a6a">
          Spot / Contract Prices — Paid Data Sources Required
        </div>""", unsafe_allow_html=True)

        paid = [
            ("Ethylene (¢/lb)",    "OPIS / PetroChemWire (PCW)",     "opisnet.com"),
            ("PGP Propylene (¢/lb)","OPIS / PCW — drives PP contract","opisnet.com"),
            ("PE — HDPE/LLDPE/LDPE","ICIS or The Plastics Exchange",  "plasticsexchange.com"),
            ("Polypropylene (PP)",  "ICIS or Resintel / PT Online",   "ptonline.com/resin-pricing"),
            ("PVC Resin (¢/lb)",    "OPIS / PCW or ICIS",             "opisnet.com"),
            ("PET Resin (¢/lb)",    "ICIS — tied to paraxylene",      "icis.com"),
            ("Polystyrene / ABS",   "ICIS — benzene + ethylene",      "icis.com"),
        ]
        pcols = st.columns(4)
        for k, (label, source, link) in enumerate(paid):
            with pcols[k % 4]:
                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.5);border:1px solid #1e2a3a;
                            border-radius:4px;padding:12px 14px;margin-bottom:8px">
                  <div style="font-size:11px;color:#5a5a7a;font-weight:600;margin-bottom:4px">{label}</div>
                  <div style="font-size:10px;color:#3a3a5a;line-height:1.5">{source}</div>
                  <div style="font-size:9px;color:#0078d4;margin-top:3px">{link} →</div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 4 — COMPARISONS
    # ════════════════════════════════════════════════════════════════
    with tabs[3]:
        comp_cols = st.columns(2)

        with comp_cols[0]:
            # Fed Funds vs 10yr
            ff   = load_series(api_key, "FEDFUNDS", 60)
            t10  = load_series(api_key, "DGS10",    600)
            t2   = load_series(api_key, "DGS2",     600)
            fig  = make_line_chart(
                {"Fed Funds": ff, "10-Yr Treasury": t10, "2-Yr Treasury": t2},
                "Interest Rate Landscape", yformat=".2f"
            )
            st.plotly_chart(fig, use_container_width=True)

        with comp_cols[1]:
            # Unemployment + Wage pressure
            ur   = load_series(api_key, "UNRATE", 60)
            wage = load_series(api_key, "AHETPI", 60)
            fig  = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=ur.index, y=ur.values, name="Unemployment %",
                                     line=dict(color="#f1707a", width=2)), secondary_y=False)
            if not wage.empty:
                fig.add_trace(go.Scatter(x=wage.index, y=yoy_series(wage).dropna().values,
                                         x=yoy_series(wage).dropna().index,
                                         name="Wage Growth YoY%",
                                         line=dict(color="#ffb900", width=2)), secondary_y=True)
            fig.update_layout(**PLOT_LAYOUT,
                              title=dict(text="Labor Market — Unemployment vs Wages", font=dict(size=13), x=0))
            fig.update_yaxes(title_text="Unemployment %", secondary_y=False,
                             gridcolor="#1e2a3a", tickfont=dict(size=10))
            fig.update_yaxes(title_text="Wage YoY %", secondary_y=True, tickfont=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)

        with comp_cols[0]:
            vix    = load_series(api_key, "VIXCLS",       240)
            spread = load_series(api_key, "BAMLH0A0HYM2", 240)
            fig    = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=vix.index, y=vix.values, name="VIX",
                                     line=dict(color="#c586c0", width=1.5)), secondary_y=False)
            if not spread.empty:
                fig.add_trace(go.Scatter(x=spread.index, y=spread.values, name="HY Spread %",
                                         line=dict(color="#e06c75", width=1.5)), secondary_y=True)
            fig.add_hline(y=25, line_dash="dash", line_color="#ffb900", line_width=1,
                          annotation_text="VIX 25 — Stress", annotation_font_color="#ffb900",
                          annotation_font_size=9)
            fig.update_layout(**PLOT_LAYOUT,
                              title=dict(text="Risk Gauges — VIX & HY Credit Spread", font=dict(size=13), x=0))
            fig.update_yaxes(title_text="VIX", secondary_y=False,
                             gridcolor="#1e2a3a", tickfont=dict(size=10))
            fig.update_yaxes(title_text="HY Spread %", secondary_y=True, tickfont=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)

        with comp_cols[1]:
            retail = load_series(api_key, "RSAFS",   60)
            indpro = load_series(api_key, "INDPRO",  60)
            fig    = make_line_chart(
                {"Retail Sales YoY%":    yoy_series(retail).dropna(),
                 "Industrial Prod YoY%": yoy_series(indpro).dropna()},
                "Consumer vs Industrial Activity — YoY %", yformat=".1f"
            )
            fig.add_hline(y=0, line_width=1, line_color="#3a3a5a")
            st.plotly_chart(fig, use_container_width=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #1e2a3a;
                font-size:10px;color:#2a2a4a;display:flex;justify-content:space-between">
      <span>Data: Federal Reserve Economic Data (FRED) · St. Louis Fed</span>
      <span>Last loaded: {datetime.now().strftime('%b %d %Y, %H:%M')}</span>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
