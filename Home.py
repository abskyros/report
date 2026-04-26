import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="AB Σκύρος 1082",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #f8f9fb !important;
    color: #111827 !important;
}
.stApp { background: #f8f9fb !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding: 2rem 1.5rem 4rem !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}
.top-header {
    background: #111827;
    border-radius: 14px;
    padding: 1.4rem 1.8rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}
.brand-sub  { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: #6ee7b7; margin-bottom: 0.3rem; }
.brand-name { font-size: 1.4rem; font-weight: 700; color: #f9fafb; }
.date-lbl   { font-size: 0.6rem; color: #6b7280; text-align: right; }
.date-val   { font-size: 0.8rem; color: #9ca3af; text-align: right; margin-top: 0.15rem; }

.cards-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
@media(max-width:600px) {
    .cards-wrap { grid-template-columns: 1fr; }
    .top-header { flex-direction: column; align-items: flex-start; }
    .date-lbl, .date-val { text-align: left; }
}
.card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1.4rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--accent);
    border-radius: 14px 14px 0 0;
}
.card-green { --accent: #10b981; }
.card-blue  { --accent: #3b82f6; }
.card-icon  { font-size: 1.4rem; margin-bottom: 0.5rem; }
.card-mod   { font-size: 0.58rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: #9ca3af; margin-bottom: 0.2rem; }
.card-title { font-size: 1rem; font-weight: 700; color: #111827; margin-bottom: 0.9rem; }
.card-divider { border: none; border-top: 1px solid #f3f4f6; margin-bottom: 0.85rem; }
.stat-lbl   { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #9ca3af; margin-bottom: 0.2rem; }
.stat-val   { font-size: 1.25rem; font-weight: 700; color: #111827; }
.stat-sub   { font-size: 0.65rem; color: #6b7280; margin-top: 0.1rem; }
.stat-empty { font-size: 0.75rem; color: #9ca3af; font-style: italic; }
.badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    font-size: 0.6rem; font-weight: 600;
    padding: 0.22rem 0.6rem;
    border-radius: 20px;
    margin-top: 0.6rem;
}
.badge-green { background: #ecfdf5; color: #059669; }
.badge-amber { background: #fffbeb; color: #d97706; }
.badge-gray  { background: #f9fafb; color: #6b7280; border: 1px solid #e5e7eb; }

.stButton > button {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    border: none !important;
    transition: opacity 0.15s !important;
}
.btn-green > button { background: #10b981 !important; color: #fff !important; }
.btn-green > button:hover { opacity: 0.88 !important; }
.btn-blue  > button { background: #3b82f6 !important; color: #fff !important; }
.btn-blue  > button:hover { opacity: 0.88 !important; }

.footer-info {
    background: #eff6ff;
    border: 1px solid #dbeafe;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.73rem;
    color: #3b82f6;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ──────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
MN = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
GR = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

today = date.today()

# ── LOAD DATA ────────────────────────────────────────────────────────────────
df_s = pd.DataFrame()
if os.path.exists(SALES_CACHE):
    try:
        df_s = pd.read_csv(SALES_CACHE)
        if not df_s.empty:
            df_s["date"] = pd.to_datetime(df_s["date"]).dt.date
            df_s = df_s.sort_values("date", ascending=False).reset_index(drop=True)
    except: df_s = pd.DataFrame()

df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        df_i = pd.read_csv(INV_CACHE)
        if not df_i.empty:
            df_i["DATE"] = pd.to_datetime(df_i["DATE"])
    except: df_i = pd.DataFrame()

# ── COMPUTE PREVIEWS ─────────────────────────────────────────────────────────
# Sales: last day + weekly total
s_last_val = s_last_date = s_last_cust = s_days = None
s_week_total = None

if not df_s.empty:
    r = df_s.iloc[0]
    s_last_val  = r.get("net_sales")
    s_last_date = r.get("date")
    s_last_cust = int(r["customers"]) if "customers" in r.index and pd.notna(r.get("customers")) else None
    s_days = (today - s_last_date).days if s_last_date else None

    # Εβδομαδιαίο σύνολο (Δευτέρα έως σήμερα)
    week_start = today - timedelta(days=today.weekday())  # Δευτέρα
    week_mask  = (df_s["date"] >= week_start) & (df_s["date"] <= today)
    week_df    = df_s[week_mask]
    if not week_df.empty:
        s_week_total = week_df["net_sales"].sum()

# Invoice: καθαρό μήνα
inv_net_month = None
if not df_i.empty:
    mm = (df_i["DATE"].dt.month == today.month) & (df_i["DATE"].dt.year == today.year)
    m_df = df_i[mm]
    if not m_df.empty:
        _inv = m_df[~m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        _crd = m_df[ m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        inv_net_month = _inv - _crd

# Invoice: καθαρό εβδομάδας
inv_net_week = None
if not df_i.empty:
    week_start_dt = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    week_end_dt   = datetime.combine(today, datetime.max.time())
    wm = (df_i["DATE"] >= week_start_dt) & (df_i["DATE"] <= week_end_dt)
    w_df_i = df_i[wm]
    if not w_df_i.empty:
        _wi = w_df_i[~w_df_i["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        _wc = w_df_i[ w_df_i["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        inv_net_week = _wi - _wc

# ── HEADER ───────────────────────────────────────────────────────────────────
day_str  = f"{GR[today.weekday()]}, {today.day} {MN[today.month-1]} {today.year}"
week_lbl = f"{(today - timedelta(days=today.weekday())).strftime('%d/%m')} – {(today - timedelta(days=today.weekday()) + timedelta(days=6)).strftime('%d/%m')}"

st.markdown(f"""
<div class="top-header">
  <div>
    <div class="brand-sub">AB Σκύρος · Κατάστημα 1082</div>
    <div class="brand-name">Business Hub</div>
  </div>
  <div>
    <div class="date-lbl">Σήμερα</div>
    <div class="date-val">{day_str}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SALES CARD CONTENT ───────────────────────────────────────────────────────
st.markdown('<div class="cards-wrap">', unsafe_allow_html=True)

# -- Card 1: Πωλήσεις
st.markdown('<div class="card card-green">', unsafe_allow_html=True)
st.markdown('<div class="card-icon">📊</div>', unsafe_allow_html=True)
st.markdown('<div class="card-mod">Ενότητα 1</div>', unsafe_allow_html=True)
st.markdown('<div class="card-title">Πωλήσεις Καταστήματος</div>', unsafe_allow_html=True)
st.markdown('<hr class="card-divider"/>', unsafe_allow_html=True)

if s_last_val is not None:
    date_lbl = s_last_date.strftime('%d/%m/%Y') if s_last_date else "—"
    cust_txt = f"{s_last_cust} πελάτες" if s_last_cust else ""
    st.markdown(f'<div class="stat-lbl">Τελευταία Πώληση · {date_lbl}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-val">{fmt(s_last_val)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-sub">{cust_txt}</div>', unsafe_allow_html=True)

    # Εβδομαδιαίο σύνολο
    if s_week_total is not None:
        st.markdown(f'<div class="stat-lbl" style="margin-top:.7rem;">Εβδομάδα {week_lbl}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-val" style="font-size:1rem;color:#059669;">{fmt(s_week_total)}</div>', unsafe_allow_html=True)

    if s_days == 0:
        st.markdown('<span class="badge badge-green">● Ενημερωμένο σήμερα</span>', unsafe_allow_html=True)
    elif s_days and s_days <= 2:
        st.markdown(f'<span class="badge badge-amber">● Πριν {s_days} μέρες</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="badge badge-gray">● Πριν {s_days} μέρες</span>' if s_days else '<span class="badge badge-gray">● —</span>', unsafe_allow_html=True)
else:
    st.markdown('<div class="stat-empty">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge badge-gray">● Εκκρεμεί ενημέρωση</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # close card

# -- Card 2: Τιμολόγια
st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
st.markdown('<div class="card-icon">📄</div>', unsafe_allow_html=True)
st.markdown('<div class="card-mod">Ενότητα 2</div>', unsafe_allow_html=True)
st.markdown('<div class="card-title">Έλεγχος Τιμολογίων</div>', unsafe_allow_html=True)
st.markdown('<hr class="card-divider"/>', unsafe_allow_html=True)

mn_name = MN[today.month-1]
if inv_net_week is not None:
    st.markdown(f'<div class="stat-lbl">Καθαρό Εβδομάδας · {week_lbl}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-val">{fmt(inv_net_week)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="stat-sub">Τιμολόγια − Πιστωτικά</div>', unsafe_allow_html=True)
elif inv_net_month is not None:
    st.markdown(f'<div class="stat-lbl">Καθαρό Μήνα · {mn_name} {today.year}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-val">{fmt(inv_net_month)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="stat-sub">Τιμολόγια − Πιστωτικά</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="stat-empty">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)

if inv_net_week is not None or inv_net_month is not None:
    st.markdown('<span class="badge badge-green">● Ενημερωμένο</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="badge badge-gray">● Εκκρεμεί φόρτωση</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # close card
st.markdown('</div>', unsafe_allow_html=True)  # close cards-wrap

# ── BUTTONS ──────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-green">', unsafe_allow_html=True)
    if st.button("📊  Πωλήσεις  →", use_container_width=True, key="go_sales"):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
    if st.button("📄  Τιμολόγια  →", use_container_width=True, key="go_inv"):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div class="footer-info">
  ℹ️ Τα δεδομένα ενημερώνονται αυτόματα από email. Μπείτε σε κάθε ενότητα για αναλυτικά στοιχεία και ενημέρωση.
</div>
""", unsafe_allow_html=True)
