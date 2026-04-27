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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#f0f4f8!important;color:#1a202c!important;}
.stApp{background:#f0f4f8!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1rem 3rem!important;max-width:480px!important;margin:0 auto!important;}

/* ── HEADER ── */
.hdr{
  background:#1a202c;
  border-radius:16px;
  padding:1.4rem 1.6rem;
  margin-bottom:1rem;
  display:flex;
  justify-content:space-between;
  align-items:center;
}
.hdr-left{}
.hdr-tag{font-size:.55rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:#48bb78;margin-bottom:.2rem;}
.hdr-name{font-size:1.5rem;font-weight:800;color:#f7fafc;}
.hdr-right{text-align:right;}
.hdr-day{font-size:.58rem;color:#718096;margin-bottom:.1rem;}
.hdr-date{font-size:.78rem;font-weight:600;color:#a0aec0;}

/* ── WEEK STRIP ── */
.week{
  background:#fff;
  border:1px solid #e2e8f0;
  border-radius:12px;
  padding:.9rem 1.2rem;
  margin-bottom:1rem;
  display:flex;
  justify-content:space-between;
  align-items:center;
  box-shadow:0 1px 3px rgba(0,0,0,.04);
}
.week-lbl{font-size:.55rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#a0aec0;margin-bottom:.15rem;}
.week-range{font-size:.8rem;font-weight:700;color:#2d3748;}
.week-stats{display:flex;gap:1.5rem;}
.ws{text-align:right;}
.ws-lbl{font-size:.52rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#a0aec0;margin-bottom:.1rem;}
.ws-val{font-size:1rem;font-weight:800;}
.ws-val.g{color:#38a169;}
.ws-val.b{color:#3182ce;}
.ws-val.gray{color:#718096;}

/* ── CARDS ── */
.card{
  background:#fff;
  border:1px solid #e2e8f0;
  border-radius:14px;
  padding:1.2rem 1.4rem;
  margin-bottom:.85rem;
  position:relative;
  overflow:hidden;
  box-shadow:0 1px 3px rgba(0,0,0,.05);
}
.card::before{
  content:'';
  position:absolute;top:0;left:0;right:0;
  height:3px;
  background:var(--top);
  border-radius:14px 14px 0 0;
}
.c-green{--top:#48bb78;}
.c-blue{--top:#4299e1;}

.card-head{display:flex;align-items:center;gap:.7rem;margin-bottom:.9rem;}
.card-ico{
  width:36px;height:36px;border-radius:9px;
  display:flex;align-items:center;justify-content:center;
  font-size:1.1rem;
}
.ico-g{background:#f0fff4;}
.ico-b{background:#ebf8ff;}
.card-name{font-size:.9rem;font-weight:700;color:#1a202c;}
.card-sub{font-size:.6rem;color:#a0aec0;margin-top:.05rem;}

.stat-row{display:flex;justify-content:space-between;align-items:baseline;padding:.35rem 0;border-bottom:1px solid #f7fafc;}
.stat-row:last-child{border-bottom:none;}
.stat-lbl{font-size:.6rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#a0aec0;}
.stat-val{font-size:.95rem;font-weight:700;color:#1a202c;}
.stat-val.big{font-size:1.1rem;}
.stat-val.g{color:#38a169;}
.stat-val.b{color:#3182ce;}
.empty{font-size:.72rem;color:#a0aec0;font-style:italic;padding:.3rem 0;}

.badge{
  display:inline-flex;align-items:center;gap:.25rem;
  font-size:.58rem;font-weight:700;
  padding:.18rem .55rem;border-radius:20px;margin-top:.6rem;
}
.b-ok{background:#f0fff4;color:#276749;}
.b-warn{background:#fffbeb;color:#744210;}
.b-gray{background:#f7fafc;color:#718096;border:1px solid #e2e8f0;}

/* ── BUTTONS ── */
.stButton>button{
  border-radius:10px!important;
  font-family:'Inter',sans-serif!important;
  font-size:.85rem!important;
  font-weight:700!important;
  padding:.7rem 1rem!important;
  border:none!important;
  transition:all .15s!important;
  width:100%!important;
}
.btn-g>button{background:#48bb78!important;color:#fff!important;}
.btn-g>button:hover{background:#38a169!important;}
.btn-b>button{background:#4299e1!important;color:#fff!important;}
.btn-b>button:hover{background:#3182ce!important;}

.foot{text-align:center;font-size:.6rem;color:#cbd5e0;margin-top:.6rem;}

@media(max-width:400px){
  .hdr{flex-direction:column;align-items:flex-start;gap:.5rem;}
  .hdr-right{text-align:left;}
  .week{flex-direction:column;align-items:flex-start;gap:.6rem;}
  .week-stats{justify-content:flex-start;}
  .ws{text-align:left;}
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ────────────────────────────────────────────────────────────────
SALES_CACHE = "sales_cache.csv"
INV_CACHE   = "invoices_cache.csv"
MN  = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
DAY = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]

def fmt(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return "—"
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

today    = date.today()
week_mon = today - timedelta(days=today.weekday())
week_sun = week_mon + timedelta(days=6)
week_lbl = f"{week_mon.strftime('%d/%m')} – {week_sun.strftime('%d/%m')}"

# ── LOAD ─────────────────────────────────────────────────────────────────────
df_s = pd.DataFrame()
if os.path.exists(SALES_CACHE):
    try:
        df_s = pd.read_csv(SALES_CACHE)
        if not df_s.empty:
            df_s["date"] = pd.to_datetime(df_s["date"]).dt.date
            # Κρατάμε μόνο την υψηλότερη τιμή ανά ημέρα
            df_s = (df_s.sort_values("net_sales", ascending=False)
                        .drop_duplicates("date", keep="first")
                        .sort_values("date", ascending=False)
                        .reset_index(drop=True))
    except: df_s = pd.DataFrame()

df_i = pd.DataFrame()
if os.path.exists(INV_CACHE):
    try:
        df_i = pd.read_csv(INV_CACHE)
        if not df_i.empty:
            df_i["DATE"] = pd.to_datetime(df_i["DATE"])
    except: df_i = pd.DataFrame()

# ── COMPUTE ──────────────────────────────────────────────────────────────────
# Sales
s_last_val = s_last_date = s_cust = s_days = None
s_week = 0; s_wdays = 0

if not df_s.empty:
    r = df_s.iloc[0]
    s_last_val  = r.get("net_sales")
    s_last_date = r.get("date")
    s_cust      = int(r["customers"]) if pd.notna(r.get("customers")) else None
    s_days      = (today - s_last_date).days if s_last_date else None
    w = df_s[(df_s["date"] >= week_mon) & (df_s["date"] <= today)]
    if not w.empty:
        s_week  = w["net_sales"].sum()
        s_wdays = len(w)

# Invoices
inv_week = inv_month = None
if not df_i.empty:
    wdt = datetime.combine(week_mon, datetime.min.time())
    wet = datetime.combine(today, datetime.max.time())
    wi  = df_i[(df_i["DATE"]>=wdt)&(df_i["DATE"]<=wet)]
    if not wi.empty:
        _i = wi[~wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        _c = wi[ wi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        inv_week = _i - _c
    mi = df_i[(df_i["DATE"].dt.month==today.month)&(df_i["DATE"].dt.year==today.year)]
    if not mi.empty:
        _i2 = mi[~mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        _c2 = mi[ mi["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        inv_month = _i2 - _c2

# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hdr">
  <div class="hdr-left">
    <div class="hdr-tag">AB Σκύρος · 1082</div>
    <div class="hdr-name">Business Hub</div>
  </div>
  <div class="hdr-right">
    <div class="hdr-day">{DAY[today.weekday()]}</div>
    <div class="hdr-date">{today.day} {MN[today.month-1]} {today.year}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── WEEK STRIP ────────────────────────────────────────────────────────────────
s_week_str   = fmt(s_week)   if s_week   else "—"
inv_week_str = fmt(inv_week) if inv_week is not None else "—"

s_week_cls   = "g"    if s_week   else "gray"
inv_week_cls = "b"    if inv_week is not None else "gray"

st.markdown(f"""
<div class="week">
  <div>
    <div class="week-lbl">📅 Τρέχουσα Εβδομάδα</div>
    <div class="week-range">{week_lbl}</div>
  </div>
  <div class="week-stats">
    <div class="ws">
      <div class="ws-lbl">Πωλήσεις</div>
      <div class="ws-val {s_week_cls}">{s_week_str}</div>
    </div>
    <div class="ws">
      <div class="ws-lbl">Καθ. Τιμολ.</div>
      <div class="ws-val {inv_week_cls}">{inv_week_str}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── CARD: ΠΩΛΗΣΕΙΣ ────────────────────────────────────────────────────────────
st.markdown('<div class="card c-green">', unsafe_allow_html=True)
st.markdown("""
<div class="card-head">
  <div class="card-ico ico-g">📊</div>
  <div>
    <div class="card-name">Πωλήσεις</div>
    <div class="card-sub">Ημερήσιος τζίρος καταστήματος</div>
  </div>
</div>
""", unsafe_allow_html=True)

if s_last_val is not None:
    dl = s_last_date.strftime("%d/%m/%Y")
    st.markdown(f'<div class="stat-row"><span class="stat-lbl">Τελευταία · {dl}</span><span class="stat-val big g">{fmt(s_last_val)}</span></div>', unsafe_allow_html=True)
    if s_cust:
        st.markdown(f'<div class="stat-row"><span class="stat-lbl">Πελάτες</span><span class="stat-val">{s_cust}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-row"><span class="stat-lbl">Εβδομάδα {week_lbl}</span><span class="stat-val g">{fmt(s_week) if s_week else "—"}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-row"><span class="stat-lbl">Ημέρες εβδ.</span><span class="stat-val">{s_wdays} / 7</span></div>', unsafe_allow_html=True)
    if s_days == 0:   st.markdown('<span class="badge b-ok">● Ενημερωμένο σήμερα</span>', unsafe_allow_html=True)
    elif s_days == 1: st.markdown('<span class="badge b-warn">● Χθες</span>', unsafe_allow_html=True)
    elif s_days and s_days <= 3: st.markdown(f'<span class="badge b-warn">● Πριν {s_days} μέρες</span>', unsafe_allow_html=True)
    else: st.markdown(f'<span class="badge b-gray">● Πριν {s_days} μέρες</span>', unsafe_allow_html=True)
else:
    st.markdown('<div class="empty">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge b-gray">● Εκκρεμεί ενημέρωση</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── CARD: ΤΙΜΟΛΟΓΙΑ ──────────────────────────────────────────────────────────
st.markdown('<div class="card c-blue">', unsafe_allow_html=True)
st.markdown("""
<div class="card-head">
  <div class="card-ico ico-b">📄</div>
  <div>
    <div class="card-name">Τιμολόγια</div>
    <div class="card-sub">Παραστατικά και πιστωτικά</div>
  </div>
</div>
""", unsafe_allow_html=True)

if inv_week is not None or inv_month is not None:
    if inv_week is not None:
        st.markdown(f'<div class="stat-row"><span class="stat-lbl">Καθαρό εβδ. {week_lbl}</span><span class="stat-val big b">{fmt(inv_week)}</span></div>', unsafe_allow_html=True)
    if inv_month is not None:
        st.markdown(f'<div class="stat-row"><span class="stat-lbl">Καθαρό {MN[today.month-1]} {today.year}</span><span class="stat-val">{fmt(inv_month)}</span></div>', unsafe_allow_html=True)
    st.markdown('<span class="badge b-ok">● Ενημερωμένο</span>', unsafe_allow_html=True)
else:
    st.markdown('<div class="empty">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge b-gray">● Εκκρεμεί φόρτωση</span>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── NAVIGATION ────────────────────────────────────────────────────────────────
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

st.markdown('<div class="foot">AB Σκύρος 1082 · Ενημέρωση από email</div>', unsafe_allow_html=True)
