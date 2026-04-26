import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

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
.block-container { padding: 2rem 1.5rem 4rem !important; max-width: 860px !important; margin: 0 auto !important; }

.top-header {
    background: #111827;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}
.brand-sub { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: #6ee7b7; margin-bottom: 0.3rem; }
.brand-name { font-size: 1.4rem; font-weight: 700; color: #f9fafb; }
.date-lbl { font-size: 0.6rem; color: #6b7280; text-align: right; }
.date-val { font-size: 0.8rem; color: #9ca3af; text-align: right; margin-top: 0.15rem; }

.cards-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
@media(max-width:600px){ .cards-wrap { grid-template-columns: 1fr; } }

.card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1.4rem;
    position: relative;
    overflow: hidden;
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

.card-icon  { font-size: 1.5rem; margin-bottom: 0.5rem; }
.card-mod   { font-size: 0.58rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: #9ca3af; margin-bottom: 0.2rem; }
.card-title { font-size: 1rem; font-weight: 700; color: #111827; margin-bottom: 1rem; }
.card-divider { border: none; border-top: 1px solid #f3f4f6; margin-bottom: 0.85rem; }
.stat-lbl { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #9ca3af; margin-bottom: 0.2rem; }
.stat-val { font-size: 1.3rem; font-weight: 700; color: #111827; }
.stat-sub { font-size: 0.65rem; color: #6b7280; margin-top: 0.1rem; }
.stat-empty { font-size: 0.75rem; color: #9ca3af; font-style: italic; }

.badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    font-size: 0.6rem; font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    margin-top: 0.6rem;
}
.badge-green { background: #ecfdf5; color: #059669; }
.badge-amber { background: #fffbeb; color: #d97706; }
.badge-gray  { background: #f9fafb; color: #6b7280; }

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
@media(max-width:600px){
  .top-header { flex-direction: column; align-items: flex-start; }
  .date-lbl, .date-val { text-align: left; }
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

# Sales cache
df_s = pd.DataFrame()
if os.path.exists(SALES_CACHE):
    try:
        df_s = pd.read_csv(SALES_CACHE)
        if not df_s.empty:
            df_s["date"] = pd.to_datetime(df_s["date"]).dt.date
            df_s = df_s.sort_values("date", ascending=False).reset_index(drop=True)
    except: df_s = pd.DataFrame()

# Invoice cache
df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        df_i = pd.read_csv(INV_CACHE)
        if not df_i.empty:
            df_i["DATE"] = pd.to_datetime(df_i["DATE"])
    except: df_i = pd.DataFrame()

# ── COMPUTE PREVIEWS ─────────────────────────────────────────────────────────
# Sales
s_val = s_date = s_cust = s_days = None
if not df_s.empty:
    r = df_s.iloc[0]
    s_val  = r.get("net_sales")
    s_date = r.get("date")
    s_cust = int(r["customers"]) if "customers" in r and pd.notna(r.get("customers")) else None
    s_days = (today - s_date).days if s_date else None

# Invoices — καθαρό μήνα
inv_net = None
if not df_i.empty:
    mm = (df_i["DATE"].dt.month == today.month) & (df_i["DATE"].dt.year == today.year)
    m_df = df_i[mm]
    if not m_df.empty:
        _inv = m_df[~m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        _crd = m_df[ m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        inv_net = _inv - _crd

# ── HEADER ───────────────────────────────────────────────────────────────────
day_str = f"{GR[today.weekday()]}, {today.day} {MN[today.month-1]} {today.year}"

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

# ── CARDS ────────────────────────────────────────────────────────────────────
if s_val is not None:
    s_stat = f"""
      <div class="stat-lbl">Τελευταία Πώληση · {s_date.strftime('%d/%m/%Y')}</div>
      <div class="stat-val">{fmt(s_val)}</div>
      <div class="stat-sub">{f'{s_cust} πελάτες' if s_cust else ''}</div>
    """
    if s_days == 0:
        s_badge = '<span class="badge badge-green">● Ενημερωμένο σήμερα</span>'
    elif s_days and s_days <= 2:
        s_badge = f'<span class="badge badge-amber">● Πριν {s_days} μέρες</span>'
    else:
        s_badge = f'<span class="badge badge-gray">● Πριν {s_days} μέρες</span>' if s_days else '<span class="badge badge-gray">● —</span>'
else:
    s_stat  = '<div class="stat-empty">Δεν υπάρχουν δεδομένα ακόμα</div>'
    s_badge = '<span class="badge badge-gray">● Εκκρεμεί ενημέρωση</span>'

mn_name = MN[today.month-1]
if inv_net is not None:
    i_stat  = f"""
      <div class="stat-lbl">Καθαρό · {mn_name} {today.year}</div>
      <div class="stat-val">{fmt(inv_net)}</div>
      <div class="stat-sub">Τιμολόγια − Πιστωτικά</div>
    """
    i_badge = '<span class="badge badge-green">● Ενημερωμένο</span>'
else:
    i_stat  = '<div class="stat-empty">Δεν υπάρχουν δεδομένα ακόμα</div>'
    i_badge = '<span class="badge badge-gray">● Εκκρεμεί φόρτωση</span>'

st.markdown(f"""
<div class="cards-wrap">
  <div class="card card-green">
    <div class="card-icon">📊</div>
    <div class="card-mod">Ενότητα 1</div>
    <div class="card-title">Πωλήσεις Καταστήματος</div>
    <hr class="card-divider"/>
    {s_stat}
    {s_badge}
  </div>
  <div class="card card-blue">
    <div class="card-icon">📄</div>
    <div class="card-mod">Ενότητα 2</div>
    <div class="card-title">Έλεγχος Τιμολογίων</div>
    <hr class="card-divider"/>
    {i_stat}
    {i_badge}
  </div>
</div>
""", unsafe_allow_html=True)

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
