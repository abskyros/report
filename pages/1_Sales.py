import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import io
import logging

logging.basicConfig(level=logging.WARNING)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sales Analytics — AB Skyros",
    layout="wide",
    initial_sidebar_state="collapsed",
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

def save_history(df):
    df.to_csv(HISTORY_FILE, index=False)

def ocr_extract_sales(image_bytes):
    """Εξαγωγή δεδομένων από εικόνα με OCR"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang='ell')
        
        # Εξαγωγή τζίρου
        import re
        patterns = [
            r'NET\s*?[:\-]?\s*?([\d.,]+)',
            r'ΚΑΘΑΡΟ\s*?[:\-]?\s*?([\d.,]+)',
            r'ΤΕΛΙΚΟ\s*?[:\-]?\s*?([\d.,]+)',
        ]
        
        netday = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace('.', '').replace(',', '.')
                netday = float(val)
                break
        
        return netday, text
    except Exception as e:
        st.error(f"OCR Error: {e}")
        return None, str(e)

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#f0f2f5;}
.block-container{padding:1rem 1rem 3rem!important;max-width:100%!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden;}

.ph{background:#0f172a;border-radius:10px;padding:1rem;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;}
.ph-h1{font-size:1.3rem;font-weight:700;color:#f8fafc;margin:0;}
.ph-lbl{font-size:.55rem;color:#475569;}
.ph-val{font-family:monospace;font-size:.65rem;color:#64748b;}

.sh{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;padding-bottom:.45rem;margin:1.6rem 0 .8rem;}

.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:.9rem 1rem;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#2563eb);}
.kl{font-size:.6rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:.35rem;}
.kv{font-family:monospace;font-size:1rem;font-weight:500;color:#0f172a;}

.bn{border-radius:7px;padding:.6rem .9rem;font-size:.75rem;font-weight:500;margin:.6rem 0;}
.bn-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;}
.bn-warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;}
.bn-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;}

.stButton>button{background:#2563eb!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.45rem 1rem!important;}
.stButton>button:hover{background:#1d4ed8!important;}

.data-table{border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;margin:1rem 0;}

@media(max-width:640px){
  .ph{padding:.8rem;flex-direction:column;align-items:flex-start;}
  .ph-h1{font-size:1.1rem;}
  .kv{font-size:.9rem;}
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ──────────────────────────────────────────────────────────────
if "sales_data" not in st.session_state:
    st.session_state.sales_data = load_history()

# ─── HEADER ────────────────────────────────────────────────────────────────────
today = date.today()
st.markdown(f"""
<div class="ph">
  <div>
    <div class="ph-h1">📊 Sales Analytics</div>
  </div>
  <div style="text-align:right;">
    <div class="ph-lbl">Σημερα</div>
    <div class="ph-val">{DAYS_GR[today.weekday()]}, {today.day}/{today.month}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Ιστορικο", "📧 Διαβασμα Email", "📸 Manual Entry"])

# ─── TAB 1: HISTORY ────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="sh">Ιστορικο Πωλησεων</div>', unsafe_allow_html=True)
    
    df = st.session_state.sales_data
    if not df.empty:
        st.markdown(f"**Συνολο εγγραφων:** {len(df)}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Chart
        ch = df.head(14).sort_values("date").copy()
        ch["D"] = ch["date"].apply(lambda d: d.strftime("%d/%m"))
        st.bar_chart(ch.set_index("D")["netday"], color="#2563eb", height=200)
    else:
        st.markdown('<div class="bn bn-info">Δεν υπάρχουν δεδομένα ακόμα</div>', unsafe_allow_html=True)

# ─── TAB 2: EMAIL READING ──────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="sh">Διαβασμα Email — Πρώτα 20 Records</div>', unsafe_allow_html=True)
    
    with st.form("email_form"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("📧 Email", placeholder="your@gmail.com")
        with col2:
            password = st.text_input("🔐 Password", type="password")
        
        submit = st.form_submit_button("📥 Διαβάστε Emails", use_container_width=True)
    
    if submit:
        if not email or not password:
            st.error("Εισάγετε email και κωδικό")
        else:
            with st.spinner("Σύνδεση..."):
                try:
                    mb = MailBox('imap.gmail.com')
                    mb.login(email, password)
                    messages = list(mb.fetch(limit=20, reverse=True))
                    
                    st.success(f"✓ Εβρέθησαν {len(messages)} emails")
                    
                    for idx, msg in enumerate(messages, 1):
                        with st.expander(f"#{idx} {msg.subject[:60]}...", expanded=False):
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.write(f"**From:** {msg.from_}")
                                st.write(f"**Date:** {msg.date.strftime('%d/%m/%Y %H:%M')}")
                            with col2:
                                st.write(f"**Size:** {len(msg.subject)} chars")
                            
                            st.write("---")
                            
                            # Check for attachments
                            if msg.attachments:
                                st.write(f"📎 **Attachments:** {len(msg.attachments)}")
                                for att in msg.attachments:
                                    st.write(f"  - {att.filename}")
                    
                    mb.logout()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# ─── TAB 3: MANUAL ENTRY ──────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="sh">Χειροκινητη Εισαγωγη Δεδομενων</div>', unsafe_allow_html=True)
    
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("📅 Ημερομηνια", value=today)
        with col2:
            netday = st.number_input("💰 Καθαρο Τζιρο (€)", min_value=0.0, step=0.01)
        
        col3, col4 = st.columns(2)
        with col3:
            customers = st.number_input("👥 Αριθμος Πελατων", min_value=0, step=1)
        with col4:
            avg_basket = st.number_input("🛒 ΜΟ Καλαθιου (€)", min_value=0.0, step=0.01)
        
        depts = st.text_input("🏪 Τμηματα", placeholder="Π.χ: ΠΟΤΑ,ΦΑΓΗΤΟ,ΑΛΛΑ")
        
        if st.form_submit_button("✓ Προσθηκη", use_container_width=True):
            new_row = pd.DataFrame({
                "date": [entry_date],
                "netday": [netday],
                "customers": [customers],
                "avg_basket": [avg_basket],
                "depts": [depts]
            })
            
            df = st.session_state.sales_data
            df = pd.concat([new_row, df], ignore_index=True)
            save_history(df)
            st.session_state.sales_data = df
            
            st.success(f"✓ Δεδομένα προστέθηκαν για {entry_date.strftime('%d/%m/%Y')}")
            st.rerun()
