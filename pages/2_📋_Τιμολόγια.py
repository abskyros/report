import streamlit as st
import pandas as pd
import io, os, sys
from imap_tools import MailBox, AND
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import COMMON_CSS, MONTHS_GR, fmt_euro

st.set_page_config(page_title="Τιμολόγια · ΑΒ ΣΚΥΡΟΣ",
                   layout="wide", page_icon="📋", initial_sidebar_state="expanded")
st.markdown(COMMON_CSS, unsafe_allow_html=True)

EMAIL_USER    = "abf.skyros@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASS"]
SENDER_EMAIL  = "Notifications@WeDoConnect.com"

# ── Sidebar nav ───────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.5rem;">
      <div style="font-size:.65rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#10b981;margin-bottom:.3rem;">ΑΒ ΣΚΥΡΟΣ 1082</div>
      <div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;">Business Hub</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#334155;margin-bottom:.5rem;">ΠΛΟΗΓΗΣΗ</div>', unsafe_allow_html=True)
    st.page_link("Home.py",                       label="🏠  Αρχική Σελίδα")
    st.page_link("pages/1_📊_Πωλήσεις.py",        label="📊  Sales Analytics")
    st.page_link("pages/2_📋_Τιμολόγια.py",        label="📋  Τιμολόγια")

# ── Helpers ───────────────────────────────────────────────
def get_week_range(d):
    s = d - timedelta(days=d.weekday())
    return s, s + timedelta(days=6)

def find_header_and_load(file_content, filename):
    try:
        is_excel = filename.lower().endswith(('.xlsx', '.xls'))
        if is_excel:
            df_raw = pd.read_excel(io.BytesIO(file_content), header=None)
        else:
            try:
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None, sep=None, engine='python')
            except:
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None, encoding='cp1253', sep=None, engine='python')

        hi = -1
        for i in range(min(40, len(df_raw))):
            row_str = " ".join(str(x).upper() for x in df_raw.iloc[i].values if pd.notna(x))
            if "ΤΥΠΟΣ" in row_str and "ΗΜΕΡΟΜΗΝΙΑ" in row_str:
                hi = i; break
        if hi == -1: return None

        df = df_raw.iloc[hi+1:].copy()
        df.columns = [str(h).strip().upper() for h in df_raw.iloc[hi]]
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.str.contains('NAN|UNNAMED', case=False)]
        return df.reset_index(drop=True)
    except:
        return None

@st.cache_data(ttl=600)
def load_invoices():
    all_data = pd.DataFrame()
    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            for msg in mailbox.fetch(AND(from_=SENDER_EMAIL), limit=30, reverse=True):
                for att in msg.attachments:
                    if not att.filename.lower().endswith(('.xlsx','.csv','.xls')): continue
                    df = find_header_and_load(att.payload, att.filename)
                    if df is None: continue

                    col_d = next((c for c in df.columns if 'ΗΜΕΡΟΜΗΝΙΑ' in c), None)
                    col_v = next((c for c in df.columns if 'ΑΞΙΑ' in c or 'ΣΥΝΟΛΟ' in c), None)
                    col_t = next((c for c in df.columns if 'ΤΥΠΟΣ' in c), None)
                    if not (col_d and col_v and col_t): continue

                    tmp = df[[col_d,col_t,col_v]].copy()
                    tmp.columns = ['DATE','TYPE','VALUE']
                    tmp['DATE'] = pd.to_datetime(tmp['DATE'], errors='coerce')
                    if tmp['VALUE'].dtype == object:
                        tmp['VALUE'] = tmp['VALUE'].astype(str).str.replace('€','').str.replace(',','.').str.strip()
                    tmp['VALUE'] = pd.to_numeric(tmp['VALUE'], errors='coerce').fillna(0)
                    all_data = pd.concat([all_data, tmp.dropna(subset=['DATE'])], ignore_index=True)
        # Αποθήκευσε στο session_state για την αρχική σελίδα
        st.session_state['invoice_data'] = all_data
        return all_data
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης: {e}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════
st.markdown("""
<div style="margin-bottom:1.5rem;">
  <div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#3b82f6;margin-bottom:.2rem;">ΑΒ ΣΚΥΡΟΣ · ΚΑΤΑΣΤΗΜΑ 1082</div>
  <h1 style="font-size:1.9rem;font-weight:700;color:#f1f5f9;margin:0;letter-spacing:-.02em;">Έλεγχος Τιμολογίων</h1>
</div>
""", unsafe_allow_html=True)

rc1, rc2 = st.columns([1, 3])
with rc1:
    if st.button("🔄  Φόρτωση / Ανανέωση", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

df = load_invoices()

if df.empty:
    st.markdown("""
    <div style="text-align:center;padding:4rem;color:#334155;">
      <div style="font-size:3rem;">📭</div>
      <div style="margin-top:.5rem;">Δεν βρέθηκαν δεδομένα · Πατήστε «Φόρτωση»</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

st.markdown(f'<div class="ok-banner">✓ Φορτώθηκαν <strong>{len(df):,}</strong> εγγραφές</div>', unsafe_allow_html=True)

tab_w, tab_m, tab_all = st.tabs(["📅  Εβδομαδιαία","📆  Μηνιαία","📊  Συνολική Εικόνα"])

# ── Εβδομαδιαία ──────────────────────────────────────────
with tab_w:
    st.markdown('<div class="sec-header"><span>▍</span> Εβδομαδιαία Εικόνα</div>', unsafe_allow_html=True)
    sel = st.date_input("Επίλεξε ημέρα:", datetime.now(), label_visibility="collapsed")
    ws, we = get_week_range(datetime.combine(sel, datetime.min.time()))
    st.markdown(f'<div style="font-size:.8rem;color:#475569;margin-bottom:1rem;">Εβδομάδα: <strong style="color:#94a3b8;">{ws.strftime("%d/%m/%Y")}</strong> — <strong style="color:#94a3b8;">{we.strftime("%d/%m/%Y")}</strong></div>', unsafe_allow_html=True)

    mask = (df['DATE'] >= ws) & (df['DATE'] <= we)
    w_df = df[mask]

    if not w_df.empty:
        inv = w_df[~w_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
        crd = w_df[ w_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
        net = inv - crd

        st.markdown(f"""<div class="kpi-grid-3">
          <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Τιμολόγια Εβδ.</div><div class="kpi-value">{fmt_euro(inv)}</div></div>
          <div class="kpi-card" style="--accent:#f43f5e"><div class="kpi-label">Πιστωτικά Εβδ.</div><div class="kpi-value">{fmt_euro(crd)}</div></div>
          <div class="kpi-card" style="--accent:#10b981"><div class="kpi-label">Καθαρό Σύνολο</div><div class="kpi-value">{fmt_euro(net)}</div></div>
        </div>""", unsafe_allow_html=True)

        # Ημερήσια ανάλυση
        st.markdown('<div class="sec-header"><span>▍</span> Ανά Ημέρα</div>', unsafe_allow_html=True)
        daily = (w_df.groupby([w_df['DATE'].dt.date, 'TYPE'])['VALUE']
                 .sum().reset_index())
        daily.columns = ['Ημερομηνία','Τύπος','Αξία']
        daily['Ημερομηνία'] = daily['Ημερομηνία'].apply(lambda d: d.strftime('%d/%m/%Y'))
        st.dataframe(daily.style.format({"Αξία": "{:.2f} €"}),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Δεν υπάρχουν εγγραφές για αυτή την εβδομάδα.")

# ── Μηνιαία ──────────────────────────────────────────────
with tab_m:
    st.markdown('<div class="sec-header"><span>▍</span> Μηνιαία Εικόνα</div>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2)
    with mc1:
        s_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1],
                           index=datetime.now().month-1, label_visibility="collapsed")
    with mc2:
        years = sorted(df['DATE'].dt.year.dropna().unique().astype(int), reverse=True)
        s_y   = st.selectbox("Έτος", years, label_visibility="collapsed")

    mask_m = (df['DATE'].dt.month == s_m) & (df['DATE'].dt.year == s_y)
    m_df   = df[mask_m]

    if not m_df.empty:
        inv_m = m_df[~m_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
        crd_m = m_df[ m_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
        net_m = inv_m - crd_m

        st.markdown(f"""<div class="kpi-grid-3">
          <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Τιμολόγια {MONTHS_GR[s_m-1][:3]}.</div><div class="kpi-value">{fmt_euro(inv_m)}</div></div>
          <div class="kpi-card" style="--accent:#f43f5e"><div class="kpi-label">Πιστωτικά {MONTHS_GR[s_m-1][:3]}.</div><div class="kpi-value">{fmt_euro(crd_m)}</div></div>
          <div class="kpi-card" style="--accent:#10b981"><div class="kpi-label">Καθαρό {MONTHS_GR[s_m-1][:3]}.</div><div class="kpi-value">{fmt_euro(net_m)}</div></div>
        </div>""", unsafe_allow_html=True)

        # Εβδομαδιαία ανάλυση μέσα στον μήνα
        st.markdown('<div class="sec-header"><span>▍</span> Ανά Εβδομάδα</div>', unsafe_allow_html=True)
        m_df2 = m_df.copy()
        m_df2['week'] = m_df2['DATE'].dt.isocalendar().week.astype(int)
        weekly = m_df2.groupby('week').agg(
            Τιμολόγια=('VALUE', lambda x: x[~m_df2.loc[x.index,'TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)].sum()),
            Πιστωτικά=('VALUE', lambda x: x[ m_df2.loc[x.index,'TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)].sum()),
        ).reset_index()
        weekly['Καθαρό'] = weekly['Τιμολόγια'] - weekly['Πιστωτικά']
        weekly.columns = ['Εβδομάδα','Τιμολόγια (€)','Πιστωτικά (€)','Καθαρό (€)']
        st.dataframe(weekly, use_container_width=True, hide_index=True)

        st.markdown('<hr class="divider-module"/>', unsafe_allow_html=True)
        csv = m_df.copy()
        csv['DATE'] = csv['DATE'].dt.strftime('%d/%m/%Y')
        csv.columns = ['ΗΜΕΡΟΜΗΝΙΑ','ΤΥΠΟΣ','ΑΞΙΑ']
        st.download_button("↓  Εξαγωγή CSV Μήνα",
                           csv.to_csv(index=False).encode('utf-8-sig'),
                           f"invoices_{s_m}_{s_y}.csv", "text/csv")
    else:
        st.info("Δεν υπάρχουν εγγραφές για αυτόν τον μήνα.")

# ── Συνολική Εικόνα ───────────────────────────────────────
with tab_all:
    st.markdown('<div class="sec-header"><span>▍</span> Συνολικά Στοιχεία</div>', unsafe_allow_html=True)

    total_inv = df[~df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
    total_crd = df[ df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()

    st.markdown(f"""<div class="kpi-grid-3">
      <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Σύνολο Τιμολογίων</div><div class="kpi-value">{fmt_euro(total_inv)}</div></div>
      <div class="kpi-card" style="--accent:#f43f5e"><div class="kpi-label">Σύνολο Πιστωτικών</div><div class="kpi-value">{fmt_euro(total_crd)}</div></div>
      <div class="kpi-card" style="--accent:#10b981"><div class="kpi-label">Καθαρό Σύνολο</div><div class="kpi-value">{fmt_euro(total_inv-total_crd)}</div></div>
    </div>""", unsafe_allow_html=True)

    # Μηνιαίο γράφημα
    st.markdown('<div class="sec-header"><span>▍</span> Μηνιαία Εξέλιξη</div>', unsafe_allow_html=True)
    monthly = df.copy()
    monthly['month'] = monthly['DATE'].dt.to_period('M')
    inv_monthly = (monthly[~monthly['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]
                   .groupby('month')['VALUE'].sum().reset_index())
    inv_monthly.columns = ['Μήνας','Αξία']
    inv_monthly['Μήνας'] = inv_monthly['Μήνας'].astype(str)
    if not inv_monthly.empty:
        st.bar_chart(inv_monthly.set_index('Μήνας')['Αξία'], color="#3b82f6",
                     use_container_width=True, height=220)

    # Πλήρης πίνακας
    st.markdown('<div class="sec-header"><span>▍</span> Λίστα Εγγραφών</div>', unsafe_allow_html=True)
    disp = df.copy()
    disp['DATE'] = disp['DATE'].dt.strftime('%d/%m/%Y')
    disp.columns = ['Ημερομηνία','Τύπος','Αξία (€)']
    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)
