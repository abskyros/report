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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* { box-sizing: border-box; font-family: 'Inter', sans-serif !important; }
html, body, [class*="css"] {
    background: #f1f5f9 !important; /* Ελαφρώς πιο σκούρο γκρι φόντο για αντίθεση με τις κάρτες */
    color: #0f172a !important;
}
.stApp { background: #f1f5f9 !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }

/* --- ΕΔΩ ΕΙΝΑΙ ΤΟ ΜΥΣΤΙΚΟ ΓΙΑ ΤΟ ΚΕΝΤΡΑΡΙΣΜΑ --- */
.block-container {
    padding: 3rem 1.5rem 4rem !important;
    max-width: 1000px !important; /* Κλειδώνει το μέγιστο πλάτος */
    margin: 0 auto !important;    /* Το κεντράρει απόλυτα στην οθόνη */
}

/* ── HERO BANNER ── */
.hero {
    background: linear-gradient(to right, rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.4)), 
                url('https://images.unsplash.com/photo-1542838132-92c53300491e?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80') center/cover no-repeat;
    border-radius: 20px;
    min-height: 240px; /* Σταθερό κομψό ύψος */
    padding: 2.5rem 3rem;
    color: #ffffff;
    margin-bottom: 2rem;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}
.hero-sub {
    font-size: 0.8rem; font-weight: 700; letter-spacing: 0.25em;
    text-transform: uppercase; color: #10b981; margin-bottom: 0.6rem;
}
.hero-title {
    font-size: 2.5rem; font-weight: 800; color: #ffffff; line-height: 1.1; margin-bottom: 0.2rem;
}
.hero-date {
    text-align: right; font-size: 0.9rem; color: #cbd5e1; font-weight: 500; line-height: 1.6;
}

/* ── WEEK STRIP ── */
.wstrip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #e2e8f0;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 2rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,.05);
}
.wc { background: #fff; padding: 1.2rem 1.5rem; }
.wc-lbl { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #64748b; margin-bottom: 0.4rem; }
.wc-val { font-size: 1.3rem; font-weight: 800; color: #0f172a; }
.wc-val.g { color: #10b981; }
.wc-val.b { color: #3b82f6; }
.wc-val.m { color: #94a3b8; font-size: 1rem; font-weight: 500; }

/* ── CARDS ── */
.cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2.5rem;
}
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,.05);
}
.card-hdr {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.2rem 1.5rem;
    border-bottom: 1px solid #f1f5f9;
    background: #f8fafc;
}
.card-name { font-size: 0.9rem; font-weight: 700;
    letter-spacing: 0.05em; color: #334155; }
.badge { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; padding: 0.3rem 0.7rem; border-radius: 8px; }
.b-ok   { background: #dcfce7; color: #15803d; }
.b-warn { background: #fef9c3; color: #92400e; }
.b-off  { background: #f1f5f9; color: #94a3b8; }

.card-body { padding: 1.2rem 1.5rem 1.5rem; }
.row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid #f8fafc;
}
.row:last-child { border-bottom: none; }
.rk { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; color: #64748b; }
.rv { font-size: 1.05rem; font-weight: 700; color: #0f172a; }
.rv.hero { font-size: 1.4rem; color: #10b981; }
.rv.blue { font-size: 1.4rem; color: #3b82f6; }
.rv.nil  { color: #cbd5e1; font-weight: 500; font-style: italic; font-size: 0.9rem; }

/* ── BUTTONS ── */
.stButton > button {
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    border: none !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1) !important;
}
.btn-g > button { background: #10b981 !important; color: #ffffff !important; }
.btn-g > button:hover { background: #059669 !important; transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(16,185,129,0.3) !important; }
.btn-b > button { background: #3b82f6 !important; color: #ffffff !important; }
.btn-b > button:hover { background: #2563eb !important; transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(59,130,246,0.3) !important; }

.nav { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.foot { text-align: center; font-size: 0.7rem; color: #94a3b8; font-weight: 500;
    padding-top: 2rem; margin-top: 2rem; }

/* ── RESPONSIVE ΓΙΑ ΚΙΝΗΤΑ ── */
@media (max-width: 768px) {
    .block-container { padding: 1rem !important; }
    .hero { flex-direction: column; align-items: flex-start; padding: 2rem 1.5rem; border-radius: 16px; }
    .hero-date { text-align: left; margin-top: 1.5rem; }
    .hero-title { font-size: 2rem; }
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
    if v is None or (isinstance(v,float) and pd.isna(v)): return "—"
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
    wi  = df_i[(df_i["DATE"]>=wdt)&(df_i["DATE"]<=wet)]
    
    if not wi.empty:
        inv_week = (wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                  - wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())
        
    mi = df_i[(df_i["DATE"].dt.month==today.month)&(df_i["DATE"].dt.year==today.year)]
    if not mi.empty:
        inv_month = (mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
                   - mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum())

# ── RENDER ────────────────────────────────────────────────────────────────────
dy = DAYS[today.weekday()]
mn = MON[today.month-1]

if s_days == 0:    s_bdg, s_bcls = "LIVE",   "b-ok"
elif s_days and s_days<=2: s_bdg, s_bcls = f"–{s_days}D", "b-warn"
elif s_date:       s_bdg, s_bcls = f"–{s_days}D", "b-off"
else:              s_bdg, s_bcls = "N/A",    "b-off"

i_bdg = "OK"  if (inv_week is not None or inv_month is not None) else "N/A"
i_bcls= "b-ok" if (inv_week is not None or inv_month is not None) else "b-off"

# Hero Banner
st.markdown(f"""
<div class="hero">
  <div>
    <div class="hero-sub">Κατάστημα 1082 · Σκύρος</div>
    <div class="hero-title">Business Operations Portal</div>
  </div>
  <div class="hero-date">{dy}, {today.day} {mn} {today.year}<br><span style="color:#10b981;">Εβδομάδα: {wlbl}</span></div>
</div>
""", unsafe_allow_html=True)

# Week strip
sw = "g" if s_week  else "m"
iw = "b" if inv_week is not None else "m"
st.markdown(f"""
<div class="wstrip">
  <div class="wc"><div class="wc-lbl">Πωλήσεις Εβδομάδας</div>
    <div class="wc-val {sw}">{fmt(s_week) if s_week else "—"}</div></div>
  <div class="wc"><div class="wc-lbl">Τιμολόγια Εβδομάδας</div>
    <div class="wc-val {iw}">{fmt(inv_week) if inv_week is not None else "—"}</div></div>
  <div class="wc"><div class="wc-lbl">Πωλήσεις Μήνα ({mn.split()[0]})</div>
    <div class="wc-val">{fmt(s_month) if s_month else "—"}</div></div>
  <div class="wc"><div class="wc-lbl">Ημέρες Συστήματος</div>
    <div class="wc-val">{s_wdays} / 7</div></div>
</div>
""", unsafe_allow_html=True)

# Cards
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
    <div class="row"><span class="rk">Πελάτες Τελευταίας</span><span class="rv">{s_cust if s_cust else "—"}</span></div>
    <div class="row sec"><span class="rk">ΜΟ Καλαθιού</span><span class="rv">{fmt(s_avg) if s_avg else "—"}</span></div>
    <div class="row sec"><span class="rk">Σύνολο Εβδομάδας</span><span class="rv" style="color:#10b981">{fmt(s_week) if s_week else "—"}</span></div>
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
        st.markdown(f'<div class="row sec"><span class="rk">Καθαρό Μήνα</span><span class="rv">{fmt(inv_month)}</span></div>', unsafe_allow_html=True)
    if not df_i.empty:
        last_inv = df_i["DATE"].max().strftime("%d/%m/%Y")
        st.markdown(f'<div class="row sec"><span class="rk">Τελευταία εγγραφή</span><span class="rv">{last_inv}</span></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="row"><span class="rv nil">Δεν υπάρχουν καταχωρημένα τιμολόγια</span></div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Navigation
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

st.markdown(f'<div class="foot">AB Skyros 1082 · Operations Platform · {today.year}</div>', unsafe_allow_html=True)
