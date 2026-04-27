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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; font-family: 'Inter', sans-serif !important; }
html, body, [class*="css"] {
    background: #f8fafc !important;
    color: #0f172a !important;
}
.stApp { background: #f8fafc !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

.wrap {
    max-width: 1000px;
    margin: 0 auto;
    padding: 1.8rem 1.5rem 2rem;
}

/* ── TOP ── */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: .9rem;
    margin-bottom: 1.2rem;
}
.tb-sub { font-size: .6rem; font-weight: 600; letter-spacing: .16em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: .2rem; }
.tb-title { font-size: 1.3rem; font-weight: 700; color: #0f172a; }
.tb-date { text-align: right; font-size: .65rem; color: #94a3b8; line-height: 1.8; }

/* ── WEEK STRIP ── */
.wstrip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #e2e8f0;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 1.1rem;
}
.wc { background: #fff; padding: .7rem 1rem; }
.wc-lbl { font-size: .52rem; font-weight: 600; letter-spacing: .14em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: .25rem; }
.wc-val { font-size: .9rem; font-weight: 700; color: #0f172a; }
.wc-val.g { color: #16a34a; }
.wc-val.b { color: #2563eb; }
.wc-val.m { color: #94a3b8; font-size: .78rem; font-weight: 400; }

/* ── CARDS ── */
.cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
}
.card-hdr {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: .65rem 1rem;
    border-bottom: 1px solid #f1f5f9;
    background: #f8fafc;
}
.card-name { font-size: .72rem; font-weight: 700;
    letter-spacing: .04em; color: #334155; }
.badge { font-size: .52rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; padding: .18rem .55rem; border-radius: 4px; }
.b-ok   { background: #dcfce7; color: #15803d; }
.b-warn { background: #fef9c3; color: #92400e; }
.b-off  { background: #f1f5f9; color: #94a3b8; }

.card-body { padding: .6rem 1rem .8rem; }
.row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: .3rem 0;
    border-bottom: 1px solid #f8fafc;
}
.row:last-child { border-bottom: none; }
.rk { font-size: .58rem; font-weight: 500; letter-spacing: .06em;
    text-transform: uppercase; color: #94a3b8; }
.rv { font-size: .85rem; font-weight: 700; color: #0f172a; }
.rv.hero { font-size: 1rem; color: #16a34a; }
.rv.blue { font-size: 1rem; color: #2563eb; }
.rv.nil  { color: #cbd5e1; font-weight: 400; font-style: italic; font-size: .75rem; }

/* ── BUTTONS ── */
.stButton > button {
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .8rem !important;
    font-weight: 600 !important;
    padding: .65rem 1rem !important;
    width: 100% !important;
    transition: all .12s !important;
    border: none !important;
}
.btn-g > button { background: #16a34a !important; color: #fff !important; }
.btn-g > button:hover { background: #15803d !important; }
.btn-b > button { background: #2563eb !important; color: #fff !important; }
.btn-b > button:hover { background: #1d4ed8 !important; }

.nav { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }

.foot { text-align: center; font-size: .58rem; color: #cbd5e1;
    padding-top: .8rem; border-top: 1px solid #f1f5f9; margin-top: .5rem; }

/* ── RESPONSIVE ── */
@media (max-width: 640px) {
    .wrap { padding: 1rem .9rem 1.5rem; }
    .tb-date { display: none; }
    .wstrip { grid-template-columns: 1fr 1fr; }
    .wc:nth-child(3), .wc:nth-child(4) { display: none; }
    .cards { grid-template-columns: 1fr; gap: .7rem; }
    .row.sec { display: none; }
    .rv.hero { font-size: .9rem; }
    .rv.blue { font-size: .9rem; }
}
@media (min-width: 641px) and (max-width: 900px) {
    .wstrip { grid-template-columns: repeat(3, 1fr); }
    .wc:last-child { display: none; }
}
</style>
""", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
DAYS = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MON  = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

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

st.markdown('<div class="wrap">', unsafe_allow_html=True)

st.markdown(f"""
<div class="topbar">
  <div>
    <div class="tb-sub">AB Skyros · Κατάστημα 1082</div>
    <div class="tb-title">Operations Hub</div>
  </div>
  <div class="tb-date">{dy}, {today.day} {mn} {today.year}<br>Εβδομάδα {wlbl}</div>
</div>
""", unsafe_allow_html=True)

# Week strip
sw = "g" if s_week  else "m"
iw = "b" if inv_week is not None else "m"
st.markdown(f"""
<div class="wstrip">
  <div class="wc"><div class="wc-lbl">Πωλήσεις Εβδ.</div>
    <div class="wc-val {sw}">{fmt(s_week) if s_week else "—"}</div></div>
  <div class="wc"><div class="wc-lbl">Καθ. Τιμολ. Εβδ.</div>
    <div class="wc-val {iw}">{fmt(inv_week) if inv_week is not None else "—"}</div></div>
  <div class="wc"><div class="wc-lbl">Πωλήσεις Μήνα</div>
    <div class="wc-val">{fmt(s_month) if s_month else "—"}</div></div>
  <div class="wc"><div class="wc-lbl">Ημέρες Εβδ.</div>
    <div class="wc-val">{s_wdays} / 7</div></div>
</div>
""", unsafe_allow_html=True)

# Cards
st.markdown('<div class="cards">', unsafe_allow_html=True)

# Sales card
st.markdown(f"""
<div class="card">
  <div class="card-hdr">
    <span class="card-name">ΠΩΛΗΣΕΙΣ ΚΑΤΑΣΤΗΜΑΤΟΣ</span>
    <span class="badge {s_bcls}">{s_bdg}</span>
  </div>
  <div class="card-body">
""", unsafe_allow_html=True)

if s_val is not None:
    dl = s_date.strftime("%d/%m/%Y")
    st.markdown(f"""
    <div class="row"><span class="rk">Τελευταία · {dl}</span><span class="rv hero">{fmt(s_val)}</span></div>
    <div class="row"><span class="rk">Πελάτες</span><span class="rv">{s_cust if s_cust else "—"}</span></div>
    <div class="row sec"><span class="rk">Εβδομάδα {wlbl}</span><span class="rv" style="color:#16a34a">{fmt(s_week) if s_week else "—"}</span></div>
    <div class="row sec"><span class="rk">Μήνας {mn}</span><span class="rv">{fmt(s_month) if s_month else "—"}</span></div>
    <div class="row sec"><span class="rk">ΜΟ Καλαθιού</span><span class="rv">{fmt(s_avg) if s_avg else "—"}</span></div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="row"><span class="rv nil">Χωρίς δεδομένα</span></div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# Invoices card
st.markdown(f"""
<div class="card">
  <div class="card-hdr">
    <span class="card-name">ΕΛΕΓΧΟΣ ΤΙΜΟΛΟΓΙΩΝ</span>
    <span class="badge {i_bcls}">{i_bdg}</span>
  </div>
  <div class="card-body">
""", unsafe_allow_html=True)

if inv_week is not None or inv_month is not None:
    if inv_week is not None:
        st.markdown(f'<div class="row"><span class="rk">Καθαρό Εβδ. {wlbl}</span><span class="rv blue">{fmt(inv_week)}</span></div>', unsafe_allow_html=True)
    if inv_month is not None:
        st.markdown(f'<div class="row sec"><span class="rk">Καθαρό Μήνα {mn}</span><span class="rv">{fmt(inv_month)}</span></div>', unsafe_allow_html=True)
    if not df_i.empty:
        last_inv = df_i["DATE"].max().strftime("%d/%m/%Y")
        st.markdown(f'<div class="row sec"><span class="rk">Τελευταία εγγραφή</span><span class="rv">{last_inv}</span></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="row"><span class="rv nil">Χωρίς δεδομένα</span></div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # close cards

# Nav
st.markdown('<div class="nav">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("Πωλήσεις →", use_container_width=True, key="gs"):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("Τιμολόγια →", use_container_width=True, key="gi"):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="foot">AB Skyros 1082 · Operations Platform · {today.year}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
