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
  --bg:       #1e2128;
  --surface:  #272b34;
  --surface2: #2e333d;
  --border:   #383d4a;
  --muted:    #5a6070;
  --dim:      #8a909e;
  --text:     #d4d8e0;
  --text-hi:  #eceef2;
  --green:    #4ade80;
  --blue:     #60a5fa;
  --amber:    #fbbf24;
  --mono:     'IBM Plex Mono', monospace;
  --sans:     'IBM Plex Sans', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  font-family: var(--sans) !important;
  background: var(--bg) !important;
  color: var(--text) !important;
}
.stApp { background: var(--bg) !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }

/* ─── LAYOUT WRAPPER ─── */
.block-container {
  padding: 0 !important;
  max-width: 100% !important;
}
.hub {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.6rem 1.5rem 2rem;
}

/* ─── TOPBAR ─── */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: .9rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.2rem;
}
.tb-left {}
.tb-eyebrow {
  font-family: var(--mono);
  font-size: .58rem;
  font-weight: 600;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: .25rem;
}
.tb-title {
  font-family: var(--mono);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-hi);
  letter-spacing: -.01em;
}
.tb-right {
  text-align: right;
  font-family: var(--mono);
  font-size: .6rem;
  color: var(--dim);
  line-height: 1.8;
}

/* ─── WEEK STRIP ─── */
.week-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 1.2rem;
}
.ws-cell {
  background: var(--surface);
  padding: .75rem 1rem;
}
.ws-label {
  font-size: .52rem;
  font-weight: 600;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: .3rem;
}
.ws-val {
  font-family: var(--mono);
  font-size: .88rem;
  font-weight: 500;
  color: var(--text);
}
.ws-val.g { color: var(--green); }
.ws-val.b { color: var(--blue); }
.ws-val.d { color: var(--dim); font-size: .75rem; }

/* ─── MODULE GRID ─── */
.mod-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr 1fr;   /* desktop: 2 columns */
  margin-bottom: 1.1rem;
}

/* ─── MODULE CARD ─── */
.mcard {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}
.mc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .65rem 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
}
.mc-title {
  font-family: var(--mono);
  font-size: .72rem;
  font-weight: 600;
  letter-spacing: .05em;
  color: var(--text-hi);
}
.mc-badge {
  font-family: var(--mono);
  font-size: .52rem;
  font-weight: 600;
  letter-spacing: .12em;
  text-transform: uppercase;
  padding: .15rem .5rem;
  border-radius: 3px;
}
.b-live { background: rgba(74,222,128,.12); color: var(--green); border: 1px solid rgba(74,222,128,.2); }
.b-warn { background: rgba(251,191,36,.1);  color: var(--amber); border: 1px solid rgba(251,191,36,.2); }
.b-idle { background: rgba(90,96,112,.15);  color: var(--muted); border: 1px solid var(--border); }

.mc-body { padding: .6rem 1rem .8rem; }

/* Desktop rows */
.mc-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: .3rem 0;
  border-bottom: 1px solid rgba(56,61,74,.5);
}
.mc-row:last-child { border-bottom: none; }
.mc-key {
  font-size: .58rem;
  font-weight: 500;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--dim);
}
.mc-val {
  font-family: var(--mono);
  font-size: .82rem;
  font-weight: 500;
  color: var(--text);
}
.mc-val.hero { font-size: 1rem; color: var(--green); }
.mc-val.blue { font-size: 1rem; color: var(--blue); }
.mc-val.dim  { color: var(--muted); font-style: italic; font-size: .72rem; }

/* Mobile: hide secondary rows */
.mc-row.secondary { display: flex; }

/* ─── NAV BUTTONS ─── */
.nav-row { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }
.stButton > button {
  width: 100% !important;
  border-radius: 5px !important;
  font-family: var(--mono) !important;
  font-size: .72rem !important;
  font-weight: 600 !important;
  letter-spacing: .06em !important;
  padding: .65rem 1rem !important;
  transition: all .12s !important;
  text-transform: uppercase !important;
}
.btn-g > button {
  background: rgba(74,222,128,.1) !important;
  border: 1px solid rgba(74,222,128,.25) !important;
  color: var(--green) !important;
}
.btn-g > button:hover { background: rgba(74,222,128,.18) !important; }
.btn-b > button {
  background: rgba(96,165,250,.1) !important;
  border: 1px solid rgba(96,165,250,.25) !important;
  color: var(--blue) !important;
}
.btn-b > button:hover { background: rgba(96,165,250,.18) !important; }

.foot {
  font-family: var(--mono);
  font-size: .52rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
  text-align: center;
  padding-top: .8rem;
  border-top: 1px solid var(--border);
  margin-top: .5rem;
}

/* ═══════════════════════════════════
   MOBILE  ≤ 640px
   ─ single column
   ─ week strip 2 cols
   ─ hide secondary data rows
   ─ smaller font
═══════════════════════════════════ */
@media (max-width: 640px) {
  .hub { padding: 1rem .9rem 1.5rem; }

  .tb-title { font-size: .95rem; }
  .tb-right { display: none; }       /* hide date on mobile — saves space */

  .week-strip { grid-template-columns: 1fr 1fr; }
  .ws-cell:nth-child(3),
  .ws-cell:nth-child(4) { display: none; }  /* hide last 2 cells on mobile */

  .mod-grid { grid-template-columns: 1fr; gap: .7rem; }

  .mc-row.secondary { display: none; }  /* hide secondary rows on mobile */

  .mc-val.hero { font-size: .88rem; }
  .mc-val.blue { font-size: .88rem; }

  .nav-row { gap: .5rem; }
  .stButton > button { padding: .55rem .8rem !important; font-size: .68rem !important; }
}

/* ═══════════════════════════════════
   TABLET  641px – 900px
   ─ 2-col grid
   ─ week strip 3 cols
═══════════════════════════════════ */
@media (min-width: 641px) and (max-width: 900px) {
  .week-strip { grid-template-columns: repeat(3, 1fr); }
  .ws-cell:last-child { display: none; }
}
</style>
""", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

today    = date.today()
week_mon = today - timedelta(days=today.weekday())
week_sun = week_mon + timedelta(days=6)
wlbl     = f"{week_mon.strftime('%d/%m')} – {week_sun.strftime('%d/%m')}"

# Load sales
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

# Load invoices
df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        t = pd.read_csv(INV_CACHE)
        if not t.empty:
            t["DATE"] = pd.to_datetime(t["DATE"])
            df_i = t
    except: pass

# ── COMPUTE ───────────────────────────────────────────────────────────────────
s_val = s_date = s_cust = s_avg = s_days = None
s_week = s_month = 0
s_wdays = 0

if not df_s.empty:
    r        = df_s.iloc[0]
    s_val    = r.get("net_sales")
    s_date   = r.get("date")
    s_cust   = int(r["customers"])   if pd.notna(r.get("customers"))   else None
    s_avg    = r.get("avg_basket")   if pd.notna(r.get("avg_basket"))  else None
    s_days   = (today - s_date).days if s_date else None
    wm = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    s_week   = wm["net_sales"].sum() if not wm.empty else 0
    s_wdays  = len(wm)
    mm = df_s[(df_s["date"] >= date(today.year,today.month,1)) & (df_s["date"] <= today)]
    s_month  = mm["net_sales"].sum() if not mm.empty else 0

inv_week = inv_month = None
if not df_i.empty:
    wdt = datetime.combine(week_mon, datetime.min.time())
    wet = datetime.combine(today,    datetime.max.time())
    wi  = df_i[(df_i["DATE"] >= wdt) & (df_i["DATE"] <= wet)]
    if not wi.empty:
        inv_week = (wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                  - wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())
    mi = df_i[(df_i["DATE"].dt.month==today.month)&(df_i["DATE"].dt.year==today.year)]
    if not mi.empty:
        inv_month = (mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                   - mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())

# ── BUILD PAGE ────────────────────────────────────────────────────────────────
day_gr  = DAYS_GR[today.weekday()]
mon_gr  = MONTHS_GR[today.month-1]
date_str = f"{day_gr}, {today.day} {mon_gr} {today.year}"

# Status badges
if s_days == 0:     s_badge, s_bcls = "LIVE", "b-live"
elif s_days and s_days <= 2: s_badge, s_bcls = f"–{s_days}D", "b-warn"
elif s_date:        s_badge, s_bcls = f"–{s_days}D", "b-idle"
else:               s_badge, s_bcls = "N/A",  "b-idle"

i_badge = "OK"  if (inv_week is not None) else "N/A"
i_bcls  = "b-live" if (inv_week is not None) else "b-idle"

# Helpers
def _val(v, cls=""):   return f'<span class="mc-val {cls}">{v}</span>'
def _row(k, v, cls="", secondary=False):
    sec = " secondary" if secondary else ""
    return f'<div class="mc-row{sec}"><span class="mc-key">{k}</span>{_val(v,cls)}</div>'
def _empty():
    return '<div class="mc-row"><span class="mc-val dim">Χωρίς δεδομένα</span></div>'

st.markdown('<div class="hub">', unsafe_allow_html=True)

# Topbar
st.markdown(f"""
<div class="topbar">
  <div class="tb-left">
    <div class="tb-eyebrow">AB Skyros · Κατάστημα 1082</div>
    <div class="tb-title">Operations Hub</div>
  </div>
  <div class="tb-right">{date_str}<br>Εβδομάδα {wlbl}</div>
</div>
""", unsafe_allow_html=True)

# Week strip — 4 cells (some hidden on mobile/tablet via CSS)
sw_cls = "g" if s_week else "d"
iw_cls = "b" if inv_week is not None else "d"

st.markdown(f"""
<div class="week-strip">
  <div class="ws-cell">
    <div class="ws-label">Πωλήσεις Εβδ.</div>
    <div class="ws-val {sw_cls}">{fmt(s_week) if s_week else "—"}</div>
  </div>
  <div class="ws-cell">
    <div class="ws-label">Καθ. Τιμολ. Εβδ.</div>
    <div class="ws-val {iw_cls}">{fmt(inv_week) if inv_week is not None else "—"}</div>
  </div>
  <div class="ws-cell">
    <div class="ws-label">Πωλήσεις Μήνα</div>
    <div class="ws-val">{fmt(s_month) if s_month else "—"}</div>
  </div>
  <div class="ws-cell">
    <div class="ws-label">Ημέρες {wlbl}</div>
    <div class="ws-val">{s_wdays} / 7</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Module cards
st.markdown('<div class="mod-grid">', unsafe_allow_html=True)

# ── SALES CARD ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="mcard">
  <div class="mc-header">
    <span class="mc-title">ΠΩΛΗΣΕΙΣ ΚΑΤΑΣΤΗΜΑΤΟΣ</span>
    <span class="mc-badge {s_bcls}">{s_badge}</span>
  </div>
  <div class="mc-body">
""", unsafe_allow_html=True)

if s_val is not None:
    dl = s_date.strftime("%d/%m/%Y")
    st.markdown(
        _row(f"Τελευταία · {dl}", fmt(s_val), "hero") +
        _row("Πελάτες", str(s_cust) if s_cust else "—") +
        _row(f"Εβδομάδα {wlbl}", fmt(s_week) if s_week else "—", "g", secondary=True) +
        _row(f"Μήνας {mon_gr}", fmt(s_month) if s_month else "—", "", secondary=True) +
        _row("ΜΟ Καλαθιού", fmt(s_avg) if s_avg else "—", "", secondary=True),
        unsafe_allow_html=True
    )
else:
    st.markdown(_empty(), unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# ── INVOICES CARD ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="mcard">
  <div class="mc-header">
    <span class="mc-title">ΕΛΕΓΧΟΣ ΤΙΜΟΛΟΓΙΩΝ</span>
    <span class="mc-badge {i_bcls}">{i_badge}</span>
  </div>
  <div class="mc-body">
""", unsafe_allow_html=True)

if inv_week is not None or inv_month is not None:
    mn_full = MONTHS_GR[today.month-1]
    rows_html = ""
    if inv_week is not None:
        rows_html += _row(f"Καθαρό εβδ. {wlbl}", fmt(inv_week), "blue")
    if inv_month is not None:
        rows_html += _row(f"Καθαρό μήνα {mn_full}", fmt(inv_month), "", secondary=True)
    # last updated
    if not df_i.empty:
        last_inv = df_i["DATE"].max().strftime("%d/%m/%Y")
        rows_html += _row("Τελευταία εγγραφή", last_inv, "", secondary=True)
        cnt = len(df_i)
        rows_html += _row("Σύνολο εγγραφών", str(cnt), "", secondary=True)
    st.markdown(rows_html, unsafe_allow_html=True)
else:
    st.markdown(_empty(), unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # close mod-grid

# ── NAVIGATION ────────────────────────────────────────────────────────────────
st.markdown('<div class="nav-row">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("Πωλήσεις", use_container_width=True, key="gs"):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("Τιμολόγια", use_container_width=True, key="gi"):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="foot">AB Skyros 1082 · Operations Platform · {today.year}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # close hub
