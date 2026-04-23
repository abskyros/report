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

# Ρυθμίσεις εμφάνισης
st.set_page_config(page_title="ΑΒ ΣΚΥΡΟΣ – BI Dashboard", layout="centered", page_icon="🛒")

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ ΛΟΓΑΡΙΑΣΜΟΥ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER = "ftoulisgm@gmail.com"
try:
    EMAIL_PASS = st.secrets["EMAIL_PASSWORD"]
except:
    EMAIL_PASS = "YOUR_PASSWORD_HERE"

EMAIL_FROM = "abf.skyros@gmail.com"
HISTORY_FILE = "sales_history.csv"

# ─────────────────────────────────────────────────────────────────────────────
# ΕΝΙΣΧΥΜΕΝΕΣ ΣΥΝΑΡΤΗΣΕΙΣ OCR & PARSING
# ─────────────────────────────────────────────────────────────────────────────

def fmt_euro(val):
    if pd.isna(val) or val is None: return "0,00 €"
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_greek_num(text):
    if not text: return 0.0
    # Καθαρισμός από οτιδήποτε δεν είναι ψηφίο, κόμμα ή τελεία
    clean = re.sub(r'[^\d,\.]', '', text)
    if not clean: return 0.0
    # Διαχείριση μορφής 9.102,82
    if '.' in clean and ',' in clean:
        clean = clean.replace('.', '').replace(',', '.')
    elif ',' in clean:
        clean = clean.replace(',', '.')
    try:
        return float(clean)
    except:
        return 0.0

def extract_all_data(pdf_bytes):
    """Εξαιρετικά ανθεκτικό OCR για σκαναρισμένα PDF"""
    try:
        images = convert_from_bytes(pdf_bytes)
        text = ""
        for img in images:
            # Χρήση και των δύο γλωσσών για καλύτερη αναγνώριση
            text += pytesseract.image_to_string(img, lang='eng+ell')

        # Βελτιωμένο Regex: Ψάχνει τη λέξη-κλειδί και παίρνει το πρώτο νούμερο που ακολουθεί (ακόμα και σε άλλη γραμμή)
        def find_metric(keyword, full_text):
            pattern = rf"{keyword}.*?([\d\.,]+)"
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            return parse_greek_num(match.group(1)) if match else 0.0

        net_day = find_metric("NetDaySalDis", text)
        num_cus = find_metric("NumOfCus", text)
        upt     = find_metric("AvgitmPerCus", text)
        aur     = find_metric("AvgItmPric", text)

        # Ανάλυση Τμημάτων (πιο ευέλικτη αναγνώριση γραμμών)
        dept_list = []
        # Pattern: 3 ψηφία (κωδικός) + Κείμενο (όνομα) + Αριθμός (τζίρος)
        dept_pattern = r"(\d{3})\s+([Α-Ω\s\-\.\/]+)\s+([\d\.,]+)"
        matches = re.findall(dept_pattern, text)
        
        for d_code, d_name, d_net in matches:
            val = parse_greek_num(d_net)
            if val > 5.0: # Αγνοούμε τμήματα με μηδαμινό τζίρο
                dept_list.append({"name": d_name.strip(), "sales": val})
        
        dept_list = sorted(dept_list, key=lambda x: x['sales'], reverse=True)
        return net_day, int(num_cus), upt, aur, json.dumps(dept_list, ensure_ascii=False)
    except Exception as e:
        return 0.0, 0, 0.0, 0.0, "[]"

def load_data():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df.sort_values('date', ascending=False).drop_duplicates(subset=['date'])
    return pd.DataFrame(columns=['date', 'netday', 'customers', 'upt', 'aur', 'depts'])

# ─────────────────────────────────────────────────────────────────────────────
# UI - SIDEBAR & SYNC
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Διαχείριση")
    # Αυξήσαμε το limit=100 για να πιάνει περασμένους μήνες
    if st.button("🔄 Συγχρονισμός Ιστορικού (100+ email)", use_container_width=True):
        with st.spinner("Γίνεται βαθιά αναζήτηση στα email..."):
            try:
                with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
                    df = load_data()
                    found_count = 0
                    # Ψάχνουμε τα τελευταία 100 email από τον συγκεκριμένο αποστολέα
                    for msg in mailbox.fetch(f'FROM "{EMAIL_FROM}"', limit=100, reverse=True):
                        d = msg.date.date()
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.pdf'):
                                net, cus, upt, aur, depts = extract_all_data(att.payload)
                                if net > 0:
                                    # Ενημέρωση ή Προσθήκη
                                    new_row = {'date': d, 'netday': net, 'customers': cus, 'upt': upt, 'aur': aur, 'depts': depts}
                                    if d in df['date'].values:
                                        idx = df[df['date'] == d].index[0]
                                        for k, v in new_row.items(): df.at[idx, k] = v
                                    else:
                                        df = pd.concat([df, pd.DataFrame([new_row])])
                                    found_count += 1
                    df.to_csv(HISTORY_FILE, index=False)
                st.success(f"Επιτυχία! Βρέθηκαν {found_count} αναφορές.")
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα σύνδεσης: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# ΚΥΡΙΩΣ ΕΦΑΡΜΟΓΗ
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.info("Η βάση είναι άδεια. Πατήστε 'Συγχρονισμός Ιστορικού' στο μενού αριστερά.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📍 Σήμερα", "🏆 Ρεκόρ", "📑 Ιστορικό"])

# --- TAB 1: ΣΗΜΕΡΑ ---
with tab1:
    latest = df.iloc[0]
    st.subheader(f"Αναφορά {latest['date'].strftime('%d/%m/%Y')}")
    
    col1, col2 = st.columns(2)
    col1.metric("💰 Πωλήσεις", fmt_euro(latest['netday']))
    col2.metric("👥 Πελάτες", f"{int(latest['customers'])}")
    
    col3, col4 = st.columns(2)
    col3.metric("🛒 UPT", f"{latest['upt']:.2f}")
    col4.metric("🏷️ AUR", fmt_euro(latest['aur']))

    st.divider()
    st.markdown("### 🔝 Απόδοση Τμημάτων")
    try:
        depts = json.loads(latest['depts'])
        if not depts: st.write("Δεν αναγνωρίστηκαν τμήματα.")
        for i, d in enumerate(depts[:8]): # Εμφάνιση των 8 πρώτων
            st.write(f"**{i+1}. {d['name']}**: {fmt_euro(d['sales'])}")
    except:
        st.write("Σφάλμα στην ανάγνωση τμημάτων.")

# --- TAB 2: ΡΕΚΟΡ ---
with tab2:
    st.subheader("Αναζήτηση Ρεκόρ")
    period = st.radio("Διάστημα:", ["Τελευταίες 7 Ημέρες", "Τρέχων Μήνας", "Όλο το Έτος"], horizontal=True)
    
    today = date.today()
    if period == "Τελευταίες 7 Ημέρες":
        mask = df[df['date'] >= (today - timedelta(days=7))]
    elif period == "Τρέχων Μήνας":
        mask = df[df['date'].apply(lambda x: x.month == today.month and x.year == today.year)]
    else:
        mask = df[df['date'].apply(lambda x: x.year == today.year)]
    
    if not mask.empty:
        best_sales = mask.loc[mask['netday'].idxmax()]
        best_cus   = mask.loc[mask['customers'].idxmax()]
        
        st.success(f"Κορυφαίες επιδόσεις ({period})")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🏆 Πωλήσεις**")
            st.markdown(f"### {fmt_euro(best_sales['netday'])}")
            st.caption(f"Στις {best_sales['date'].strftime('%d/%m')}")
        with c2:
            st.markdown("**👥 Πελάτες**")
            st.markdown(f"### {int(best_cus['customers'])}")
            st.caption(f"Στις {best_cus['date'].strftime('%d/%m')}")
            
        # Συνολικό Top Τμήμα περιόδου
        dept_totals = {}
        for row in mask['depts']:
            try:
                for d in json.loads(row):
                    dept_totals[d['name']] = dept_totals.get(d['name'], 0) + d['sales']
            except: continue
        
        if dept_totals:
            top_d = max(dept_totals, key=dept_totals.get)
            st.divider()
            st.markdown(f"📦 **Κορυφαίο Τμήμα Περιόδου:** {top_d} ({fmt_euro(dept_totals[top_d])})")
    else:
        st.write("Δεν βρέθηκαν δεδομένα για αυτή την περίοδο.")

# --- TAB 3: ΙΣΤΟΡΙΚΟ ---
with tab3:
    st.subheader("Ιστορικό Αναφορών")
    st.dataframe(
        df[['date', 'netday', 'customers']],
        column_config={
            "date": "Ημερομηνία",
            "netday": "Τζίρος",
            "customers": "Πελ."
        },
        hide_index=True,
        use_container_width=True
    )
