import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="AB Skyros 1082",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
  --bg:      #0f1117;
  --surface: #181c24;
  --border:  #2a2f3d;
  --muted:   #4a5268;
  --dim:     #8892a4;
  --text:    #e8eaf0;
  --green:   #22c55e;
  --blue:    #3b82f6;
  --amber:   #f59e0b;
  --red:     #ef4444;
  --mono:    'IBM Plex Mono', monospace;
  --sans:    'IBM Plex Sans', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  font-family: var(--sans) !important;
  background: var(--bg) !important;
  color: var(--text) !important;
  font-size: 14px !important;
}
.stApp { background: var(--bg) !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }

/* Tight single-screen layout */
.block-container {
  padding: 1.2rem 1rem 1rem !important;
  max-width: 420px !important;
  margin: 0 auto !important;
}

/* ── TOP BAR ── */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: .9rem;
}
.tb-store {
  font-family: var(--mono);
  font-size: .65rem;
  font-weight: 600;
  letter-spacing: .12em;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: .2rem;
}
.tb-title {
  font-family: var(--mono);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -.01em;
}
.tb-date {
  text-align: right;
  font-family: var(--mono);
  font-size: .6rem;
  color: var(--muted);
  line-height: 1.7;
}

/* ── WEEK ROW ── */
.week-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: .8rem;
}
.wr-cell {
  background: var(--surface);
  padding: .65rem .8rem;
}
.wr-lbl {
  font-size: .52rem;
  font-weight: 600;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: .25rem;
}
.wr-val {
  font-family: var(--mono);
  font-size: .85rem;
  font-weight: 500;
  color: var(--text);
}
.wr-val.g { color: var(--green); }
.wr-val.b { color: var(--blue); }

/* ── MODULE CARD ── */
.mcard {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: .75rem;
  overflow: hidden;
}
.mc-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .6rem .9rem;
  border-bottom: 1px solid var(--border);
}
.mc-name {
  font-family: var(--mono);
  font-size: .72rem;
  font-weight: 600;
  letter-spacing: .04em;
  color: var(--text);
}
.mc-tag {
  font-size: .52rem;
  font-weight: 600;
  letter-spacing: .12em;
  text-transform: uppercase;
  padding: .15rem .5rem;
  border-radius: 3px;
}
.tag-live { background: rgba(34,197,94,.12); color: var(--green); }
.tag-warn { background: rgba(245,158,11,.12); color: var(--amber); }
.tag-idle { background: rgba(74,82,104,.2);   color: var(--muted); }

.mc-body { padding: .65rem .9rem; }
.mc-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: .28rem 0;
  border-bottom: 1px solid rgba(42,47,61,.6);
}
.mc-row:last-child { border-bottom: none; }
.mc-key {
  font-size: .58rem;
  font-weight: 500;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--muted);
}
.mc-val {
  font-family: var(--mono);
  font-size: .78rem;
  font-weight: 500;
  color: var(--text);
}
.mc-val.hero { font-size: .92rem; color: var(--green); }
.mc-val.blue { font-size: .92rem; color: var(--blue); }
.mc-val.dim  { color: var(--muted); font-style: italic; }

/* ── NAV BUTTONS ── */
.nav-row { display: grid; grid-template-columns: 1fr 1fr; gap: .6rem; }
.stButton > button {
  width: 100% !important;
  border-radius: 5px !important;
  font-family: var(--mono) !important;
  font-size: .72rem !important;
  font-weight: 600 !important;
  letter-spacing: .06em !important;
  padding: .6rem 1rem !important;
  transition: all .12s !important;
}
.btn-g > button {
  background: rgba(34,197,94,.1) !important;
  border: 1px solid rgba(34,197,94,.3) !important;
  color: var(--green) !important;
}
.btn-g > button:hover { background: rgba(34,197,94,.2) !important; }
.btn-b > button {
  background: rgba(59,130,246,.1) !important;
  border: 1px solid rgba(59,130,246,.3) !important;
  color: var(--blue) !important;
}
.btn-b > button:hover { background: rgba(59,130,246,.2) !important; }

.foot {
  font-family: var(--mono);
  font-size: .52rem;
  letter-spacing: .1em;
  color: var(--muted);
  text-align: center;
  padding-top: .6rem;
  border-top: 1px solid var(--border);
  margin-top: .6rem;
}

@media(max-width: 380px) {
  .block-container { padding: .8rem .75rem !important; }
  .week-row { grid-template-columns: 1fr 1fr; }
}
</style>
""", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
DAYS_GR  = ["ΔΕΥ","ΤΡΙ","ΤΕΤ","ΠΕΜ","ΠΑΡ","ΣΑΒ","ΚΥΡ"]
MONTHS_GR = ["ΙΑΝ","ΦΕΒ","ΜΑΡ","ΑΠΡ","ΜΑΙ","ΙΟΥ","ΙΟΥ","ΑΥΓ","ΣΕΠ","ΟΚΤ","ΝΟΕ","ΔΕΚ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

today    = date.today()
week_mon = today - timedelta(days=today.weekday())
week_sun = week_mon + timedelta(days=6)
wlbl     = f"{week_mon.strftime('%d/%m')}–{week_sun.strftime('%d/%m')}"

df_s = pd.DataFrame()
if os.path.exists(SALES_CACHE):
    try:
        t = pd.read_csv(SALES_CACHE)
        if not t.empty:
            t["date"] = pd.to_datetime(t["date"]).dt.date
            df_s = (t.sort_values("net_sales", ascending=False)
                     .drop_duplicates("date", keep="first")
                     .sort_values("date", ascending=False)
                     .reset_index(drop=True))
    except: pass

df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        t = pd.read_csv(INV_CACHE)
        if not t.empty:
            t["DATE"] = pd.to_datetime(t["DATE"])
            df_i = t
    except: pass

# ── COMPUTE ───────────────────────────────────────────────────────────────────
s_val = s_date = s_cust = s_days = None
s_week = 0; s_wdays = 0
if not df_s.empty:
    r       = df_s.iloc[0]
    s_val   = r.get("net_sales")
    s_date  = r.get("date")
    s_cust  = int(r["customers"]) if pd.notna(r.get("customers")) else None
    s_days  = (today - s_date).days if s_date else None
    wm      = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    s_week  = wm["net_sales"].sum() if not wm.empty else 0
    s_wdays = len(wm)

inv_week = inv_month = None
if not df_i.empty:
    wdt = datetime.combine(week_mon, datetime.min.time())
    wet = datetime.combine(today,    datetime.max.time())
    wi  = df_i[(df_i["DATE"]>=wdt)&(df_i["DATE"]<=wet)]
    if not wi.empty:
        inv_week = (wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                  - wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())
    mi = df_i[(df_i["DATE"].dt.month==today.month)&(df_i["DATE"].dt.year==today.year)]
    if not mi.empty:
        inv_month = (mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                   - mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())

# ── RENDER ────────────────────────────────────────────────────────────────────
dy  = DAYS_GR[today.weekday()]
mon = MONTHS_GR[today.month-1]

st.markdown(f"""
<div class="topbar">
  <div>
    <div class="tb-store">AB Skyros · 1082</div>
    <div class="tb-title">Operations Hub</div>
  </div>
  <div class="tb-date">{dy} {today.day} {mon}<br>{today.year}</div>
</div>
""", unsafe_allow_html=True)

# Week row
sw_c = "g" if s_week else ""
iw_c = "b" if inv_week is not None else ""
st.markdown(f"""
<div class="week-row">
  <div class="wr-cell">
    <div class="wr-lbl">Εβδ. Πωλήσεις</div>
    <div class="wr-val {sw_c}">{fmt(s_week) if s_week else "—"}</div>
  </div>
  <div class="wr-cell">
    <div class="wr-lbl">Καθ. Τιμολ.</div>
    <div class="wr-val {iw_c}">{fmt(inv_week) if inv_week is not None else "—"}</div>
  </div>
  <div class="wr-cell">
    <div class="wr-lbl">Ημ. {wlbl}</div>
    <div class="wr-val">{s_wdays}/7</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Sales card
if s_days == 0: s_tag, s_tc = "LIVE", "tag-live"
elif s_days and s_days <= 2: s_tag, s_tc = f"–{s_days}D", "tag-warn"
elif s_date: s_tag, s_tc = f"–{s_days}D", "tag-idle"
else: s_tag, s_tc = "N/A", "tag-idle"

st.markdown(f'<div class="mcard"><div class="mc-hdr"><span class="mc-name">ΠΩΛΗΣΕΙΣ</span><span class="mc-tag {s_tc}">{s_tag}</span></div><div class="mc-body">', unsafe_allow_html=True)
if s_val:
    dl = s_date.strftime("%d/%m/%Y")
    st.markdown(f"""
    <div class="mc-row"><span class="mc-key">Τελευταία · {dl}</span><span class="mc-val hero">{fmt(s_val)}</span></div>
    <div class="mc-row"><span class="mc-key">Πελάτες</span><span class="mc-val">{s_cust if s_cust else '—'}</span></div>
    <div class="mc-row"><span class="mc-key">Εβδομάδα {wlbl}</span><span class="mc-val hero">{fmt(s_week) if s_week else '—'}</span></div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="mc-row"><span class="mc-val dim">Χωρίς δεδομένα</span></div>', unsafe_allow_html=True)
st.markdown('</div></div>', unsafe_allow_html=True)

# Invoices card
i_tag, i_tc = ("OK","tag-live") if (inv_week is not None or inv_month is not None) else ("N/A","tag-idle")
st.markdown(f'<div class="mcard"><div class="mc-hdr"><span class="mc-name">ΤΙΜΟΛΟΓΙΑ</span><span class="mc-tag {i_tc}">{i_tag}</span></div><div class="mc-body">', unsafe_allow_html=True)
if inv_week is not None or inv_month is not None:
    mn_lbl = MONTHS_GR[today.month-1]
    if inv_week is not None:
        st.markdown(f'<div class="mc-row"><span class="mc-key">Εβδομάδα {wlbl}</span><span class="mc-val blue">{fmt(inv_week)}</span></div>', unsafe_allow_html=True)
    if inv_month is not None:
        st.markdown(f'<div class="mc-row"><span class="mc-key">Μήνας {mn_lbl}</span><span class="mc-val">{fmt(inv_month)}</span></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="mc-row"><span class="mc-val dim">Χωρίς δεδομένα</span></div>', unsafe_allow_html=True)
st.markdown('</div></div>', unsafe_allow_html=True)

# Nav
st.markdown('<div class="nav-row">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("ΠΩΛΗΣΕΙΣ", use_container_width=True):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("ΤΙΜΟΛΟΓΙΑ", use_container_width=True):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="foot">AB SKYROS 1082 · OPERATIONS PLATFORM · {today.strftime("%Y")}</div>', unsafe_allow_html=True)
