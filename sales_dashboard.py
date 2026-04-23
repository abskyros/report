import streamlit as st
import pandas as pd
import io
import os
import re
import json
from imap_tools import MailBox
from datetime import datetime, date, timedelta
import pytesseract
from pdf2image import convert_from_bytes

# Ρυθμίσεις εμφάνισης - Mobile First
st.set_page_config(page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard", layout="centered", page_icon="🛒")

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ ΛΟΓΑΡΙΑΣΜΟΥ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER = "ftoulisgm@gmail.com"
try:
    EMAIL_PASS = st.secrets["EMAIL_PASSWORD"]
except:
    EMAIL_PASS = "YOUR_PASSWORD_HERE" # Για τοπική χρήση

EMAIL_FROM = "abf.skyros@gmail.com"
HISTORY_FILE = "sales_history.csv"

# ─────────────────────────────────────────────────────────────────────────────
# Η ΜΗΧΑΝΗ ΤΟΥ OCR (ΒΕΛΤΙΩΜΕΝΗ)
# ─────────────────────────────────────────────────────────────────────────────

def fmt_euro(val):
    if pd.isna(val) or val is None: return "0,00 €"
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_and_parse_num(text):
    if not text: return 0.0
    # Αφαιρούμε τα πάντα εκτός από ψηφία, κόμμα και τελεία
    clean = re.sub(r'[^\d,\.]', '', text)
    if not clean: return 0.0
    # Αν έχουμε μορφή 9.102,82
    if '.' in clean and ',' in clean:
        clean = clean.replace('.', '').replace(',', '.')
    # Αν έχουμε μόνο κόμμα 102,82
    elif ',' in clean:
        clean = clean.replace(',', '.')
    try:
        return float(clean)
    except:
        return 0.0

def extract_all_data(pdf_bytes):
    """Ενισχυμένη ανάγνωση για σκαναρισμένα PDF"""
    try:
        images = convert_from_bytes(pdf_bytes)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img, lang='eng+ell')

        # Πιο "έξυπνη" αναζήτηση που αγνοεί αλλαγές γραμμών ανάμεσα στη λέξη και το νούμερο
        def get_value(key, full_text):
            # Ψάχνει το key και παίρνει το επόμενο group ψηφίων/συμβόλων
            pattern = rf"{key}[\s\n]*[:\-]*[\s\n]*([\d\.,]+)"
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            return clean_and_parse_num(match.group(1)) if match else 0.0

        net_day = get_value("NetDaySalDis", text)
        num_cus = get_value("NumOfCus", text)
        upt     = get_value("AvgitmPerCus", text)
        aur     = get_value("AvgItmPric", text)

        # Ανάλυση Τμημάτων
        dept_list = []
        # Pattern: 3 ψηφία κωδικός + Ονομασία (Κεφαλαία Ελληνικά) + Ποσό
        dept_pattern = r"(\d{3})\s+([Α-Ω\s\-\.\/]+)\s+([\d\.,]+)"
        matches = re.findall(dept_pattern, text)
        
        for d_code, d_name, d_net in matches:
            val = clean_and_parse_num(d_net)
            if val > 1.0: # Αγνοούμε τα πολύ μικρά ποσά/λάθη
                dept_list.append({"name": d_name.strip(), "sales": val})
        
        dept_list = sorted(dept_list, key=lambda x: x['sales'], reverse=True)
        return net_day, int(num_cus), upt, aur, json.dumps(dept_list, ensure_ascii=False)
    except Exception:
        return 0.0, 0, 0.0, 0.0, "[]"

def load_data():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        # Διασφάλιση μοναδικότητας ανά ημερομηνία
        return df.sort_values('date', ascending=False).drop_duplicates(subset=['date'])
    return pd.DataFrame(columns=['date', 'netday', 'customers', 'upt', 'aur', 'depts'])

# ─────────────────────────────────────────────────────────────────────────────
# ΚΕΝΤΡΙΚΟ UI (ΧΩΡΙΣ SIDEBAR)
# ─────────────────────────────────────────────────────────────────────────────
st.title("🛒 ΑΒ ΣΚΥΡΟΣ Dashboard")

# Ενότητα Συγχρονισμού (Κορυφή)
col_sync, col_filter = st.columns([1, 1])

with col_sync:
    if st.button("🔄 Συγχρονισμός (Τελευταία 20)", use_container_width=True, type="primary"):
        with st.spinner("Γίνεται ανάγνωση..."):
            try:
                with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
                    df = load_data()
                    found = 0
                    for msg in mailbox.fetch(f'FROM "{EMAIL_FROM}"', limit=20, reverse=True):
                        d = msg.date.date()
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.pdf'):
                                net, cus, upt, aur, depts = extract_all_data(att.payload)
                                if net > 0:
                                    new_row = {'date': d, 'netday': net, 'customers': cus, 'upt': upt, 'aur': aur, 'depts': depts}
                                    if d in df['date'].values:
                                        idx = df[df['date'] == d].index[0]
                                        for k, v in new_row.items(): df.at[idx, k] = v
                                    else:
                                        df = pd.concat([df, pd.DataFrame([new_row])])
                                    found += 1
                    df.to_csv(HISTORY_FILE, index=False)
                st.toast(f"Βρέθηκαν {found} αναφορές!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα: {e}")

with col_filter:
    period = st.selectbox("Διάστημα:", ["Τελευταίες 7 Ημέρες", "Τρέχων Μήνας", "Όλο το Έτος"], label_visibility="collapsed")

# Φόρτωση Δεδομένων
df = load_data()

if df.empty:
    st.info("Δεν υπάρχουν δεδομένα. Πατήστε 'Συγχρονισμός' για να ξεκινήσουμε.")
    st.stop()

# Εφαρμογή Φίλτρου Περιόδου
today = date.today()
if "7 Ημέρες" in period:
    mask = df[df['date'] >= (today - timedelta(days=7))]
elif "Μήνας" in period:
    mask = df[df['date'].apply(lambda x: x.month == today.month and x.year == today.year)]
else:
    mask = df[df['date'].apply(lambda x: x.year == today.year)]

# TABS
tab1, tab2, tab3 = st.tabs(["📍 Σήμερα", "🏆 Ρεκόρ", "📑 Ιστορικό"])

# --- TAB 1: ΣΗΜΕΡΑ ---
with tab1:
    latest = df.iloc[0]
    st.subheader(f"Αναφορά {latest['date'].strftime('%d/%m/%Y')}")
    
    m1, m2 = st.columns(2)
    m1.metric("💰 Πωλήσεις", fmt_euro(latest['netday']))
    m2.metric("👥 Πελάτες", f"{int(latest['customers'])}")
    
    m3, m4 = st.columns(2)
    m3.metric("🛒 UPT", f"{latest['upt']:.2f}")
    m4.metric("🏷️ AUR", fmt_euro(latest['aur']))

    st.divider()
    st.subheader("🔝 Καλύτερα Τμήματα")
    try:
        depts = json.loads(latest['depts'])
        if not depts: 
            st.write("Δεν βρέθηκαν τμήματα σε αυτή την αναφορά.")
        else:
            for i, d in enumerate(depts[:8]):
                st.write(f"**{i+1}. {d['name']}**: {fmt_euro(d['sales'])}")
    except:
        st.write("Σφάλμα στην ανάγνωση των τμημάτων.")

# --- TAB 2: ΡΕΚΟΡ ---
with tab2:
    if not mask.empty:
        best_sales = mask.loc[mask['netday'].idxmax()]
        best_cus   = mask.loc[mask['customers'].idxmax()]
        
        st.info(f"Κορυφαίες επιδόσεις: {period}")
        
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**🏆 Πωλήσεις**")
            st.markdown(f"### {fmt_euro(best_sales['netday'])}")
            st.caption(f"Στις {best_sales['date'].strftime('%d/%m')}")
        with r2:
            st.markdown("**👥 Πελάτες**")
            st.markdown(f"### {int(best_cus['customers'])}")
            st.caption(f"Στις {best_cus['date'].strftime('%d/%m')}")
    else:
        st.write("Δεν υπάρχουν δεδομένα για αυτή την περίοδο.")

# --- TAB 3: ΙΣΤΟΡΙΚΟ ---
with tab3:
    st.subheader("Ιστορικό")
    st.dataframe(
        df[['date', 'netday', 'customers']],
        column_config={"date": "Ημ/νία", "netday": "Τζίρος", "customers": "Πελ."},
        hide_index=True,
        use_container_width=True
    )
