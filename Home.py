import streamlit as st
import pandas as pd
import os, re
from datetime import datetime, date, timedelta

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AB Skyros — Business Hub",
    layout="wide",
    page_icon=None,
    initial_sidebar_state="expanded",
)

HISTORY_FILE = "sales_history.csv"
MONTHS_GR = ["Ιανουαριος","Φεβρουαριος","Μαρτιος","Απριλιος","Μαιος","Ιουνιος",
              "Ιουλιος","Αυγουστος","Σεπτεμβριος","Οκτωβριος","Νοεμβριος","Δεκεμβριος"]
DAYS_GR   = ["Δευτερα","Τριτη","Τεταρτη","Πεμπτη","Παρασκευη","Σαββατο","Κυριακη"]

def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

def load_history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        return df.sort_values("date", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","netday","customers","avg_basket","depts"])

def period_stats(df, start, end):
    sub = df[(df["date"] >= start) & (df["date"] <= end)]
    if sub.empty: return {"total":0,"avg_day":0,"days":0,"peak":None,"peak_val":0}
    return {"total":sub["netday"].sum(),"avg_day":sub["netday"].mean(),
            "days":len(sub),"peak":sub.loc[sub["netday"].idxmax(),"date"],
            "peak_val":sub["netday"].max()}

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#f0f2f5;}
.block-container{padding:1.4rem 1.6rem 4rem;max-width:1240px;}
section[data-testid="stSidebar"]{background:#0f172a!important;border-right:1px solid #1e293b!important;min-width:210px!important;max-width:210px!important;}
section[data-testid="stSidebar"] *{color:#64748b!important;}
section[data-testid="stSidebar"] a{display:block;padding:.5rem .85rem;border-radius:6px;color:#64748b!important;font-size:.8rem;font-weight:500;text-decoration:none;transition:all .15s;margin-bottom:2px;}
section[data-testid="stSidebar"] a:hover{background:#1e293b;color:#e2e8f0!important;}
section[data-testid="stSidebar"] a[aria-current="page"]{background:#1e3a5f;color:#60a5fa!important;font-weight:600;}
#MainMenu,footer,header{visibility:hidden;}
.ph{background:#0f172a;border-radius:10px;padding:1.3rem 1.6rem;margin-bottom:1.4rem;display:flex;align-items:center;justify-content:space-between;}
.ph-ey{font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.2rem;}
.ph-h1{font-size:1.5rem;font-weight:700;color:#f8fafc;margin:0;}
.ph-rt{text-align:right;}
.ph-lbl{font-size:.62rem;color:#475569;}
.ph-val{font-family:'JetBrains Mono';font-size:.73rem;color:#64748b;}
.ng{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;}
@media(max-width:640px){.ng{grid-template-columns:1fr;}}
.nc{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:1.4rem;position:relative;overflow:hidden;transition:box-shadow .15s;}
.nc::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--s,#2563eb);}
.nc:hover{box-shadow:0 4px 16px rgba(0,0,0,.07);}
.nc-mod{font-size:.6rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--s,#2563eb);margin-bottom:.4rem;}
.nc-title{font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:.35rem;}
.nc-desc{font-size:.76rem;color:#64748b;line-height:1.55;}
.nc-tags{margin-top:.8rem;display:flex;gap:.35rem;flex-wrap:wrap;}
.nc-tag{font-size:.6rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:.18rem .5rem;border-radius:4px;background:#eff6ff;color:#1d4ed8;}
.kr{display:grid;gap:.85rem;margin:.9rem 0;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:880px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr4,.kr3{grid-template-columns:1fr;}}
.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:1rem 1.2rem;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#2563eb);}
.kl{font-size:.64rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:.4rem;}
.kv{font-family:'JetBrains Mono';font-size:1.15rem;font-weight:500;color:#0f172a;line-height:1.1;}
.sh{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;padding-bottom:.45rem;margin:1.6rem 0 .8rem;}
.bn{border-radius:7px;padding:.65rem 1rem;font-size:.78rem;font-weight:500;margin:.6rem 0;display:flex;align-items:center;gap:.5rem;}
.bn-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;}
.bn-warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;}
.bn-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;}
.div{border:none;border-top:1px solid #e2e8f0;margin:1.8rem 0;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #e2e8f0;gap:.2rem;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#94a3b8!important;font-size:.76rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:.5rem 1rem!important;border-radius:6px 6px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#1d4ed8!important;background:#eff6ff!important;border-bottom:2px solid #2563eb!important;}
.stButton>button{background:#2563eb!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.48rem 1.1rem!important;}
.stButton>button:hover{background:#1d4ed8!important;}
button[kind="secondary"]{background:#fff!important;color:#374151!important;border:1px solid #d1d5db!important;}
[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;}
[data-baseweb="select"]>div{background:#fff!important;border-color:#d1d5db!important;}
.stSpinner>div{border-top-color:#2563eb!important;}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.1rem 0 1.2rem;">
      <div style="font-size:.6rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.25rem;">AB SKYROS 1082</div>
      <div style="font-size:.95rem;font-weight:700;color:#f1f5f9;margin-bottom:1.4rem;">Business Hub</div>
      <div style="font-size:.58rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#374151;margin-bottom:.4rem;padding-left:.85rem;">NAVIGATION</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("Home.py",              label="Home")
    st.page_link("pages/1_Sales.py",     label="Sales Analytics")
    st.page_link("pages/2_Invoices.py",  label="Invoices")
    st.markdown(f'<div style="margin-top:2rem;padding-left:.85rem;font-size:.62rem;color:#374151;">{datetime.now().strftime("%d/%m/%Y %H:%M")}</div>', unsafe_allow_html=True)

# ─── HEADER ─────────────────────────────────────────────────────────────────────
today = date.today()
st.markdown(f"""
<div class="ph">
  <div>
    <div class="ph-ey">AB Skyros — Καταστημα 1082</div>
    <div class="ph-h1">Business Hub</div>
  </div>
  <div class="ph-rt">
    <div class="ph-lbl">Σημερα</div>
    <div class="ph-val">{DAYS_GR[today.weekday()]}, {today.day} {MONTHS_GR[today.month-1]} {today.year}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── MODULE CARDS ───────────────────────────────────────────────────────────────
st.markdown('<div class="sh">Ενοτητες</div>', unsafe_allow_html=True)
st.markdown("""
<div class="ng">
  <div class="nc" style="--s:#2563eb;">
    <div class="nc-mod">Sales Analytics</div>
    <div class="nc-title">Πωλησεις Καταστηματος</div>
    <div class="nc-desc">Ημερησιος τζιρος, αριθμος πελατων, αναλυση τμηματων και συγκρισεις περιοδων. Αυτοματη ανακτηση μεσω email και OCR.</div>
    <div class="nc-tags"><span class="nc-tag">Daily Sales</span><span class="nc-tag">OCR</span><span class="nc-tag">Departments</span></div>
  </div>
  <div class="nc" style="--s:#0891b2;">
    <div class="nc-mod" style="color:#0891b2;">Invoices</div>
    <div class="nc-title">Ελεγχος Τιμολογιων</div>
    <div class="nc-desc">Παρακολουθηση τιμολογιων και πιστωτικων εγγραφων. Εβδομαδιαια και μηνιαια εικονα με εξαγωγη δεδομενων CSV.</div>
    <div class="nc-tags"><span class="nc-tag" style="background:#ecfeff;color:#0e7490;">Weekly</span><span class="nc-tag" style="background:#ecfeff;color:#0e7490;">Monthly</span><span class="nc-tag" style="background:#ecfeff;color:#0e7490;">Export</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

ca, cb = st.columns(2)
with ca:
    if st.button("Sales Analytics →", use_container_width=True):
        st.switch_page("pages/1_Sales.py")
with cb:
    if st.button("Invoices →", use_container_width=True, type="secondary"):
        st.switch_page("pages/2_Invoices.py")

st.markdown('<hr class="div"/>', unsafe_allow_html=True)

# ─── SALES SNAPSHOT ─────────────────────────────────────────────────────────────
st.markdown('<div class="sh">Sales Analytics — Συνοψη</div>', unsafe_allow_html=True)
df_s = load_history()

if not df_s.empty:
    last     = df_s.iloc[0]
    prev     = df_s.iloc[1] if len(df_s) > 1 else None
    ld       = last["date"]
    days_old = (today - ld).days
    cur_total = period_stats(df_s, date(today.year,today.month,1), today)["total"]

    if days_old == 0:
        st.markdown('<div class="bn bn-ok">Ενημερωμενο — τελευταια αναφορα σημερα</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bn bn-warn">Τελευταια αναφορα: {ld.strftime("%d/%m/%Y")} ({days_old} ημερες πισω)</div>', unsafe_allow_html=True)

    def delta(now, pv, euro=True):
        if pv is None or pv == 0: return ""
        diff = now - pv; pct = diff/pv*100
        col = "#059669" if diff >= 0 else "#dc2626"
        return f'<div style="font-size:.7rem;color:{col};margin-top:.3rem;">{"+" if diff>=0 else ""}{pct:.1f}%</div>'

    p_net = prev["netday"]    if prev is not None else None
    p_cus = prev["customers"] if prev is not None else None
    p_avg = prev["avg_basket"]if prev is not None else None

    st.markdown(f"""<div class="kr kr4">
      <div class="kc" style="--a:#2563eb"><div class="kl">Πωλησεις {ld.strftime('%d/%m')}</div><div class="kv">{fmt_euro(last['netday'])}</div>{delta(last['netday'],p_net)}</div>
      <div class="kc" style="--a:#7c3aed"><div class="kl">Πελατες</div><div class="kv">{int(last['customers']) if pd.notna(last['customers']) else '—'}</div>{delta(last['customers'],p_cus,False)}</div>
      <div class="kc" style="--a:#0891b2"><div class="kl">ΜΟ Καλαθιου</div><div class="kv">{fmt_euro(last['avg_basket'])}</div>{delta(last['avg_basket'],p_avg)}</div>
      <div class="kc" style="--a:#059669"><div class="kl">Μηνιαιο ({MONTHS_GR[today.month-1][:3]})</div><div class="kv">{fmt_euro(cur_total)}</div></div>
    </div>""", unsafe_allow_html=True)

    ch = df_s[df_s["date"] >= (today - timedelta(days=13))].sort_values("date").copy()
    if not ch.empty:
        ch["D"] = ch["date"].apply(lambda d: d.strftime("%d/%m"))
        st.bar_chart(ch.set_index("D")["netday"], color="#2563eb", use_container_width=True, height=130)
else:
    st.markdown('<div class="bn bn-info">Δεν υπαρχουν δεδομενα πωλησεων. Μεταβειτε στο Sales Analytics.</div>', unsafe_allow_html=True)

st.markdown('<hr class="div"/>', unsafe_allow_html=True)

# ─── INVOICE SNAPSHOT ───────────────────────────────────────────────────────────
st.markdown('<div class="sh">Τιμολογια — Συνοψη</div>', unsafe_allow_html=True)
inv_df = st.session_state.get("invoice_data", pd.DataFrame())

if not inv_df.empty:
    ws = today - timedelta(days=today.weekday())
    w_mask = (inv_df["DATE"].dt.date >= ws) & (inv_df["DATE"].dt.date <= today)
    m_mask = (inv_df["DATE"].dt.month == today.month) & (inv_df["DATE"].dt.year == today.year)
    w_inv = inv_df[w_mask & ~inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    w_crd = inv_df[w_mask &  inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    m_inv = inv_df[m_mask & ~inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    m_crd = inv_df[m_mask &  inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    st.markdown(f"""<div class="kr kr4">
      <div class="kc" style="--a:#0891b2"><div class="kl">Τιμολογια Εβδ.</div><div class="kv">{fmt_euro(w_inv)}</div></div>
      <div class="kc" style="--a:#dc2626"><div class="kl">Πιστωτικα Εβδ.</div><div class="kv">{fmt_euro(w_crd)}</div></div>
      <div class="kc" style="--a:#0891b2"><div class="kl">Τιμολογια Μηνα</div><div class="kv">{fmt_euro(m_inv)}</div></div>
      <div class="kc" style="--a:#059669"><div class="kl">Καθαρο Μηνα</div><div class="kv">{fmt_euro(m_inv-m_crd)}</div></div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown('<div class="bn bn-info">Τα τιμολογια δεν εχουν φορτωθει. Μεταβειτε στην ενοτητα Invoices.</div>', unsafe_allow_html=True)
