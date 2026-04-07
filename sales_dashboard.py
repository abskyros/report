import streamlit as st
import pandas as pd
import io
import os
import re
import pdfplumber
from imap_tools import MailBox, AND
from datetime import datetime, timedelta, date

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"

HISTORY_FILE  = "sales_history.csv"
HOURLY_FILE   = "hourly_history.csv"

DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard",
    layout="centered",
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="metric-container"] {
    background: #f8f9fa; border-radius: 12px;
    padding: 12px 16px !important; border: 1px solid #e9ecef;
  }
  [data-testid="stMetricValue"]  { font-size: 1.45rem !important; font-weight: 700; }
  [data-testid="stMetricLabel"]  { font-size: 0.78rem !important; color: #6c757d; }
  div[data-testid="stButton"] > button { border-radius: 10px; height: 2.8em; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΙΣΤΟΡΙΚΟ (DATA PERSISTENCE)
# ─────────────────────────────────────────────────────────────────────────────

def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','netday','customers','avg_basket'])

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_FILE, index=False)

def upsert_daily(record: dict):
    df = load_history()
    mask = df['date'] == record['date']
    if mask.any():
        for k, v in record.items():
            if v is not None:
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
    return pd.DataFrame(columns=['date','hour','sales','customers'])

def save_hourly(df: pd.DataFrame):
    df.to_csv(HOURLY_FILE, index=False)

def upsert_hourly(record_date: date, hourly_rows: list):
    df = load_hourly()
    if not df.empty:
        df = df[df['date'] != record_date]
    if hourly_rows:
        new_rows = pd.DataFrame([{**r, 'date': record_date} for r in hourly_rows])
        df = pd.concat([df, new_rows], ignore_index=True)
        df = df.sort_values(['date','hour']).reset_index(drop=True)
    save_hourly(df)

def get_val(df: pd.DataFrame, target: date, col: str):
    if df.empty: return None
    mask = df['date'] == target
    if not mask.any(): return None
    v = df.loc[mask, col].values[0]
    return float(v) if pd.notna(v) else None

def fmt_euro(v):
    if v is None: return "—"
    return f"{v:,.2f} €"

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_number(s: str) -> float:
    # Καθαρισμός για μορφή 8.795,38 ή 8,795.38
    s = s.strip().replace('€','').replace(' ','').replace('\xa0','')
    if "," in s and "." in s:
        if s.rfind(',') > s.rfind('.'): s = s.replace('.','').replace(',','.')
        else: s = s.replace(',','')
    elif "," in s:
        s = s.replace(',','.')
    try: return float(s)
    except: return 0.0

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {'date': None, 'netday': None, 'customers': None, 'avg_basket': None, 'hourly': []}
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        # 1. Ημερομηνία (π.χ. For 07/04/2026)
        m_date = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', full_text)
        if m_date:
            result['date'] = datetime.strptime(m_date.group(1), "%d/%m/%Y").date()

        # 2. Πωλήσεις (NetDaySalDis)
        m_net = re.search(r'NetDaySalDis\s+([\d\.,]+)', full_text)
        if m_net:
            result['netday'] = parse_number(m_net.group(1))

        # 3. Πελάτες (NumOfCus)
        m_cus = re.search(r'NumOfCus\s+([\d\.,]+)', full_text)
        if m_cus:
            result['customers'] = int(parse_number(m_cus.group(1)))

        # 4. Μέσο Καλάθι (AvgSalCus)
        m_avg = re.search(r'AvgSalCus\s+([\d\.,]+)', full_text)
        if m_avg:
            result['avg_basket'] = parse_number(m_avg.group(1))

        # 5. Ωριαία (π.χ. 08:00 - 09:00   120,50 €   25)
        # Προσαρμογή regex για να πιάνει τη δομή του report
        hourly_pattern = r'(\d{2}):\d{2}\s*-\s*\d{2}:\d{2}\s+([\d\.,]+)\s*€?\s+[\d\.,]+\s+(\d+)'
        for h_str, s_str, c_str in re.findall(hourly_pattern, full_text):
            s_val = parse_number(s_str)
            if s_val > 0:
                result['hourly'].append({
                    'hour': int(h_str), 
                    'sales': s_val, 
                    'customers': int(parse_number(c_str))
                })

    except Exception as e:
        st.warning(f"Σφάλμα ανάγνωσης PDF: {e}")
    return result

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL (Η ΟΡΙΣΤΙΚΗ ΛΥΣΗ ΓΙΑ ΤΟ ΣΦΑΛΜΑ UID)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_reports(limit: int) -> list:
    results = []
    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            # ΑΝΤΙ ΓΙΑ ΑΝΑΖΗΤΗΣΗ ΜΕ SUBJECT (ΠΟΥ ΒΓΑΖΕΙ ΣΦΑΛΜΑ),
            # ΠΑΙΡΝΟΥΜΕ ΤΑ ΤΕΛΕΥΤΑΙΑ EMAILS ΚΑΙ ΦΙΛΤΡΑΡΟΥΜΕ ΣΤΗΝ PYTHON.
            # Το limit καθορίζει πόσα πρόσφατα emails θα ελέγξουμε συνολικά.
            for msg in mailbox.fetch(limit=limit, reverse=True):
                if EMAIL_SUBJECT.upper() in msg.subject.upper():
                    for att in msg.attachments:
                        if att.filename.lower().endswith('.pdf'):
                            data = extract_pdf_data(att.payload)
                            # Αν το PDF δεν είχε ημερομηνία, πάρε του email
                            if data['date'] is None: data['date'] = msg.date.date()
                            
                            if data['netday'] is not None:
                                results.append(data)
                                break # Βρήκαμε το σωστό attachment, πάμε στο επόμενο email
    except Exception as e:
        st.error(f"Email σφάλμα: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# UI & DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Dashboard")

# ΕΝΗΜΕΡΩΣΗ
with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=False):
    c1, c2 = st.columns([3,1])
    with c1:
        n_to_check = st.number_input("Έλεγχος τελευταίων X emails:", min_value=10, max_value=500, value=50)
    with c2:
        st.write(""); st.write("")
        if st.button("📥 Λήψη", use_container_width=True):
            fetch_reports.clear()
            with st.spinner("Γίνεται έλεγχος emails..."):
                fetched = fetch_reports(n_to_check)
            if fetched:
                for d in fetched:
                    upsert_daily({'date': d['date'], 'netday': d['netday'],
                                  'customers': d['customers'], 'avg_basket': d['avg_basket']})
                    if d['hourly']: upsert_hourly(d['date'], d['hourly'])
                st.success(f"✅ Ενημερώθηκαν {len(fetched)} ημέρες!")
                st.rerun()
            else:
                st.warning("Δεν βρέθηκαν σχετικά emails στις πρόσφατες αναζητήσεις.")

# ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ
history = load_history()
if history.empty:
    st.info("📭 Το ιστορικό είναι κενό. Πατήστε 'Λήψη' για να τραβήξετε δεδομένα από το email.")
    st.stop()

# ΠΡΟΒΟΛΗ ΤΕΛΕΥΤΑΙΑΣ ΗΜΕΡΑΣ
last_r = history.iloc[-1]
st.subheader(f"📍 Στατιστικά: {last_r['date'].strftime('%d/%m/%Y')}")
c1, c2, c3 = st.columns(3)
c1.metric("Πωλήσεις", fmt_euro(last_r['netday']))
c2.metric("Πελάτες", f"{int(last_r['customers'])}")
c3.metric("Μ.Ό. Καλαθιού", fmt_euro(last_r['avg_basket']))

# TAB ΠΡΟΒΟΛΗΣ
t1, t2 = st.tabs(["📊 Ιστορικό Πωλήσεων", "🕐 Ωριαία Ανάλυση"])

with t1:
    chart_df = history.copy().tail(30) # Τελευταίες 30 μέρες
    chart_df['date_str'] = chart_df['date'].apply(lambda d: d.strftime('%d/%m'))
    st.bar_chart(chart_df.set_index('date_str')['netday'])
    st.dataframe(history.sort_values('date', ascending=False), use_container_width=True, hide_index=True)

with t2:
    hourly_data = load_hourly()
    if not hourly_data.empty:
        sel_date = st.selectbox("Επίλεξε ημερομηνία για ωριαία:", sorted(hourly_data['date'].unique(), reverse=True))
        day_hourly = hourly_data[hourly_data['date'] == sel_date]
        day_hourly['Ώρα'] = day_hourly['hour'].apply(lambda x: f"{x:02d}:00")
        st.line_chart(day_hourly.set_index('Ώρα')['sales'])
        st.dataframe(day_hourly[['Ώρα', 'sales', 'customers']].rename(columns={'sales':'Πωλήσεις €', 'customers':'Πελάτες'}), use_container_width=True, hide_index=True)
    else:
        st.write("Δεν υπάρχουν ωριαία δεδομένα ακόμα.")
