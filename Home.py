import streamlit as st
import pandas as pd
import os, re
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
import logging

logging.basicConfig(level=logging.WARNING)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AB Skyros — Business Hub",
    layout="wide",
    page_icon=None,
    initial_sidebar_state="collapsed",  # Κρύβουμε την sidebar
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

# ─── CSS - Responsive + Mobile Friendly ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#f0f2f5;}
.block-container{padding:1rem 1rem 3rem!important;max-width:100%!important;}

/* Hide Sidebar */
section[data-testid="stSidebar"]{display:none!important;}

#MainMenu,footer,header{visibility:hidden;}

/* Header */
.ph{background:#0f172a;border-radius:10px;padding:1rem;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;}
.ph-ey{font-size:.55rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.2rem;}
.ph-h1{font-size:1.3rem;font-weight:700;color:#f8fafc;margin:0;}
.ph-rt{text-align:right;}
.ph-lbl{font-size:.55rem;color:#475569;}
.ph-val{font-family:'JetBrains Mono';font-size:.65rem;color:#64748b;}

/* Module Cards Grid */
.ng{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;}
@media(max-width:768px){.ng{grid-template-columns:1fr;}}
.nc{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:1.2rem;position:relative;overflow:hidden;transition:box-shadow .15s;}
.nc::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--s,#2563eb);}
.nc:hover{box-shadow:0 4px 16px rgba(0,0,0,.07);}
.nc-mod{font-size:.55rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--s,#2563eb);margin-bottom:.4rem;}
.nc-title{font-size:.95rem;font-weight:700;color:#0f172a;margin-bottom:.35rem;}
.nc-desc{font-size:.7rem;color:#64748b;line-height:1.55;}
.nc-tags{margin-top:.8rem;display:flex;gap:.35rem;flex-wrap:wrap;}
.nc-tag{font-size:.55rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:.15rem .45rem;border-radius:4px;background:#eff6ff;color:#1d4ed8;}

/* KPI Cards */
.kr{display:grid;gap:.85rem;margin:.9rem 0;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
.kr2{grid-template-columns:repeat(2,1fr);}
@media(max-width:1024px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:640px){.kr4,.kr3,.kr2{grid-template-columns:1fr;}}

.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:.9rem 1rem;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#2563eb);}
.kl{font-size:.6rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:.35rem;}
.kv{font-family:'JetBrains Mono';font-size:1rem;font-weight:500;color:#0f172a;line-height:1.1;}

/* Section Headers */
.sh{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;padding-bottom:.45rem;margin:1.6rem 0 .8rem;}

/* Badges */
.bn{border-radius:7px;padding:.6rem .9rem;font-size:.75rem;font-weight:500;margin:.6rem 0;display:flex;align-items:center;gap:.5rem;}
.bn-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;}
.bn-warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;}
.bn-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;}

/* Divider */
.div{border:none;border-top:1px solid #e2e8f0;margin:1.8rem 0;}

/* Buttons */
.stButton>button{background:#2563eb!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.45rem 1rem!important;}
.stButton>button:hover{background:#1d4ed8!important;}
button[kind="secondary"]{background:#fff!important;color:#374151!important;border:1px solid #d1d5db!important;}

/* Tables & DataFrames */
[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;}
[data-baseweb="select"]>div{background:#fff!important;border-color:#d1d5db!important;}

/* Mobile optimizations */
@media(max-width:640px){
  .ph{padding:.8rem;flex-direction:column;align-items:flex-start;}
  .ph-h1{font-size:1.1rem;}
  .kv{font-size:.9rem;}
  .nc{padding:1rem;}
  .sh{margin:1.2rem 0 .6rem;}
}

/* Email Check Info */
.email-list{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:1rem;max-height:400px;overflow-y:auto;}
.email-item{padding:.6rem;border-bottom:1px solid #f0f0f0;font-size:.75rem;}
.email-item:last-child{border-bottom:none;}
.email-from{font-weight:600;color:#0f172a;}
.email-subject{color:#475569;margin-top:.2rem;word-break:break-word;}
.email-date{font-size:.65rem;color:#94a3b8;margin-top:.2rem;}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ──────────────────────────────────────────────────────────────
if "emails_checked" not in st.session_state:
    st.session_state.emails_checked = False
if "emails_list" not in st.session_state:
    st.session_state.emails_list = []

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
    <div class="nc-desc">Ημερησιος τζιρος, αριθμος πελατων, αναλυση τμηματων και συγκρισεις περιοδων.</div>
    <div class="nc-tags"><span class="nc-tag">Daily Sales</span><span class="nc-tag">OCR</span><span class="nc-tag">Departments</span></div>
  </div>
  <div class="nc" style="--s:#0891b2;">
    <div class="nc-mod" style="color:#0891b2;">Invoices</div>
    <div class="nc-title">Ελεγχος Τιμολογιων</div>
    <div class="nc-desc">Παρακολουθηση τιμολογιων και πιστωτικων εγγραφων. Εβδομαδιαια και μηνιαια εικονα.</div>
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

# ─── EMAIL CHECKING SECTION ─────────────────────────────────────────────────────
st.markdown('<div class="sh">🔍 Έλεγχος Email — Πρώτα 20</div>', unsafe_allow_html=True)

with st.expander("**📧 Διαβάστε τα emails για έλεγχο**", expanded=False):
    col1, col2 = st.columns([2, 1])
    with col1:
        email = st.text_input("Email διεύθυνση", placeholder="your@email.com", key="email_input")
    with col2:
        password = st.text_input("Κωδικός", type="password", key="pass_input")
    
    if st.button("✓ Διαβάστε τα πρώτα 20 emails", use_container_width=True):
        if not email or not password:
            st.error("Εισάγετε email και κωδικό")
        else:
            with st.spinner("Σύνδεση με mail server..."):
                try:
                    mb = MailBox('imap.gmail.com')
                    mb.login(email, password)
                    
                    # Διαβάζουμε τα 20 πρώτα emails
                    messages = list(mb.fetch(limit=20, reverse=True))
                    
                    emails_data = []
                    for msg in messages:
                        emails_data.append({
                            "from": msg.from_,
                            "subject": msg.subject,
                            "date": msg.date
                        })
                    
                    st.session_state.emails_list = emails_data
                    st.session_state.emails_checked = True
                    mb.logout()
                    
                    st.success(f"✓ Διαβάστηκαν {len(emails_data)} emails!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Σφάλμα: {str(e)}")

# Εμφανίζουμε τα emails αν έχουν διαβαστεί
if st.session_state.emails_checked and st.session_state.emails_list:
    st.markdown('<div style="margin-top:1rem;"><strong>Λίστα Emails:</strong></div>', unsafe_allow_html=True)
    st.markdown('<div class="email-list">', unsafe_allow_html=True)
    for idx, email_data in enumerate(st.session_state.emails_list, 1):
        st.markdown(f'''
        <div class="email-item">
            <span class="email-from">#{idx} {email_data["from"]}</span>
            <div class="email-subject">📌 {email_data["subject"][:70]}...</div>
            <div class="email-date">📅 {email_data["date"].strftime("%d/%m/%Y %H:%M") if email_data["date"] else "—"}</div>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="bn bn-ok">✓ Ενημερωμενο — τελευταια αναφορα σημερα</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bn bn-warn">⚠ Τελευταια αναφορα: {ld.strftime("%d/%m/%Y")} ({days_old} ημερες πισω)</div>', unsafe_allow_html=True)

    def delta(now, pv, euro=True):
        if pv is None or pv == 0: return ""
        diff = now - pv; pct = diff/pv*100
        col = "#059669" if diff >= 0 else "#dc2626"
        sym = "▲" if diff >= 0 else "▼"
        return f'<div style="font-size:.65rem;color:{col};margin-top:.25rem;">{sym} {"+" if diff>=0 else ""}{pct:.1f}%</div>'

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
        st.bar_chart(ch.set_index("D")["netday"], color="#2563eb", use_container_width=True, height=180)
else:
    st.markdown('<div class="bn bn-info">ℹ Δεν υπαρχουν δεδομενα πωλησεων. Μεταβειτε στο Sales Analytics.</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="bn bn-info">ℹ Τα τιμολογια δεν εχουν φορτωθει. Μεταβειτε στην ενοτητα Invoices.</div>', unsafe_allow_html=True)

st.markdown('<hr class="div"/>', unsafe_allow_html=True)

# ─── COMBINED TOTAL SUMMARY ─────────────────────────────────────────────────────
st.markdown('<div class="sh">📊 Συνολικο Καθαρο Τζιρο (Sales + Invoices)</div>', unsafe_allow_html=True)

sales_month = 0
invoices_net_month = 0

if not df_s.empty:
    cur_stats = period_stats(df_s, date(today.year,today.month,1), today)
    sales_month = cur_stats["total"]

if not inv_df.empty:
    m_mask = (inv_df["DATE"].dt.month == today.month) & (inv_df["DATE"].dt.year == today.year)
    m_inv = inv_df[m_mask & ~inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    m_crd = inv_df[m_mask &  inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    invoices_net_month = m_inv - m_crd

total_net = sales_month + invoices_net_month

st.markdown(f"""<div class="kr kr3">
  <div class="kc" style="--a:#2563eb"><div class="kl">Sales Μηνα</div><div class="kv">{fmt_euro(sales_month)}</div></div>
  <div class="kc" style="--a:#0891b2"><div class="kl">Invoices Καθαρο</div><div class="kv">{fmt_euro(invoices_net_month)}</div></div>
  <div class="kc" style="--a:#059669;border-left:4px solid #059669;"><div class="kl">🎯 Συνολο</div><div class="kv" style="color:#059669;font-weight:700;">{fmt_euro(total_net)}</div></div>
</div>""", unsafe_allow_html=True)
