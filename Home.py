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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #f0f2f5 !important;
    color: #111827 !important;
}
.stApp { background: #f0f2f5 !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding: 1.8rem 1.5rem 4rem !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}

/* ── HERO HEADER ── */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-radius: 18px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.18);
}
.hero-left {}
.hero-tag {
    font-size: .58rem; font-weight: 700;
    letter-spacing: .22em; text-transform: uppercase;
    color: #34d399; margin-bottom: .3rem;
}
.hero-title {
    font-size: 1.6rem; font-weight: 800;
    color: #f8fafc; line-height: 1.1;
}
.hero-right { text-align: right; }
.hero-day {
    font-size: .65rem; color: #64748b;
    letter-spacing: .04em; margin-bottom: .15rem;
}
.hero-date {
    font-size: .85rem; font-weight: 500; color: #94a3b8;
}

/* ── WEEK BANNER ── */
.week-banner {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.1rem 1.5rem;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.wb-label {
    font-size: .6rem; font-weight: 700;
    letter-spacing: .18em; text-transform: uppercase;
    color: #94a3b8; margin-bottom: .2rem;
}
.wb-title {
    font-size: .88rem; font-weight: 700; color: #1e293b;
}
.wb-stats {
    display: flex; gap: 2rem; flex-wrap: wrap;
}
.wb-stat {}
.wb-stat-lbl {
    font-size: .58rem; font-weight: 600;
    letter-spacing: .12em; text-transform: uppercase;
    color: #94a3b8; margin-bottom: .15rem;
}
.wb-stat-val {
    font-size: 1.15rem; font-weight: 800; color: #0f172a;
}
.wb-stat-val.green { color: #059669; }
.wb-stat-val.blue  { color: #2563eb; }
.wb-empty {
    font-size: .75rem; color: #94a3b8; font-style: italic;
}
.wb-badge {
    display: inline-flex; align-items: center; gap: .3rem;
    font-size: .6rem; font-weight: 700;
    padding: .22rem .7rem; border-radius: 20px;
}
.badge-ok   { background: #dcfce7; color: #15803d; }
.badge-warn { background: #fef9c3; color: #854d0e; }
.badge-gray { background: #f1f5f9; color: #64748b; }

/* ── MODULE CARDS ── */
.cards-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}
@media(max-width: 620px) {
    .cards-row { grid-template-columns: 1fr; }
    .hero { flex-direction: column; align-items: flex-start; }
    .hero-right { text-align: left; }
    .wb-stats { gap: 1.2rem; }
}

.mcard {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.4rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.05);
    transition: box-shadow .15s;
}
.mcard:hover { box-shadow: 0 4px 16px rgba(0,0,0,.1); }
.mcard::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--top);
    border-radius: 16px 16px 0 0;
}
.mc-green { --top: linear-gradient(90deg, #10b981, #34d399); }
.mc-blue  { --top: linear-gradient(90deg, #2563eb, #60a5fa); }

.mc-head {
    display: flex; align-items: center; gap: .7rem;
    margin-bottom: 1rem;
}
.mc-icon {
    width: 38px; height: 38px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
}
.mc-icon-green { background: #ecfdf5; }
.mc-icon-blue  { background: #eff6ff; }
.mc-name { font-size: .93rem; font-weight: 700; color: #0f172a; }
.mc-sub  { font-size: .62rem; color: #64748b; margin-top: .05rem; }

.mc-divider {
    border: none; border-top: 1px solid #f1f5f9; margin: .9rem 0;
}

/* Last sale row */
.mc-row {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: .5rem;
}
.mc-row-lbl { font-size: .6rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; }
.mc-row-val { font-size: .9rem; font-weight: 700; color: #0f172a; }
.mc-row-val.big { font-size: 1.1rem; }
.mc-row-val.green { color: #059669; }
.mc-row-val.blue  { color: #2563eb; }

.mc-empty { font-size: .74rem; color: #94a3b8; font-style: italic; margin: .5rem 0; }

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .83rem !important;
    font-weight: 600 !important;
    padding: .65rem 1.1rem !important;
    border: none !important;
    transition: all .15s !important;
    width: 100% !important;
}
.btn-g > button { background: #10b981 !important; color: #fff !important; }
.btn-g > button:hover { background: #059669 !important; }
.btn-b > button { background: #2563eb !important; color: #fff !important; }
.btn-b > button:hover { background: #1d4ed8 !important; }

.footer-note {
    text-align: center;
    font-size: .68rem;
    color: #94a3b8;
    margin-top: .8rem;
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
MN_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
DAY_GR = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

# ── DATE HELPERS ─────────────────────────────────────────────────────────────
today      = date.today()
week_mon   = today - timedelta(days=today.weekday())       # Δευτέρα
week_sun   = week_mon + timedelta(days=6)                  # Κυριακή
week_label = f"{week_mon.strftime('%d/%m')} – {week_sun.strftime('%d/%m/%Y')}"

# ── LOAD DATA ────────────────────────────────────────────────────────────────
df_s = pd.DataFrame()
if os.path.exists(SALES_CACHE):
    try:
        df_s = pd.read_csv(SALES_CACHE)
        if not df_s.empty:
            df_s["date"] = pd.to_datetime(df_s["date"]).dt.date
            df_s = df_s.sort_values("date", ascending=False).reset_index(drop=True)
    except: pass

df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        df_i = pd.read_csv(INV_CACHE)
        if not df_i.empty:
            df_i["DATE"] = pd.to_datetime(df_i["DATE"])
    except: pass

# ── COMPUTE VALUES ────────────────────────────────────────────────────────────

# Sales
s_last_val  = None
s_last_date = None
s_last_cust = None
s_days_old  = None
s_week_total = None
s_week_days  = 0

if not df_s.empty:
    r = df_s.iloc[0]
    s_last_val  = r.get("net_sales")
    s_last_date = r.get("date")
    s_last_cust = int(r["customers"]) if pd.notna(r.get("customers", None)) else None
    s_days_old  = (today - s_last_date).days if s_last_date else None

    w_df = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    if not w_df.empty:
        s_week_total = w_df["net_sales"].sum()
        s_week_days  = len(w_df)

# Invoices
inv_week_net  = None
inv_month_net = None

if not df_i.empty:
    # Εβδομαδιαίο
    wmon_dt = datetime.combine(week_mon, datetime.min.time())
    wend_dt = datetime.combine(today, datetime.max.time())
    wi = df_i[(df_i["DATE"] >= wmon_dt) & (df_i["DATE"] <= wend_dt)]
    if not wi.empty:
        _i = wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        _c = wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        inv_week_net = _i - _c

    # Μηνιαίο
    mi = df_i[(df_i["DATE"].dt.month == today.month) & (df_i["DATE"].dt.year == today.year)]
    if not mi.empty:
        _i2 = mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        _c2 = mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        inv_month_net = _i2 - _c2

# ── HERO HEADER ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-tag">AB Σκύρος · Κατάστημα 1082</div>
    <div class="hero-title">Business Hub</div>
  </div>
  <div class="hero-right">
    <div class="hero-day">{DAY_GR[today.weekday()]}</div>
    <div class="hero-date">{today.day} {MN_GR[today.month-1]} {today.year}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── WEEK BANNER ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="week-banner">
  <div>
    <div class="wb-label">📅 Τρέχουσα Εβδομάδα</div>
    <div class="wb-title">{week_label}</div>
  </div>
  <div class="wb-stats">
    <div class="wb-stat">
      <div class="wb-stat-lbl">Πωλήσεις Εβδομάδας</div>
      <div class="wb-stat-val green">{fmt(s_week_total) if s_week_total is not None else "—"}</div>
    </div>
    <div class="wb-stat">
      <div class="wb-stat-lbl">Καθαρό Τιμολογίων</div>
      <div class="wb-stat-val blue">{fmt(inv_week_net) if inv_week_net is not None else "—"}</div>
    </div>
    <div class="wb-stat">
      <div class="wb-stat-lbl">Ημέρες με δεδομένα</div>
      <div class="wb-stat-val">{s_week_days} / 7</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── MODULE CARDS ──────────────────────────────────────────────────────────────
st.markdown('<div class="cards-row">', unsafe_allow_html=True)

# ── CARD 1: Πωλήσεις ─────────────────────────────────────────────────────────
st.markdown('<div class="mcard mc-green">', unsafe_allow_html=True)
st.markdown("""
<div class="mc-head">
  <div class="mc-icon mc-icon-green">📊</div>
  <div>
    <div class="mc-name">Πωλήσεις Καταστήματος</div>
    <div class="mc-sub">Ημερήσιος τζίρος · Τμήματα · Τάσεις</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('<hr class="mc-divider"/>', unsafe_allow_html=True)

if s_last_val is not None:
    date_str  = s_last_date.strftime("%d/%m/%Y") if s_last_date else "—"
    cust_str  = f"{s_last_cust} πελάτες" if s_last_cust else ""

    # Last day
    st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">Τελευταία Πώληση · {date_str}</span><span class="mc-row-val big">{fmt(s_last_val)}</span></div>', unsafe_allow_html=True)
    if cust_str:
        st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">Πελάτες</span><span class="mc-row-val">{cust_str}</span></div>', unsafe_allow_html=True)

    st.markdown('<hr class="mc-divider"/>', unsafe_allow_html=True)

    # Weekly
    st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">📅 Σύνολο Εβδομάδας ({week_mon.strftime("%d/%m")}–{week_sun.strftime("%d/%m")})</span><span class="mc-row-val big green">{fmt(s_week_total) if s_week_total else "—"}</span></div>', unsafe_allow_html=True)
    if s_week_days > 0:
        st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">Ημέρες καταγεγραμμένες</span><span class="mc-row-val">{s_week_days} / 7</span></div>', unsafe_allow_html=True)

    if s_days_old == 0:
        st.markdown('<span class="wb-badge badge-ok">● Ενημερωμένο σήμερα</span>', unsafe_allow_html=True)
    elif s_days_old and s_days_old <= 2:
        st.markdown(f'<span class="wb-badge badge-warn">● Πριν {s_days_old} ημέρες</span>', unsafe_allow_html=True)
    else:
        label = f"Πριν {s_days_old} ημέρες" if s_days_old else "Εκκρεμεί"
        st.markdown(f'<span class="wb-badge badge-gray">● {label}</span>', unsafe_allow_html=True)
else:
    st.markdown('<div class="mc-empty">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)
    st.markdown('<span class="wb-badge badge-gray">● Εκκρεμεί ενημέρωση</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── CARD 2: Τιμολόγια ────────────────────────────────────────────────────────
st.markdown('<div class="mcard mc-blue">', unsafe_allow_html=True)
st.markdown("""
<div class="mc-head">
  <div class="mc-icon mc-icon-blue">📄</div>
  <div>
    <div class="mc-name">Έλεγχος Τιμολογίων</div>
    <div class="mc-sub">Τιμολόγια · Πιστωτικά · Εβδομαδιαία εικόνα</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('<hr class="mc-divider"/>', unsafe_allow_html=True)

if inv_week_net is not None or inv_month_net is not None:
    if inv_week_net is not None:
        st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">📅 Καθαρό Εβδομάδας ({week_mon.strftime("%d/%m")}–{week_sun.strftime("%d/%m")})</span><span class="mc-row-val big blue">{fmt(inv_week_net)}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">Τιμολόγια − Πιστωτικά</span><span class="mc-row-val">Καθαρό σύνολο</span></div>', unsafe_allow_html=True)
        st.markdown('<hr class="mc-divider"/>', unsafe_allow_html=True)

    if inv_month_net is not None:
        mn_name = MN_GR[today.month-1]
        st.markdown(f'<div class="mc-row"><span class="mc-row-lbl">Καθαρό Μήνα · {mn_name} {today.year}</span><span class="mc-row-val big">{fmt(inv_month_net)}</span></div>', unsafe_allow_html=True)

    st.markdown('<span class="wb-badge badge-ok">● Ενημερωμένο</span>', unsafe_allow_html=True)
else:
    st.markdown('<div class="mc-empty">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)
    st.markdown('<span class="wb-badge badge-gray">● Εκκρεμεί φόρτωση</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # close cards-row

# ── NAV BUTTONS ───────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-g">', unsafe_allow_html=True)
    if st.button("📊  Πωλήσεις  →", use_container_width=True, key="go_sales"):
        st.switch_page("pages/1_Sales.py")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-b">', unsafe_allow_html=True)
    if st.button("📄  Τιμολόγια  →", use_container_width=True, key="go_inv"):
        st.switch_page("pages/2_Invoices.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="footer-note">Τα δεδομένα ενημερώνονται αυτόματα από email · AB Σκύρος 1082</div>', unsafe_allow_html=True)
