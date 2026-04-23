import streamlit as st
import pandas as pd
import io
import os
import re
from imap_tools import MailBox
from datetime import datetime, date, timedelta
import traceback
import pytesseract
from pdf2image import convert_from_bytes

# Αν τρέχεις τοπικά σε Windows, βγάλε το σχόλιο και βάλε το σωστό path για το Tesseract:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ & ΠΑΡΑΜΕΤΡΟΠΟΙΗΣΗ
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – BI Dashboard",
    layout="centered", # Ιδανικό για Mobile
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

EMAIL_USER   = "ftoulisgm@gmail.com"
try:
    EMAIL_PASS = st.secrets["EMAIL_PASSWORD"]
except:
    EMAIL_PASS = "ΒΑΛΕ_ΕΔΩ_ΤΟ_PASS_ΓΙΑ_ΤΟΠΙΚΗ_ΔΟΚΙΜΗ"

EMAIL_FROM   = "abf.skyros@gmail.com"
HISTORY_FILE = "sales_history.csv"

# CSS για Mobile-Friendly Κάρτες (Metrics)
st.markdown("""
<style>
  [data-testid="metric-container"] {
    background: #ffffff; 
    border-radius: 10px;
    padding: 12px; 
    border: 1px solid #e0e0e0;
    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
  }
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
  }
  .stTabs [data-baseweb="tab"] {
    padding-top: 10px;
    padding-bottom: 10px;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ (OCR & DATA)
# ─────────────────────────────────────────────────────────────────────────────
def fmt_euro(val):
    if pd.isna(val): return "—"
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_num(val, is_float=False):
    if pd.isna(val): return "—"
    if is_float:
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(val)}"

def parse_val(match):
    if match:
        val_str = match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(val_str)
        except ValueError:
            return None
    return None

def extract_data_via_ocr(pdf_bytes):
    try:
        images = convert_from_bytes(pdf_bytes)
        full_text = ""
        for img in images:
            text = pytesseract.image_to_string(img, lang='eng') 
            full_text += text + "\n"
        
        # Εξαγωγή Βασικών Δεικτών (KPIs)
        net_day = parse_val(re.search(r"NetDaySalDis[\s\n]*([\d\.]+(?:,\d+)?)", full_text, re.IGNORECASE))
        num_cus = parse_val(re.search(r"NumOfCus[\s\n]*(\d+)", full_text, re.IGNORECASE))
        upt     = parse_val(re.search(r"AvgitmPerCus[\s\n]*([\d\.]+(?:,\d+)?)", full_text, re.IGNORECASE))
        aur     = parse_val(re.search(r"AvgltmPric[\s\n]*([\d\.]+(?:,\d+)?)", full_text, re.IGNORECASE))
        cancels = parse_val(re.search(r"Cancel[\s\n]*([\d\.]+(?:,\d+)?)", full_text, re.IGNORECASE))
        returns = parse_val(re.search(r"Return[\s\n]*([\d\.]+(?:,\d+)?)", full_text, re.IGNORECASE))

        avg_basket = None
        if net_day is not None and num_cus is not None and num_cus > 0:
            avg_basket = net_day / num_cus

        return net_day, num_cus, avg_basket, upt, aur, cancels, returns

    except Exception as e:
        print(f"Σφάλμα κατά το OCR: {e}")
        return None, None, None, None, None, None, None

def load_history():
    expected_cols = ['date', 'netday', 'customers', 'avg_basket', 'upt', 'aur', 'cancels', 'returns']
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        # Προσθήκη νέων στηλών αν προέρχεται από παλιά έκδοση
        for col in expected_cols:
            if col not in df.columns:
                df[col] = pd.NA
        return df.sort_values('date').reset_index(drop=True)
    return pd.DataFrame(columns=expected_cols)

def save_to_history(date_obj, netday, customers, avg_basket, upt, aur, cancels, returns):
    df = load_history()
    new_data = {
        'date': date_obj, 'netday': netday, 'customers': customers, 
        'avg_basket': avg_basket, 'upt': upt, 'aur': aur, 
        'cancels': cancels, 'returns': returns
    }
    
    if date_obj in df['date'].values:
        idx = df[df['date'] == date_obj].index[0]
        for key, val in new_data.items():
            df.at[idx, key] = val
    else:
        new_row = pd.DataFrame([new_data])
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv(HISTORY_FILE, index=False)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# ΠΛΑΪΝΟ ΜΕΝΟΥ (SIDEBAR) & ΦΙΛΤΡΑ
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Εργαλεία & Φίλτρα")
    
    if st.button("🔄 Λήψη Νέων Δεδομένων", type="primary", use_container_width=True):
        with st.spinner("Ανάλυση PDF (OCR)..."):
            try:
                with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
                    messages = list(mailbox.fetch(f'FROM "{EMAIL_FROM}"', limit=7, reverse=True))
                    found_new = False
                    for msg in messages:
                        msg_date = msg.date.date()
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.pdf'):
                                net, cus, basket, upt, aur, canc, ret = extract_data_via_ocr(att.payload)
                                if net is not None:
                                    save_to_history(msg_date, net, cus, basket, upt, aur, canc, ret)
                                    found_new = True
                                    st.success(f"Ενημερώθηκε: {msg_date.strftime('%d/%m')} ({fmt_euro(net)})")
                    if not found_new:
                        st.info("Δεν βρέθηκαν νέα PDF.")
            except Exception as e:
                st.error(f"Σφάλμα: {e}")
    
    st.divider()
    st.subheader("📅 Χρονικό Διάστημα")
    
    filter_option = st.radio("Επιλογή:", ["Τελευταίες 7 Ημέρες", "Τρέχων Μήνας", "Όλο το Ιστορικό"])
    
# Φόρτωση Δεδομένων
history = load_history()
if history.empty:
    st.warning("Δεν υπάρχουν δεδομένα. Πάτα 'Λήψη Νέων Δεδομένων' από το μενού.")
    st.stop()

# Εφαρμογή Φίλτρων
today = datetime.now().date()
if filter_option == "Τελευταίες 7 Ημέρες":
    filtered_df = history[history['date'] >= (today - timedelta(days=7))]
elif filter_option == "Τρέχων Μήνας":
    filtered_df = history[(history['date'].apply(lambda x: x.month)) == today.month]
else:
    filtered_df = history

if filtered_df.empty:
    st.info("Δεν υπάρχουν δεδομένα για το επιλεγμένο διάστημα.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ΚΕΝΤΡΙΚΗ ΟΘΟΝΗ (MOBILE TABS)
# ─────────────────────────────────────────────────────────────────────────────
st.title("📊 BI Dashboard")
st.caption(f"Εμφάνιση δεδομένων: {filter_option}")

tab1, tab2, tab3, tab4 = st.tabs(["📌 Σύνοψη", "📈 Τάσεις", "🏆 Ρεκόρ", "💾 Δεδομένα"])

# -- TAB 1: ΣΥΝΟΨΗ -------------------------------------------------------------
with tab1:
    last_record = history.iloc[-1]
    prev_record = history.iloc[-2] if len(history) > 1 else None
    
    st.subheader(f"Σημερινή Εικόνα ({last_record['date'].strftime('%d/%m')})")
    
    # Υπολογισμός διαφοράς
    def get_delta(current, previous):
        if pd.isna(current) or pd.isna(previous) or previous == 0: return None
        return f"{((current - previous) / previous * 100):+.1f}%"

    col1, col2 = st.columns(2)
    with col1:
        delta_net = get_delta(last_record['netday'], prev_record['netday']) if prev_record is not None else None
        st.metric("💰 Τζίρος (NetDay)", fmt_euro(last_record['netday']), delta_net)
        
        delta_upt = get_delta(last_record['upt'], prev_record['upt']) if prev_record is not None else None
        st.metric("🛒 Τεμάχια/Πελάτη (UPT)", fmt_num(last_record['upt'], True), delta_upt)

    with col2:
        delta_cus = get_delta(last_record['customers'], prev_record['customers']) if prev_record is not None else None
        st.metric("👥 Πελάτες", fmt_num(last_record['customers']), delta_cus)
        
        delta_aur = get_delta(last_record['aur'], prev_record['aur']) if prev_record is not None else None
        st.metric("🏷️ Μέση Τιμή Είδους (AUR)", fmt_euro(last_record['aur']), delta_aur)
        
    st.divider()
    st.subheader("⚠️ Δείκτης Εξαιρέσεων (Ταμεία)")
    col3, col4 = st.columns(2)
    col3.metric("❌ Ακυρώσεις", fmt_euro(last_record['cancels']))
    col4.metric("🔄 Επιστροφές", fmt_euro(last_record['returns']))

# -- TAB 2: ΤΑΣΕΙΣ -------------------------------------------------------------
with tab2:
    st.subheader("Τζίρος ανά Ημέρα")
    chart_data = filtered_df.copy()
    chart_data['label'] = chart_data['date'].apply(lambda d: d.strftime('%d/%m'))
    st.bar_chart(chart_data.set_index('label')['netday'])
    
    st.subheader("Κίνηση Πελατών")
    st.line_chart(chart_data.set_index('label')['customers'])

# -- TAB 3: ΡΕΚΟΡ --------------------------------------------------------------
with tab3:
    st.subheader("Ηγέτες Διοίκησης (Best Performers)")
    
    best_sales_day = filtered_df.loc[filtered_df['netday'].idxmax()]
    best_cus_day   = filtered_df.loc[filtered_df['customers'].idxmax()]
    
    with st.expander("👑 Καλύτερη Ημέρα Τζίρου", expanded=True):
        st.markdown(f"**Ημερομηνία:** {best_sales_day['date'].strftime('%d/%m/%Y')}")
        st.markdown(f"**Τζίρος:** {fmt_euro(best_sales_day['netday'])}")
        st.markdown(f"**Πελάτες:** {fmt_num(best_sales_day['customers'])}")
        
    with st.expander("🏃‍♂️ Περισσότεροι Πελάτες"):
        st.markdown(f"**Ημερομηνία:** {best_cus_day['date'].strftime('%d/%m/%Y')}")
        st.markdown(f"**Πελάτες:** {fmt_num(best_cus_day['customers'])}")
        st.markdown(f"**Τζίρος:** {fmt_euro(best_cus_day['netday'])}")

# -- TAB 4: ΔΕΔΟΜΕΝΑ -----------------------------------------------------------
with tab4:
    st.subheader("Αναλυτική Λίστα")
    # Μορφοποίηση του dataframe για καλύτερη απεικόνιση στο κινητό (χωρίς export)
    display_df = filtered_df.copy()
    display_df['Ημερομηνία'] = display_df['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
    display_df['Τζίρος'] = display_df['netday'].apply(lambda x: fmt_euro(x))
    display_df['Πελάτες'] = display_df['customers'].apply(lambda x: fmt_num(x))
    display_df['Μ.Ο. Καλάθι'] = display_df['avg_basket'].apply(lambda x: fmt_euro(x))
    
    # Εμφάνιση μόνο των βασικών στηλών για να χωράει στις οθόνες
    st.dataframe(
        display_df[['Ημερομηνία', 'Τζίρος', 'Πελάτες', 'Μ.Ο. Καλάθι']], 
        use_container_width=True,
        hide_index=True
    )
