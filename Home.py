import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime

st.set_page_config(
    page_title="AB Skyros 1082",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from gsheets_helper import load_sales, load_invoices

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { box-sizing: border-box; font-family: 'Inter', sans-serif !important; }
html, body, [class*="css"] { background: #f0f6fb !important; color: #0f172a !important; }
.stApp { background: #f0f6fb !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 2rem 1.5rem 4rem !important; max-width: 680px !important; margin: 0 auto !important; }

.hdr {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 2rem; padding-bottom: 1.2rem;
    border-bottom: 2px solid #bae6fd;
}
.hdr-left { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 1rem; font-weight: 800; background: #003d6b; color: #fff;
        padding: 5px 10px; border-radius: 6px; letter-spacing: -0.5px; }
.store { font-size: 0.9rem; font-weight: 600; color: #003d6b; }
.hdr-date { font-size: 0.78rem; color: #64748b; font-weight: 500; text-align: right; line-height: 1.6; }

.metrics {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1px; background: #bae6fd;
    border: 1px solid #bae6fd; border-radius: 14px; overflow: hidden;
    margin-bottom: 2rem;
    box-shadow: 0 4px 16px rgba(0,61,107,0.08);
}
.metric { background: #fff; padding: 1.2rem 1.4rem; }
.m-lbl { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.14em;
          text-transform: uppercase; color: #64748b; margin-bottom: 0.4rem; }
.m-val { font-size: 1.35rem; font-weight: 800; color: #003d6b; margin-bottom: 0.2rem; }
.m-val.cyan { color: #0077b6; }
.m-sub { font-size: 0.65rem; color: #94a3b8; font-weight: 500; }
.m-val.empty { color: #cbd5e1; font-size: 1.1rem; font-weight: 500; }

.stButton > button {
    border-radius: 10px !important; font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important; font-weight: 700 !important;
    padding: 0.85rem 1.2rem !important; width: 100% !important;
    transition: all 0.15s ease !important; border: none !important;
}
.btn-g > button { background: #0077b6 !important; color: #fff !important; }
.btn-g > button:hover { background: #005f9e !important; }
.btn-b > button { background: #003d6b !important; color: #fff !important; }
.btn-b > button:hover { background: #004f8a !important; }
.nav { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }

.foot { text-align: center; font-size: 0.65rem; color: #94a3b8;
        padding-top: 2rem; margin-top: 2rem; border-top: 1px solid #e0f2fe; }

@media (max-width: 580px) {
    .block-container { padding: 1rem !important; }
    .metrics { grid-template-columns: 1fr; }
    .nav { grid-template-columns: 1fr; }
    .hdr { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
DAYS = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MON  = ["Ιαν","Φεβ","Μαρ","Απρ","Μαΐ","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    if v == int(v):
        return f"{int(v):,} €".replace(",",".")
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

today    = date.today()
week_mon = today - timedelta(days=today.weekday())

# ── DATA ──────────────────────────────────────────────────────────────────────
df_s = load_sales()
df_i = load_invoices()

# Πωλήσεις
s_val = s_date = s_cust = s_wdays = None
s_week = 0

if not df_s.empty:
    r      = df_s.iloc[0]
    s_val  = r.get("net_sales")
    s_date = r.get("date")
    s_cust = int(r["customers"]) if pd.notna(r.get("customers")) else None

    wm     = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    s_week  = wm["net_sales"].sum() if not wm.empty else 0
    s_wdays = len(wm)

# Τιμολόγια εβδομάδας
inv_week = None
if not df_i.empty:
    wdt = datetime.combine(week_mon, datetime.min.time())
    wet = datetime.combine(today,    datetime.max.time())
    wi  = df_i[(df_i["DATE"] >= wdt) & (df_i["DATE"] <= wet)]
    if not wi.empty:
        inv_week = (wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
                  - wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum())

# ── RENDER ────────────────────────────────────────────────────────────────────
dy = DAYS[today.weekday()]
mn = MON[today.month - 1]

# Header
st.markdown(f"""
<div class="hdr">
  <div class="hdr-left">
    <span class="logo">AB</span>
    <span class="store">Κατάστημα 1082 · Σκύρος</span>
  </div>
  <div class="hdr-date">{dy} {today.day} {mn} {today.year}</div>
</div>
""", unsafe_allow_html=True)

# Metrics
last_lbl  = s_date.strftime("%d/%m") if s_date else "—"
cust_lbl  = f"{s_cust} πελάτες" if s_cust else ""
days_lbl  = f"{s_wdays}/7 ημέρες" if s_wdays else "καμία εγγραφή"

s_val_html   = fmt(s_val)   if s_val  else "—"
s_week_html  = fmt(s_week)  if s_week else "—"
inv_week_html = fmt(inv_week) if inv_week is not None else "—"

s_cls   = "m-val cyan" if s_val  else "m-val empty"
sw_cls  = "m-val"      if s_week else "m-val empty"
iw_cls  = "m-val"      if inv_week is not None else "m-val empty"

st.markdown(f"""
<div class="metrics">
  <div class="metric">
    <div class="m-lbl">Τελευταίες Πωλήσεις</div>
    <div class="{s_cls}">{s_val_html}</div>
    <div class="m-sub">{last_lbl} · {cust_lbl}</div>
  </div>
  <div class="metric">
    <div class="m-lbl">Σύνολο Εβδομάδας</div>
    <div class="{sw_cls}">{s_week_html}</div>
    <div class="m-sub">{days_lbl}</div>
  </div>
  <div class="metric">
    <div class="m-lbl">Τιμολόγια Εβδ.</div>
    <div class="{iw_cls}">{inv_week_html}</div>
    <div class="m-sub">Καθαρό σύνολο</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Navigation
st.markdown('<div class="nav">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("📊 Πωλήσεις →", use_container_width=True, key="gs"):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("📄 Τιμολόγια →", use_container_width=True, key="gi"):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="foot">AB Βασιλόπουλος · 1082 Σκύρος · {today.year}</div>', unsafe_allow_html=True)
