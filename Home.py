import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="AB Skyros 1082",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS — AB Branded (navy #003d6b + cyan #00b5e2) ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* { box-sizing: border-box; font-family: 'Inter', sans-serif !important; }
html, body, [class*="css"] {
    background: #e8f4fb !important;
    color: #0f172a !important;
}
.stApp { background: #e8f4fb !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }

.block-container {
    padding: 2.5rem 1.5rem 4rem !important;
    max-width: 1000px !important;
    margin: 0 auto !important;
}

/* ── HERO BANNER — Pure CSS, καμία εξωτερική εικόνα ── */
.hero {
    background: linear-gradient(135deg, #003d6b 0%, #005f9e 55%, #0077b6 100%);
    border-radius: 20px;
    min-height: 220px;
    padding: 2.5rem 3rem;
    color: #ffffff;
    margin-bottom: 2rem;
    box-shadow: 0 20px 40px -8px rgba(0, 61, 107, 0.35);
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    position: relative;
    overflow: hidden;
}
/* Γεωμετρικά κύκλα ως subtle texture */
.hero::before {
    content: "";
    position: absolute; top: -60px; right: -60px;
    width: 260px; height: 260px; border-radius: 50%;
    background: rgba(0,181,226,0.12); pointer-events: none;
}
.hero::after {
    content: "";
    position: absolute; bottom: -80px; right: 120px;
    width: 200px; height: 200px; border-radius: 50%;
    background: rgba(0,181,226,0.08); pointer-events: none;
}
.hero-sub {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.28em;
    text-transform: uppercase; color: #00b5e2; margin-bottom: 0.6rem;
    position: relative; z-index: 1;
}
.hero-title {
    font-size: 2.3rem; font-weight: 800; color: #ffffff;
    line-height: 1.1; margin-bottom: 0.2rem;
    position: relative; z-index: 1;
}
.hero-date {
    text-align: right; font-size: 0.88rem; color: #bae6fd;
    font-weight: 500; line-height: 1.7;
    position: relative; z-index: 1;
}
.hero-logo {
    font-size: 1rem; font-weight: 800; letter-spacing: -0.5px;
    background: white; color: #003d6b; padding: 6px 12px;
    border-radius: 8px; display: inline-block; margin-bottom: 12px;
}

/* ── WEEK STRIP ── */
.wstrip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #bae6fd;
    border: 1px solid #bae6fd;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 2rem;
    box-shadow: 0 4px 12px rgba(0, 61, 107, 0.08);
}
.wc { background: #fff; padding: 1.2rem 1.5rem; }
.wc-lbl {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #64748b; margin-bottom: 0.4rem;
}
.wc-val { font-size: 1.25rem; font-weight: 800; color: #0f172a; }
.wc-val.g { color: #00b5e2; }
.wc-val.b { color: #003d6b; }
.wc-val.m { color: #94a3b8; font-size: 1rem; font-weight: 500; }

/* ── CARDS ── */
.cards {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 1.5rem; margin-bottom: 2.5rem;
}
.card {
    background: #fff;
    border: 1px solid #e0f2fe;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 61, 107, 0.07);
}
.card-hdr {
    display: flex; justify-content: space-between; align-items: center;
    padding: 1.1rem 1.5rem;
    border-bottom: 1px solid #f0f9ff;
    background: #f8fafc;
    border-top: 3px solid #00b5e2;
}
.card-name { font-size: 0.82rem; font-weight: 800; letter-spacing: 0.06em; color: #003d6b; }
.badge {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; padding: 0.3rem 0.75rem; border-radius: 8px;
}
.b-ok   { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
.b-warn { background: #fef9c3; color: #92400e; border: 1px solid #fde68a; }
.b-off  { background: #f1f5f9; color: #94a3b8; border: 1px solid #e2e8f0; }

.card-body { padding: 1.2rem 1.5rem 1.5rem; }
.row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.65rem 0; border-bottom: 1px solid #f0f9ff;
}
.row:last-child { border-bottom: none; }
.rk {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: #64748b;
}
.rv { font-size: 1.0rem; font-weight: 700; color: #0f172a; }
.rv.hero  { font-size: 1.35rem; color: #00b5e2; }
.rv.blue  { font-size: 1.35rem; color: #003d6b; }
.rv.nil   { color: #cbd5e1; font-weight: 500; font-style: italic; font-size: 0.9rem; }

/* ── BUTTONS ── */
.stButton > button {
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,61,107,0.15) !important;
}
.btn-g > button {
    background: #00b5e2 !important; color: #ffffff !important;
}
.btn-g > button:hover {
    background: #0099c4 !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,181,226,0.35) !important;
}
.btn-b > button {
    background: #003d6b !important; color: #ffffff !important;
}
.btn-b > button:hover {
    background: #004f8a !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,61,107,0.3) !important;
}

.nav { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.foot {
    text-align: center; font-size: 0.7rem; color: #94a3b8; font-weight: 500;
    padding-top: 2rem; margin-top: 2rem;
    border-top: 1px solid #e0f2fe;
}

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
    .block-container { padding: 1rem !important; }
    .hero {
        flex-direction: column; align-items: flex-start;
        padding: 2rem 1.5rem; border-radius: 14px; min-height: auto;
    }
    .hero-date { text-align: left; margin-top: 1.2rem; }
    .hero-title { font-size: 1.8rem; }
    .wstrip { grid-template-columns: 1fr 1fr; border-radius: 12px; }
    .cards { grid-template-columns: 1fr; }
    .nav { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
DAYS = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MON  = ["Ιανουαρίου","Φεβρουαρίου","Μαρτίου","Απριλίου","Μαΐου","Ιουνίου",
        "Ιουλίου","Αυγούστου","Σεπτεμβρίου","Οκτωβρίου","Νοεμβρίου","Δεκεμβρίου"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

today    = date.today()
week_mon = today - timedelta(days=today.weekday())
week_sun = week_mon + timedelta(days=6)
wlbl     = f"{week_mon.strftime('%d/%m')} – {week_sun.strftime('%d/%m')}"

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
s_val = s_date = s_cust = s_avg = s_days = None
s_week = s_month = 0; s_wdays = 0

if not df_s.empty:
    r = df_s.iloc[0]
    s_val   = r.get("net_sales")
    s_date  = r.get("date")
    s_cust  = int(r["customers"])  if pd.notna(r.get("customers"))  else None
    s_avg   = r.get("avg_basket")  if pd.notna(r.get("avg_basket")) else None
    s_days  = (today - s_date).days if s_date else None

    wm = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    s_week  = wm["net_sales"].sum() if not wm.empty else 0
    s_wdays = len(wm)

    mm = df_s[(df_s["date"] >= date(today.year,today.month,1)) & (df_s["date"] <= today)]
    s_month = mm["net_sales"].sum() if not mm.empty else 0

inv_week = inv_month = None
if not df_i.empty:
    wdt = datetime.combine(week_mon, datetime.min.time())
    wet = datetime.combine(today, datetime.max.time())
    wi  = df_i[(df_i["DATE"] >= wdt) & (df_i["DATE"] <= wet)]
    if not wi.empty:
        inv_week = (wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                  - wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())

    mi = df_i[(df_i["DATE"].dt.month == today.month) & (df_i["DATE"].dt.year == today.year)]
    if not mi.empty:
        inv_month = (mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                   - mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())

# ── RENDER ────────────────────────────────────────────────────────────────────
dy = DAYS[today.weekday()]
mn = MON[today.month - 1]

if s_days == 0:              s_bdg, s_bcls = "LIVE",   "b-ok"
elif s_days and s_days <= 2: s_bdg, s_bcls = f"–{s_days}D", "b-warn"
elif s_date:                 s_bdg, s_bcls = f"–{s_days}D", "b-off"
else:                        s_bdg, s_bcls = "N/A",    "b-off"

i_bdg  = "OK"    if (inv_week is not None or inv_month is not None) else "N/A"
i_bcls = "b-ok"  if (inv_week is not None or inv_month is not None) else "b-off"

# ── Hero Banner ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div>
    <div class="hero-logo">AB</div>
    <div class="hero-sub">Κατάστημα 1082 · Σκύρος</div>
    <div class="hero-title">Business Operations</div>
  </div>
  <div class="hero-date">
    {dy}, {today.day} {mn} {today.year}<br>
    <span style="color:#00b5e2; font-weight:700;">Εβδομάδα: {wlbl}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Week Strip ────────────────────────────────────────────────────────────────
sw = "g" if s_week  else "m"
iw = "b" if inv_week is not None else "m"
st.markdown(f"""
<div class="wstrip">
  <div class="wc">
    <div class="wc-lbl">Πωλήσεις Εβδομάδας</div>
    <div class="wc-val {sw}">{fmt(s_week) if s_week else "—"}</div>
  </div>
  <div class="wc">
    <div class="wc-lbl">Τιμολόγια Εβδομάδας</div>
    <div class="wc-val {iw}">{fmt(inv_week) if inv_week is not None else "—"}</div>
  </div>
  <div class="wc">
    <div class="wc-lbl">Πωλήσεις Μήνα</div>
    <div class="wc-val">{fmt(s_month) if s_month else "—"}</div>
  </div>
  <div class="wc">
    <div class="wc-lbl">Ημέρες Συστήματος</div>
    <div class="wc-val">{s_wdays} / 7</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Cards ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="cards">', unsafe_allow_html=True)

# Sales card
st.markdown(f"""
<div class="card">
  <div class="card-hdr">
    <span class="card-name">🛒 ΠΩΛΗΣΕΙΣ ΚΑΤΑΣΤΗΜΑΤΟΣ</span>
    <span class="badge {s_bcls}">{s_bdg}</span>
  </div>
  <div class="card-body">
""", unsafe_allow_html=True)

if s_val is not None:
    dl = s_date.strftime("%d/%m/%Y")
    st.markdown(f"""
    <div class="row"><span class="rk">Τελευταία ({dl})</span><span class="rv hero">{fmt(s_val)}</span></div>
    <div class="row"><span class="rk">Πελάτες</span><span class="rv">{s_cust if s_cust else "—"}</span></div>
    <div class="row"><span class="rk">ΜΟ Καλαθιού</span><span class="rv">{fmt(s_avg) if s_avg else "—"}</span></div>
    <div class="row"><span class="rk">Σύνολο Εβδομάδας</span><span class="rv hero">{fmt(s_week) if s_week else "—"}</span></div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="row"><span class="rv nil">Δεν υπάρχουν καταχωρημένες πωλήσεις</span></div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# Invoices card
st.markdown(f"""
<div class="card">
  <div class="card-hdr">
    <span class="card-name">📄 ΕΛΕΓΧΟΣ ΤΙΜΟΛΟΓΙΩΝ</span>
    <span class="badge {i_bcls}">{i_bdg}</span>
  </div>
  <div class="card-body">
""", unsafe_allow_html=True)

if inv_week is not None or inv_month is not None:
    if inv_week is not None:
        st.markdown(f'<div class="row"><span class="rk">Καθαρό Εβδομάδας</span><span class="rv blue">{fmt(inv_week)}</span></div>', unsafe_allow_html=True)
    if inv_month is not None:
        st.markdown(f'<div class="row"><span class="rk">Καθαρό Μήνα</span><span class="rv">{fmt(inv_month)}</span></div>', unsafe_allow_html=True)
    if not df_i.empty:
        last_inv = df_i["DATE"].max().strftime("%d/%m/%Y")
        st.markdown(f'<div class="row"><span class="rk">Τελευταία εγγραφή</span><span class="rv">{last_inv}</span></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="row"><span class="rv nil">Δεν υπάρχουν καταχωρημένα τιμολόγια</span></div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────────────────────────
st.markdown('<div class="nav">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("📊 Αναλυτικές Πωλήσεις →", use_container_width=True, key="gs"):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("📄 Διαχείριση Τιμολογίων →", use_container_width=True, key="gi"):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="foot">AB Βασιλόπουλος · Κατάστημα 1082 Σκύρος · Operations Platform · {today.year}</div>', unsafe_allow_html=True)
