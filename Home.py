import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="AB Skyros 1082 — Operations",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Geist:wght@300;400;500;600&display=swap');

:root {
  --ink:    #0d0d0d;
  --paper:  #f5f3ef;
  --rule:   #d6d2ca;
  --muted:  #8a8680;
  --accent: #1a472a;
  --accent2:#2c5282;
  --pos:    #1a472a;
  --neg:    #7f1d1d;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  font-family: 'Geist', sans-serif !important;
  background: var(--paper) !important;
  color: var(--ink) !important;
}
.stApp { background: var(--paper) !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
  padding: 3rem 2rem 6rem !important;
  max-width: 560px !important;
  margin: 0 auto !important;
}

/* ── MASTHEAD ── */
.masthead {
  border-top: 3px solid var(--ink);
  border-bottom: 1px solid var(--rule);
  padding: 1.4rem 0 1.2rem;
  margin-bottom: 2.4rem;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  gap: 1rem;
}
.mast-hed {
  font-family: 'DM Serif Display', serif;
  font-size: 2rem;
  line-height: 1;
  color: var(--ink);
  letter-spacing: -0.02em;
}
.mast-sub {
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 0.35rem;
}
.mast-date {
  text-align: right;
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  color: var(--muted);
  line-height: 1.6;
}

/* ── WEEK SUMMARY BAR ── */
.week-bar {
  display: grid;
  grid-template-columns: 1fr 1px 1fr 1px 1fr;
  border: 1px solid var(--rule);
  border-radius: 2px;
  margin-bottom: 1.8rem;
  background: #fff;
}
.wb-sep { background: var(--rule); }
.wb-cell { padding: 1rem 1.2rem; }
.wb-label {
  font-size: 0.57rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.3rem;
}
.wb-val {
  font-family: 'DM Serif Display', serif;
  font-size: 1.1rem;
  color: var(--ink);
  line-height: 1.1;
}
.wb-val.pos { color: var(--pos); }
.wb-val.neg { color: var(--ink); }
.wb-val.muted { color: var(--muted); font-family: 'Geist', sans-serif; font-size: .85rem; }

/* ── SECTION LABEL ── */
.section-lbl {
  font-size: 0.57rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
  padding-bottom: 0.45rem;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 1rem;
}

/* ── DATA CARD ── */
.dcard {
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: #fff;
  margin-bottom: 1rem;
  overflow: hidden;
}
.dcard-hdr {
  padding: 0.85rem 1.2rem;
  border-bottom: 1px solid var(--rule);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dcard-title {
  font-family: 'DM Serif Display', serif;
  font-size: 1.05rem;
  color: var(--ink);
}
.dcard-status {
  font-size: 0.6rem;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 0.18rem 0.6rem;
  border-radius: 1px;
}
.st-live { background: #dcfce7; color: var(--pos); }
.st-warn { background: #fef9c3; color: #78350f; }
.st-idle { background: #f3f4f6; color: var(--muted); }

.dcard-body { padding: 0.9rem 1.2rem; }

.stat-line {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0.42rem 0;
  border-bottom: 1px solid #f5f3ef;
}
.stat-line:last-child { border-bottom: none; }
.sl-key {
  font-size: 0.63rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.sl-val {
  font-family: 'DM Mono', monospace;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--ink);
}
.sl-val.hero {
  font-family: 'DM Serif Display', serif;
  font-size: 1.25rem;
  font-weight: 400;
  color: var(--pos);
}
.sl-val.blue {
  font-family: 'DM Serif Display', serif;
  font-size: 1.25rem;
  font-weight: 400;
  color: var(--accent2);
}
.empty-state {
  padding: 1.2rem 0;
  font-size: 0.72rem;
  color: var(--muted);
  font-style: italic;
}

/* ── NAV BUTTONS ── */
.nav-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.stButton > button {
  width: 100% !important;
  border-radius: 2px !important;
  font-family: 'Geist', sans-serif !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.04em !important;
  padding: 0.75rem 1rem !important;
  border: 1px solid var(--ink) !important;
  background: var(--ink) !important;
  color: var(--paper) !important;
  transition: all 0.12s !important;
}
.stButton > button:hover {
  background: var(--paper) !important;
  color: var(--ink) !important;
}

/* ── FOOTER RULE ── */
.foot-rule {
  border-top: 1px solid var(--rule);
  margin-top: 2rem;
  padding-top: 0.8rem;
  font-size: 0.58rem;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  text-align: center;
}

@media(max-width:420px) {
  .block-container { padding: 1.5rem 1rem 4rem !important; }
  .masthead { grid-template-columns: 1fr; }
  .mast-date { text-align: left; }
  .week-bar { grid-template-columns: 1fr; }
  .wb-sep { display: none; }
  .wb-cell { border-bottom: 1px solid var(--rule); }
  .wb-cell:last-child { border-bottom: none; }
}
</style>
""", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
DAYS_GR = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουαρίου","Φεβρουαρίου","Μαρτίου","Απριλίου","Μαΐου","Ιουνίου",
              "Ιουλίου","Αυγούστου","Σεπτεμβρίου","Οκτωβρίου","Νοεμβρίου","Δεκεμβρίου"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

today    = date.today()
week_mon = today - timedelta(days=today.weekday())
week_sun = week_mon + timedelta(days=6)
week_lbl = f"{week_mon.strftime('%d/%m')} — {week_sun.strftime('%d/%m/%Y')}"

df_s = pd.DataFrame()
if os.path.exists(SALES_CACHE):
    try:
        df_s = pd.read_csv(SALES_CACHE)
        if not df_s.empty:
            df_s["date"] = pd.to_datetime(df_s["date"]).dt.date
            df_s = (df_s.sort_values("net_sales", ascending=False)
                        .drop_duplicates("date", keep="first")
                        .sort_values("date", ascending=False)
                        .reset_index(drop=True))
    except: pass

df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        df_i = pd.read_csv(INV_CACHE)
        if not df_i.empty:
            df_i["DATE"] = pd.to_datetime(df_i["DATE"])
    except: pass

# Compute
s_val = s_date = s_cust = s_days = None
s_week = s_wdays = 0
if not df_s.empty:
    r = df_s.iloc[0]
    s_val   = r.get("net_sales"); s_date = r.get("date")
    s_cust  = int(r["customers"]) if pd.notna(r.get("customers")) else None
    s_days  = (today - s_date).days if s_date else None
    w = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    s_week  = w["net_sales"].sum() if not w.empty else 0
    s_wdays = len(w)

inv_week = inv_month = None
if not df_i.empty:
    wdt = datetime.combine(week_mon, datetime.min.time())
    wet = datetime.combine(today, datetime.max.time())
    wi  = df_i[(df_i["DATE"] >= wdt) & (df_i["DATE"] <= wet)]
    if not wi.empty:
        inv_week = (wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                  - wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())
    mi = df_i[(df_i["DATE"].dt.month==today.month)&(df_i["DATE"].dt.year==today.year)]
    if not mi.empty:
        inv_month = (mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                   - mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())

# ── MASTHEAD ─────────────────────────────────────────────────────────────────
date_str = f"{DAYS_GR[today.weekday()]}<br>{today.day} {MONTHS_GR[today.month-1]} {today.year}"
st.markdown(f"""
<div class="masthead">
  <div>
    <div class="mast-hed">Operations</div>
    <div class="mast-sub">AB Σκύρος &nbsp;·&nbsp; Κατάστημα 1082</div>
  </div>
  <div class="mast-date">{date_str}</div>
</div>
""", unsafe_allow_html=True)

# ── WEEK BAR ─────────────────────────────────────────────────────────────────
s_cls  = "pos"   if s_week   else "muted"
i_cls  = "blue"  if inv_week is not None else "muted"
d_cls  = "pos"   if s_wdays  else "muted"
st.markdown(f"""
<div class="week-bar">
  <div class="wb-cell">
    <div class="wb-label">Πωλήσεις Εβδ.</div>
    <div class="wb-val {s_cls}">{fmt(s_week) if s_week else "—"}</div>
  </div>
  <div class="wb-sep"></div>
  <div class="wb-cell">
    <div class="wb-label">Καθ. Τιμολογίων</div>
    <div class="wb-val {i_cls}">{fmt(inv_week) if inv_week is not None else "—"}</div>
  </div>
  <div class="wb-sep"></div>
  <div class="wb-cell">
    <div class="wb-label">Ημέρες {week_lbl[:11]}</div>
    <div class="wb-val {d_cls}">{s_wdays} / 7</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SALES CARD ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-lbl">Modules</div>', unsafe_allow_html=True)

if s_days == 0:   s_st, s_sc = "Ενημερωμένο", "st-live"
elif s_days and s_days <= 2: s_st, s_sc = f"Πριν {s_days} ημέρες", "st-warn"
elif s_date: s_st, s_sc = f"Πριν {s_days} ημέρες", "st-idle"
else: s_st, s_sc = "Εκκρεμεί", "st-idle"

st.markdown(f"""
<div class="dcard">
  <div class="dcard-hdr">
    <div class="dcard-title">Πωλήσεις Καταστήματος</div>
    <span class="dcard-status {s_sc}">{s_st}</span>
  </div>
  <div class="dcard-body">
""", unsafe_allow_html=True)

if s_val is not None:
    dl = s_date.strftime("%d/%m/%Y")
    st.markdown(f"""
    <div class="stat-line">
      <span class="sl-key">Τελευταία ημέρα &nbsp;·&nbsp; {dl}</span>
      <span class="sl-val hero">{fmt(s_val)}</span>
    </div>
    <div class="stat-line">
      <span class="sl-key">Πελάτες</span>
      <span class="sl-val">{s_cust if s_cust else "—"}</span>
    </div>
    <div class="stat-line">
      <span class="sl-key">Σύνολο εβδ. &nbsp;·&nbsp; {week_lbl}</span>
      <span class="sl-val hero">{fmt(s_week) if s_week else "—"}</span>
    </div>
    <div class="stat-line">
      <span class="sl-key">Ημέρες εβδομάδας</span>
      <span class="sl-val">{s_wdays} / 7</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="empty-state">Δεν υπάρχουν δεδομένα. Μεταβείτε στη σελίδα Πωλήσεων.</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# ── INVOICES CARD ─────────────────────────────────────────────────────────────
i_st = "Ενημερωμένο" if (inv_week is not None or inv_month is not None) else "Εκκρεμεί"
i_sc = "st-live"     if (inv_week is not None or inv_month is not None) else "st-idle"

st.markdown(f"""
<div class="dcard">
  <div class="dcard-hdr">
    <div class="dcard-title">Ελεγχος Τιμολογιων</div>
    <span class="dcard-status {i_sc}">{i_st}</span>
  </div>
  <div class="dcard-body">
""", unsafe_allow_html=True)

if inv_week is not None or inv_month is not None:
    wl = f"{week_mon.strftime('%d/%m')} — {week_sun.strftime('%d/%m')}"
    mn = MONTHS_GR[today.month-1]
    if inv_week is not None:
        st.markdown(f"""
        <div class="stat-line">
          <span class="sl-key">Καθαρό εβδ. &nbsp;·&nbsp; {wl}</span>
          <span class="sl-val blue">{fmt(inv_week)}</span>
        </div>""", unsafe_allow_html=True)
    if inv_month is not None:
        st.markdown(f"""
        <div class="stat-line">
          <span class="sl-key">Καθαρό μήνα &nbsp;·&nbsp; {mn}</span>
          <span class="sl-val">{fmt(inv_month)}</span>
        </div>""", unsafe_allow_html=True)
else:
    st.markdown('<div class="empty-state">Δεν υπάρχουν δεδομένα. Μεταβείτε στη σελίδα Τιμολογίων.</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# ── NAV ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="nav-grid">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if st.button("Πωλησεις", use_container_width=True):
        st.switch_page("pages/1_Sales.py")
with c2:
    if st.button("Τιμολογια", use_container_width=True):
        st.switch_page("pages/2_Invoices.py")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="foot-rule">AB Skyros &nbsp;·&nbsp; Store 1082 &nbsp;·&nbsp; Operations Platform</div>', unsafe_allow_html=True)
