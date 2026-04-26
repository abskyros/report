import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(
    page_title="AB Σκύρος 1082",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background: #0a0a0f !important;
    color: #e8e4dc !important;
}
.stApp { background: #0a0a0f !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.page-wrap { min-height: 100vh; padding: 2rem 1.5rem 4rem; max-width: 860px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.07); }
.brand-tag { font-family: 'Syne', sans-serif; font-size: 0.6rem; font-weight: 600; letter-spacing: 0.25em; text-transform: uppercase; color: #5a9f7a; }
.brand-title { font-family: 'Syne', sans-serif; font-size: 1.55rem; font-weight: 800; color: #f5f0e8; line-height: 1.1; margin-top: 0.2rem; }
.top-right { text-align: right; }
.date-label { font-size: 0.58rem; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(255,255,255,0.25); }
.date-val { font-family: 'Syne', sans-serif; font-size: 0.8rem; color: rgba(255,255,255,0.45); margin-top: 0.2rem; }
.card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.2rem; }
.dash-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.09); border-radius: 16px; padding: 1.4rem; position: relative; overflow: hidden; }
.dash-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--acc); border-radius: 16px 16px 0 0; }
.card-sales { --acc: linear-gradient(90deg,#5a9f7a,#3d8a63); }
.card-inv { --acc: linear-gradient(90deg,#6b8fd4,#4a72c4); }
.card-icon { font-size: 1.4rem; margin-bottom: 0.6rem; }
.card-label { font-size: 0.56rem; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(255,255,255,0.3); margin-bottom: 0.25rem; }
.card-title { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #f5f0e8; margin-bottom: 0.85rem; }
.card-stat { border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.85rem; }
.stat-lbl { font-size: 0.58rem; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.28); margin-bottom: 0.15rem; }
.stat-val { font-family: 'Syne', sans-serif; font-size: 1.3rem; font-weight: 700; color: #f5f0e8; }
.stat-sub { font-size: 0.62rem; color: rgba(255,255,255,0.3); margin-top: 0.1rem; }
.stat-empty { font-size: 0.7rem; color: rgba(255,255,255,0.18); font-style: italic; }
.dot-row { display: flex; align-items: center; gap: 0.35rem; margin-top: 0.45rem; }
.dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-ok { background: #5a9f7a; }
.dot-warn { background: #c9874a; }
.dot-off { background: rgba(255,255,255,0.15); }
.dot-txt { font-size: 0.58rem; color: rgba(255,255,255,0.28); }
.stButton > button { width: 100% !important; border-radius: 10px !important; font-family: 'DM Sans', sans-serif !important; font-size: 0.82rem !important; padding: 0.7rem 1rem !important; transition: all 0.2s !important; }
.btn-g > button { background: #5a9f7a !important; border: none !important; color: #0a0a0f !important; font-weight: 700 !important; }
.btn-g > button:hover { background: #4d8f6d !important; }
.btn-b > button { background: #6b8fd4 !important; border: none !important; color: #0a0a0f !important; font-weight: 700 !important; }
.btn-b > button:hover { background: #5a80c8 !important; }
.info { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 0.8rem 1rem; font-size: 0.72rem; color: rgba(255,255,255,0.3); margin-top: 1.2rem; }
@media(max-width:640px){
  .card-grid { grid-template-columns: 1fr; }
  .page-wrap { padding: 1.2rem 1rem 3rem; }
  .brand-title { font-size: 1.25rem; }
  .top-bar { flex-direction: column; gap: 0.5rem; }
  .top-right { text-align: left; }
}
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def load_sales():
    if os.path.exists(SALES_CACHE):
        df = pd.read_csv(SALES_CACHE)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            return df.sort_values("date", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def load_inv():
    if os.path.exists(INV_CACHE):
        df = pd.read_csv(INV_CACHE)
        if not df.empty:
            df["DATE"] = pd.to_datetime(df["DATE"])
        return df
    return pd.DataFrame(columns=["DATE","TYPE","VALUE"])

# ─── DATA ────────────────────────────────────────────────────────────────────
today = datetime.now().date()
df_s  = load_sales()
df_i  = load_inv()

last_val = last_date = last_cust = days_ago = None
if not df_s.empty:
    r = df_s.iloc[0]
    last_val  = r["net_sales"]
    last_date = r["date"]
    last_cust = int(r["customers"]) if pd.notna(r.get("customers")) else None
    days_ago  = (today - last_date).days

inv_month_net = None
if not df_i.empty:
    m_mask = (df_i["DATE"].dt.month == today.month) & (df_i["DATE"].dt.year == today.year)
    m_df   = df_i[m_mask]
    if not m_df.empty:
        _inv = m_df[~m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        _crd = m_df[ m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        inv_month_net = _inv - _crd

# ─── BUILD CARD HTML ─────────────────────────────────────────────────────────
day_str = f"{DAYS_GR[today.weekday()]}, {today.day} {MONTHS_GR[today.month-1]} {today.year}"

# Sales card content
if last_val is not None:
    s_stat = f"""
      <div class="stat-lbl">Τελευταία πώληση · {last_date.strftime('%d/%m/%Y')}</div>
      <div class="stat-val">{fmt(last_val)}</div>
      <div class="stat-sub">{f'{last_cust} πελάτες' if last_cust else ''}</div>
    """
    if days_ago == 0:   s_dot, s_dtxt = "dot dot-ok", "Ενημερωμένο σήμερα"
    elif days_ago <= 2: s_dot, s_dtxt = "dot dot-warn", f"Πριν {days_ago} μέρες"
    else:               s_dot, s_dtxt = "dot dot-off", f"Πριν {days_ago} μέρες"
else:
    s_stat = '<div class="stat-empty">Δεν υπάρχουν δεδομένα — πατήστε για φόρτωση</div>'
    s_dot, s_dtxt = "dot dot-off", "Εκκρεμεί ενημέρωση"

# Invoice card content
mn = MONTHS_GR[today.month-1]
if inv_month_net is not None:
    i_stat = f"""
      <div class="stat-lbl">Καθαρό σύνολο · {mn} {today.year}</div>
      <div class="stat-val">{fmt(inv_month_net)}</div>
      <div class="stat-sub">Τιμολόγια − Πιστωτικά</div>
    """
    i_dot, i_dtxt = "dot dot-ok", "Ενημερωμένο"
else:
    i_stat = '<div class="stat-empty">Δεν υπάρχουν δεδομένα — πατήστε για φόρτωση</div>'
    i_dot, i_dtxt = "dot dot-off", "Εκκρεμεί φόρτωση"

# ─── RENDER ──────────────────────────────────────────────────────────────────
st.markdown('<div class="page-wrap">', unsafe_allow_html=True)

st.markdown(f"""
<div class="top-bar">
  <div>
    <div class="brand-tag">AB Σκύρος · Κατάστημα 1082</div>
    <div class="brand-title">Business Hub</div>
  </div>
  <div class="top-right">
    <div class="date-label">Σήμερα</div>
    <div class="date-val">{day_str}</div>
  </div>
</div>
<div class="card-grid">
  <div class="dash-card card-sales">
    <div class="card-icon">📊</div>
    <div class="card-label">Ενότητα 1</div>
    <div class="card-title">Πωλήσεις Καταστήματος</div>
    <div class="card-stat">
      {s_stat}
      <div class="dot-row"><div class="{s_dot}"></div><span class="dot-txt">{s_dtxt}</span></div>
    </div>
  </div>
  <div class="dash-card card-inv">
    <div class="card-icon">📄</div>
    <div class="card-label">Ενότητα 2</div>
    <div class="card-title">Έλεγχος Τιμολογίων</div>
    <div class="card-stat">
      {i_stat}
      <div class="dot-row"><div class="{i_dot}"></div><span class="dot-txt">{i_dtxt}</span></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("📊  Πωλήσεις  →", use_container_width=True, key="nav_sales"):
        st.switch_page("pages/1_Πωλήσεις.py")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("📄  Τιμολόγια  →", use_container_width=True, key="nav_inv"):
        st.switch_page("pages/2_Τιμολόγια.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div class="info">
  ℹ️ &nbsp;Τα δεδομένα ενημερώνονται αυτόματα από email. Μπείτε σε κάθε ενότητα για αναλυτικά στοιχεία, ιστορικό και χειροκίνητη ανανέωση.
</div>
</div>
""", unsafe_allow_html=True)
