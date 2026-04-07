import streamlit as st
import pandas as pd
import io
import os
import re
import json
import pdfplumber
from imap_tools import MailBox
from datetime import datetime, timedelta, date

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["bkrvmuqxysymqwbf"]

HISTORY_FILE  = "sales_history.csv"   # ημερήσιο ιστορικό
HOURLY_FILE   = "hourly_history.csv"  # ωριαίο ιστορικό

DAYS_GR = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard",
    layout="centered",          
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

# ── Mobile-friendly CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="metric-container"] { padding: 10px 14px !important; border: 1px solid #f0f2f6; border-radius: 10px; }
  [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
  [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
  .stTabs [data-baseweb="tab"] { font-size: 0.85rem; padding: 8px 12px; }
  .stButton > button { width: 100%; border-radius: 8px; height: 3em; background-color: #ff4b4b; color: white; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΔΙΑΧΕΙΡΙΣΗ ΔΕΔΟΜΕΝΩΝ (CSV)
# ─────────────────────────────────────────────────────────────────────────────

def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','netday','grossal','customers','items','avg_basket'])

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_FILE, index=False)

def upsert_daily(record: dict):
    df = load_history()
    mask = df['date'] == record['date']
    if mask.any():
        for k, v in record.items():
            df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df = df.sort_values('date').reset_index(drop=True)
    save_history(df)

def load_hourly() -> pd.DataFrame:
    if os.path.exists(HOURLY_FILE):
        df = pd.read_csv(HOURLY_FILE)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','hour','sales','customers','items'])

def save_hourly(df: pd.DataFrame):
    df.to_csv(HOURLY_FILE, index=False)

def upsert_hourly(record_date: date, hourly_rows: list[dict]):
    df = load_hourly()
    if not df.empty:
        df = df[df['date'] != record_date]          
    new_rows = pd.DataFrame([{**r, 'date': record_date} for r in hourly_rows])
    df = pd.concat([df, new_rows], ignore_index=True)
    df = df.sort_values(['date','hour']).reset_index(drop=True)
    save_hourly(df)

def get_history_value(df: pd.DataFrame, target_date: date, col: str):
    if df.empty: return None
    mask = df['date'] == target_date
    if mask.any():
        val = df.loc[mask, col].values[0]
        return float(val) if pd.notna(val) else None
    return None

# ─────────────────────────────────────────────────────────────────────────────
# PDF & EMAIL LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def parse_number(s: str) -> float:
    s = s.strip().replace('€','').replace(' ','')
    if "," in s and "." in s:
        if s.rfind(',') > s.rfind('.'): s = s.replace('.','').replace(',','.')
        else: s = s.replace(',','')
    elif "," in s: s = s.replace(',','.')
    try: return float(s)
    except: return 0.0

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {'date': None, 'netday': None, 'grossal': None, 'customers': None, 'avg_basket': None, 'hourly': []}
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])

        m = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', full_text)
        if m: result['date'] = datetime.strptime(m.group(1), "%d/%m/%Y").date()

        m = re.search(r'NetDaySalDis\s+([\d,\.]+)', full_text)
        if m: result['netday'] = parse_number(m.group(1))

        m = re.search(r'NumOfCus\s+([\d,\.]+)', full_text)
        if m: result['customers'] = int(parse_number(m.group(1)))

        m = re.search(r'AvgSalCus\s+([\d,\.]+)', full_text)
        if m: result['avg_basket'] = parse_number(m.group(1))

        hourly_pattern = re.findall(r'(\d{2}:\d{2})\s*-\s*\d{2}:\d{2}\s+([\d,\.]+)\s*€\s+([\d\.]+)\s+(\d+)', full_text)
        for match in hourly_pattern:
            h_str, s_str, _, c_str = match
            result['hourly'].append({'hour': int(h_str.split(':')[0]), 'sales': parse_number(s_str), 'customers': int(c_str)})
    except Exception as e: st.error(f"Error PDF: {e}")
    return result

def fetch_latest_report(n_emails: int = 30):
    results = []
    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            # Ελέγχουμε τα τελευταία 150 emails (αγνοούμε το θέμα για να μη χάσουμε κανένα)
            for msg in mailbox.fetch(limit=150, reverse=True):
                if not msg.attachments:
                    continue # Πάμε στο επόμενο αν δεν έχει συνημμένο
                    
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        data = extract_pdf_data(att.payload)
                        
                        # Αν το PDF δεν γράφει ημερομηνία μέσα, παίρνουμε την ημερομηνία του email
                        if data['date'] is None:
                            data['date'] = msg.date.date()
                            
                        # Αν βρήκαμε πωλήσεις (netday), το κρατάμε!
                        if data['netday'] is not None:
                            results.append(data)
                            break # Βρήκαμε δεδομένα, πάμε στο επόμενο email
                
                if len(results) >= n_emails:
                    break
    except Exception as e: st.error(f"Email Error: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# UI & TABS
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 AB ΣΚΥΡΟΣ Dashboard")

with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=True):
    n_fetch = st.selectbox("Πόσες ημέρες να ελέγξω;", [7, 14, 30, 60], index=1)
    if st.button("📥 Λήψη από Email"):
        with st.spinner("Γίνεται σάρωση στα emails..."):
            fetched = fetch_latest_report(n_fetch)
            if fetched:
                for d in fetched:
                    upsert_daily({'date': d['date'], 'netday': d['netday'], 'customers': d['customers'], 'avg_basket': d['avg_basket']})
                    if d['hourly']: upsert_hourly(d['date'], d['hourly'])
                st.success(f"Ενημερώθηκαν {len(fetched)} ημέρες επιτυχώς!")
                st.rerun()
            else:
                st.warning("Σαρώθηκαν τα emails, αλλά δεν βρέθηκαν PDF με δεδομένα πωλήσεων.")

history = load_history()
hourly = load_hourly()

if history.empty:
    st.info("Δεν υπάρχουν δεδομένα. Κάνε λήψη από το Email.")
    st.stop()

tab_day, tab_week, tab_month, tab_hourly = st.tabs(["📍 Σήμερα", "📅 Εβδομάδα", "📆 Μήνας", "🕐 Ώρα"])

with tab_day:
    dates = sorted(history['date'].unique(), reverse=True)
    sel_date = st.selectbox("Ημερομηνία:", dates, format_func=lambda d: d.strftime('%d/%m/%Y'))
    
    r = history[history['date'] == sel_date].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Πωλήσεις", f"{r['netday']:,.2f}€")
    c2.metric("👥 Πελάτες", int(r['customers']) if pd.notna(r['customers']) else 0)
    c3.metric("🛒 Μ.Ο.", f"{r['avg_basket']:,.2f}€" if pd.notna(r['avg_basket']) else "0.00€")

    # Σύγκριση με πέρσι
    last_year_date = date(sel_date.year - 1, sel_date.month, sel_date.day)
    old_val = get_history_value(history, last_year_date, 'netday')
    if old_val:
        diff = r['netday'] - old_val
        pct = (diff/old_val)*100
        st.metric("Vs Πέρσι (ίδια μέρα)", f"{old_val:,.2f}€", delta=f"{pct:+.1f}%")

with tab_week:
    st.write("Στατιστικά τελευταίων 7 ημερών")
    last_7 = history.sort_values('date', ascending=False).head(7)
    st.bar_chart(last_7.set_index('date')['netday'])
    st.dataframe(last_7[['date', 'netday', 'customers']], use_container_width=True, hide_index=True)

with tab_month:
    history['month_year'] = history['date'].apply(lambda x: x.strftime('%m/%Y'))
    m_list = history['month_year'].unique()
    sel_m = st.selectbox("Επίλεξε Μήνα", m_list)
    m_data = history[history['month_year'] == sel_m]
    st.metric(f"Σύνολο {sel_m}", f"{m_data['netday'].sum():,.2f} €")
    st.line_chart(m_data.set_index('date')['netday'])

with tab_hourly:
    if not hourly.empty:
        h_dates = sorted(hourly['date'].unique(), reverse=True)
        sel_h_date = st.selectbox("Ώρες για:", h_dates, key="h_date_sel")
        h_df = hourly[hourly['date'] == sel_h_date]
        if not h_df.empty:
            st.bar_chart(h_df.set_index('hour')['sales'])
            st.dataframe(h_df[['hour', 'sales', 'customers']], use_container_width=True, hide_index=True)

            # Σύγκριση ίδιας μέρας χθες
            prev_h_date = sel_h_date - timedelta(days=1)
            prev_h_df   = hourly[hourly['date'] == prev_h_date]
            if not prev_h_df.empty:
                st.divider()
                st.markdown(f"**Σύγκριση με {prev_h_date.strftime('%d/%m/%Y')}:**")
                merged = h_df[['hour','sales']].merge(
                    prev_h_df[['hour','sales']].rename(columns={'sales':'sales_prev'}),
                    on='hour', how='outer'
                ).fillna(0).sort_values('hour')
                merged['Ώρα']     = merged['hour'].apply(lambda x: f"{x:02d}:00")
                merged['Σήμερα']  = merged['sales'].map(lambda x: f"{x:,.2f} €")
                merged['Χθες']    = merged['sales_prev'].map(lambda x: f"{x:,.2f} €")
                merged['Δ%']      = merged.apply(
                    lambda r: f"{((r['sales']-r['sales_prev'])/r['sales_prev']*100):+.1f}%"
                    if r['sales_prev'] > 0 else "—", axis=1
                )
                st.dataframe(merged[['Ώρα','Σήμερα','Χθες','Δ%']],
                             use_container_width=True, hide_index=True)
    else:
        st.info("Δεν υπάρχουν ωριαία δεδομένα ακόμα.")
