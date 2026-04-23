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

# Ρυθμίσεις εμφάνισης για κινητό
st.set_page_config(page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard", layout="centered", page_icon="🛒")

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
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────

def fmt_euro(val):
    if pd.isna(val) or val is None: return "0,00 €"
    return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_greek_num(text):
    if not text: return 0.0
    # Καθαρισμός: κρατάμε μόνο ψηφία, κόμματα και τελείες
    clean = re.sub(r'[^\d,\.]', '', text)
    if not clean: return 0.0
    # Αν έχει και τελεία και κόμμα (π.χ. 9.102,82)
    if '.' in clean and ',' in clean:
        clean = clean.replace('.', '').replace(',', '.')
    # Αν έχει μόνο κόμμα (π.χ. 102,82)
    elif ',' in clean:
        clean = clean.replace(',', '.')
    try:
        return float(clean)
    except:
        return 0.0

def extract_all_data(pdf_bytes):
    """Εξαγωγή βασικών στοιχείων και λίστας τμημάτων με OCR"""
    try:
        images = convert_from_bytes(pdf_bytes)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img, lang='eng+ell')

        # 1. Βασικά Στοιχεία (Regex βελτιωμένο)
        net_day = parse_greek_num(re.search(r"NetDaySalDis[\s\n]*([\d\.,]+)", text, re.I).group(1)) if re.search(r"NetDaySalDis[\s\n]*([\d\.,]+)", text, re.I) else 0.0
        num_cus = parse_greek_num(re.search(r"NumOfCus[\s\n]*([\d\.,]+)", text, re.I).group(1)) if re.search(r"NumOfCus[\s\n]*([\d\.,]+)", text, re.I) else 0.0
        upt = parse_greek_num(re.search(r"AvgitmPerCus[\s\n]*([\d\.,]+)", text, re.I).group(1)) if re.search(r"AvgitmPerCus[\s\n]*([\d\.,]+)", text, re.I) else 0.0
        aur = parse_greek_num(re.search(r"AvgItmPric[\s\n]*([\d\.,]+)", text, re.I).group(1)) if re.search(r"AvgItmPric[\s\n]*([\d\.,]+)", text, re.I) else 0.0

        # 2. Τμήματα (Ψάχνουμε γραμμές που ξεκινούν με 3 ψηφία)
        # Παράδειγμα: 001 ΟΠΩΡΟΠΩΛΕΙΟ 1.126,85 ...
        dept_list = []
        dept_lines = re.findall(r"(\d{3})\s+([Α-Ω\s\-]+)\s+([\d\.,]+)\s+([\d\.,]+)", text)
        for d_code, d_name, d_gross, d_net in dept_lines:
            val = parse_greek_num(d_net)
            if val > 0:
                dept_list.append({"name": d_name.strip(), "sales": val})
        
        # Ταξινόμηση τμημάτων ανά τζίρο
        dept_list = sorted(dept_list, key=lambda x: x['sales'], reverse=True)
        # Μετατροπή σε string για αποθήκευση στο CSV
        dept_json = json.dumps(dept_list, ensure_ascii=False)

        return net_day, int(num_cus), upt, aur, dept_json
    except Exception as e:
        st.error(f"OCR Error: {e}")
        return 0.0, 0, 0.0, 0.0, "[]"

def load_data():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df.sort_values('date', ascending=False)
    return pd.DataFrame(columns=['date', 'netday', 'customers', 'upt', 'aur', 'depts'])

# ─────────────────────────────────────────────────────────────────────────────
# UI - SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Ρυθμίσεις")
    if st.button("🔄 Συγχρονισμός Email", use_container_width=True):
        with st.spinner("Διαβάζω τα PDF..."):
            try:
                with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
                    for msg in mailbox.fetch(f'FROM "{EMAIL_FROM}"', limit=5, reverse=True):
                        d = msg.date.date()
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.pdf'):
                                net, cus, upt, aur, depts = extract_all_data(att.payload)
                                # Αποθήκευση
                                df = load_data()
                                if d in df['date'].values:
                                    df.loc[df['date'] == d, ['netday','customers','upt','aur','depts']] = [net, cus, upt, aur, depts]
                                else:
                                    new_row = pd.DataFrame([{'date': d, 'netday': net, 'customers': cus, 'upt': upt, 'aur': aur, 'depts': depts}])
                                    df = pd.concat([df, new_row])
                                df.to_csv(HISTORY_FILE, index=False)
                st.success("Η βάση ενημερώθηκε!")
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# ΚΥΡΙΩΣ ΟΘΟΝΗ
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.info("Δεν υπάρχουν δεδομένα. Κάνε συγχρονισμό από το μενού αριστερά.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📍 Σήμερα", "🏆 Ρεκόρ", "📑 Ιστορικό"])

# --- TAB 1: ΣΗΜΕΡΑ ---
with tab1:
    latest = df.iloc[0]
    st.subheader(f"Αναφορά {latest['date'].strftime('%d/%m/%Y')}")
    
    c1, c2 = st.columns(2)
    c1.metric("💰 Πωλήσεις", fmt_euro(latest['netday']))
    c2.metric("👥 Πελάτες", f"{int(latest['customers'])}")
    
    c3, c4 = st.columns(2)
    c3.metric("🛒 UPT (Τεμ/Πελ)", f"{latest['upt']:.2f}")
    c4.metric("🏷️ AUR (Μέση Τιμή)", fmt_euro(latest['aur']))

    st.divider()
    st.markdown("### 🔝 Τμήματα με τις περισσότερες πωλήσεις")
    try:
        depts = json.loads(latest['depts'])
        for i, d in enumerate(depts[:5]): # Δείξε τα top 5
            st.write(f"**{i+1}. {d['name']}**: {fmt_euro(d['sales'])}")
    except:
        st.write("Δεν βρέθηκαν δεδομένα τμημάτων.")

# --- TAB 2: ΡΕΚΟΡ ---
with tab2:
    st.subheader("Ανάλυση Ρεκόρ")
    period = st.segmented_control("Επίπεδο Αναφοράς:", ["Εβδομάδα", "Μήνας", "Έτος"], default="Εβδομάδα")
    
    # Φιλτράρισμα βάσει περιόδου
    today = date.today()
    if period == "Εβδομάδα":
        start_date = today - timedelta(days=7)
    elif period == "Μήνας":
        start_date = today - timedelta(days=30)
    else:
        start_date = date(today.year, 1, 1)
    
    mask = df[df['date'] >= start_date]
    
    if not mask.empty:
        best_sales = mask.loc[mask['netday'].idxmax()]
        best_cus = mask.loc[mask['customers'].idxmax()]
        
        st.info(f"Ρεκόρ περιόδου (Από {start_date.strftime('%d/%m')})")
        
        with st.expander("🥇 Κορυφαίες Πωλήσεις Ημέρας", expanded=True):
            st.write(f"**{fmt_euro(best_sales['netday'])}** στις {best_sales['date'].strftime('%d/%m/%Y')}")
            
        with st.expander("🥈 Μεγαλύτερη Προσέλευση Πελατών"):
            st.write(f"**{int(best_cus['customers'])} πελάτες** στις {best_cus['date'].strftime('%d/%m/%Y')}")

        # Εύρεση του "Top Τμήματος" όλης της περιόδου
        all_depts = {}
        for row in mask['depts']:
            try:
                d_list = json.loads(row)
                for d in d_list:
                    all_depts[d['name']] = all_depts.get(d['name'], 0) + d['sales']
            except: continue
        
        if all_depts:
            top_dept = max(all_depts, key=all_depts.get)
            with st.expander("📦 Κορυφαίο Τμήμα Περιόδου"):
                st.write(f"**{top_dept}** με συνολικές πωλήσεις **{fmt_euro(all_depts[top_dept])}**")
    else:
        st.write("Δεν υπάρχουν αρκετά δεδομένα για αυτή την περίοδο.")

# --- TAB 3: ΙΣΤΟΡΙΚΟ ---
with tab3:
    st.subheader("Όλες οι εγγραφές")
    # Μόνο οι βασικές στήλες για το κινητό
    st.dataframe(
        df[['date', 'netday', 'customers']],
        column_config={
            "date": "Ημ/νία",
            "netday": "Πωλήσεις",
            "customers": "Πελ."
        },
        hide_index=True,
        use_container_width=True
    )
