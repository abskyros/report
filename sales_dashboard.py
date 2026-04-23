import streamlit as st
import pandas as pd
import io
import os
import re
from imap_tools import MailBox
from datetime import datetime, date
import traceback
import pytesseract
from pdf2image import convert_from_bytes

# Αν τρέχεις τοπικά σε Windows και το pytesseract δεν βρίσκει το exe, βγάλε το σχόλιο και βάλε το σωστό path:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER   = "ftoulisgm@gmail.com"
# Χρήση secrets του Streamlit για ασφάλεια. Τοπικά το βάζεις στο .streamlit/secrets.toml
try:
    EMAIL_PASS = st.secrets["EMAIL_PASSWORD"]
except:
    EMAIL_PASS = "ΒΑΛΕ_ΕΔΩ_ΤΟ_PASS_ΓΙΑ_ΤΟΠΙΚΗ_ΔΟΚΙΜΗ" # Προσωρινό fallback για testing

EMAIL_FROM   = "abf.skyros@gmail.com"

HISTORY_FILE = "sales_history.csv"

DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard",
    layout="centered",
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="metric-container"] {
    background: #f8f9fa; border-radius: 12px;
    padding: 15px; border: 1px solid #e9ecef;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────

def fmt_euro(val):
    if pd.isna(val): return "—"
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def extract_data_via_ocr(pdf_bytes):
    """
    Μετατρέπει το PDF σε εικόνες και κάνει OCR (Αγγλικά & Ελληνικά) για να βρει τις τιμές.
    """
    try:
        # Μετατροπή των bytes του PDF σε λίστα από εικόνες (Pillow Images)
        images = convert_from_bytes(pdf_bytes)
        
        full_text = ""
        for img in images:
            # Κάνουμε OCR. Το 'eng+ell' διαβάζει και αγγλικά και ελληνικά.
            # Αν δεν έχεις εγκαταστήσει τα ελληνικά στο Tesseract, βάλε απλά 'eng'
            text = pytesseract.image_to_string(img, lang='eng') 
            full_text += text + "\n"
        
        # Εκτύπωση στο console για debugging (τι είδε το Tesseract)
        print("--- ΑΠΟΤΕΛΕΣΜΑ OCR ---")
        print(full_text[:500]) # Τυπώνει τους πρώτους 500 χαρακτήρες
        print("----------------------")

        # Ψάχνουμε το NetDaySalDis (π.χ. NetDaySalDis 7.488,29)
        # Η Regex αγνοεί τυχόν σκουπίδια/κενά ανάμεσα στη λέξη και το νούμερο
        net_day_match = re.search(r"NetDaySalDis[^\d]*([\d\.]+(?:,\d+)?)", full_text, re.IGNORECASE)
        # Ψάχνουμε το NumOfCus (π.χ. NumOfCus 288)
        num_cus_match = re.search(r"NumOfCus[^\d]*(\d+)", full_text, re.IGNORECASE)

        net_day = None
        num_cus = None

        if net_day_match:
            # Μετατροπή 7.488,29 σε float 7488.29
            val_str = net_day_match.group(1).replace('.', '').replace(',', '.')
            try:
                net_day = float(val_str)
            except ValueError:
                pass

        if num_cus_match:
            try:
                num_cus = int(num_cus_match.group(1))
            except ValueError:
                pass
                
        # Υπολογισμός Μέσου Όρου Καλαθιού (αν έχουμε και τα δύο)
        avg_basket = None
        if net_day is not None and num_cus is not None and num_cus > 0:
            avg_basket = net_day / num_cus

        return net_day, num_cus, avg_basket

    except Exception as e:
        print(f"Σφάλμα κατά το OCR: {e}")
        return None, None, None

def load_history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df.sort_values('date').reset_index(drop=True)
    return pd.DataFrame(columns=['date', 'netday', 'customers', 'avg_basket'])

def save_to_history(date_obj, netday, customers, avg_basket):
    df = load_history()
    # Αν υπάρχει ήδη η ημερομηνία, την κάνουμε update, αλλιώς την προσθέτουμε
    if date_obj in df['date'].values:
        idx = df[df['date'] == date_obj].index[0]
        df.at[idx, 'netday'] = netday
        df.at[idx, 'customers'] = customers
        df.at[idx, 'avg_basket'] = avg_basket
    else:
        new_row = pd.DataFrame([{
            'date': date_obj, 
            'netday': netday, 
            'customers': customers, 
            'avg_basket': avg_basket
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv(HISTORY_FILE, index=False)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# ΚΥΡΙΩΣ ΕΦΑΡΜΟΓΗ
# ─────────────────────────────────────────────────────────────────────────────
st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Dashboard")

# Κουμπί για συγχρονισμό με το Email
if st.button("🔄 Συγχρονισμός από Email (OCR)", use_container_width=True):
    with st.spinner("Γίνεται σύνδεση στο Gmail και ανάλυση PDF (OCR)... Μπορεί να διαρκέσει λίγο."):
        try:
            with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
                # Ψάχνουμε τα email από τον συγκεκριμένο αποστολέα
                messages = list(mailbox.fetch(f'FROM "{EMAIL_FROM}"', limit=5, reverse=True))
                
                found_new = False
                for msg in messages:
                    msg_date = msg.date.date()
                    for att in msg.attachments:
                        if att.filename.lower().endswith('.pdf'):
                            pdf_bytes = att.payload
                            netday, customers, avg_basket = extract_data_via_ocr(pdf_bytes)
                            
                            if netday is not None:
                                save_to_history(msg_date, netday, customers, avg_basket)
                                found_new = True
                                st.success(f"Επιτυχής ανάγνωση για {msg_date}: {fmt_euro(netday)} | {customers} Πελάτες")
                            else:
                                st.warning(f"Δεν βρέθηκαν δεδομένα στο PDF της {msg_date}. Δες το console για το αποτέλεσμα του OCR.")
                
                if not found_new:
                    st.info("Δεν βρέθηκαν νέα PDF με αναγνωρίσιμα δεδομένα.")
                    
        except Exception as e:
            st.error(f"Σφάλμα σύνδεσης/ανάγνωσης: {e}")
            st.code(traceback.format_exc())

st.divider()

# Φόρτωση και εμφάνιση δεδομένων
history = load_history()

if history.empty:
    st.info("Δεν υπάρχουν δεδομένα. Κάνε συγχρονισμό.")
else:
    # Πάρε την τελευταία εγγραφή
    last = history.iloc[-1]
    last_date = last['date']
    
    st.subheader(f"Ημερήσια Εικόνα ({last_date.strftime('%d/%m/%Y')})")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Πωλήσεις", fmt_euro(last['netday']))
    c2.metric("Πελάτες", f"{int(last['customers'])}" if pd.notna(last['customers']) else "—")
    c3.metric("Μ.Ό. Καλαθιού", fmt_euro(last['avg_basket']))

    if len(history) >= 2:
        prev = history.iloc[-2]
        if pd.notna(prev['netday']) and pd.notna(last['netday']):
            diff = last['netday'] - prev['netday']
            pct  = diff / prev['netday'] * 100
            sign, color = ("▲", "green") if diff >= 0 else ("▼", "red")
            st.markdown(
                f"<span style='color:{color}'>{sign} {fmt_euro(abs(diff))} "
                f"({pct:+.1f}%) σε σχέση με {prev['date'].strftime('%d/%m')}</span>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("📊 Τελευταίες 30 ημέρες – Πωλήσεις")
    chart = history.tail(30).copy()
    chart['label'] = pd.to_datetime(chart['date']).dt.strftime('%d/%m')
    st.bar_chart(chart.set_index('label')['netday'])
