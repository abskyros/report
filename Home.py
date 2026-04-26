import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="AB Σκύρος 1082",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CONFIG & LOAD ─────────────────────────────────────────────────────────────
HISTORY_FILE = "sales_cache.csv"
INV_CACHE = "invoices_cache.csv"

def fmt_euro(v):
    """Μορφοποίηση σε Ευρώ με ελληνικό format (π.χ. 1.234,56 €)"""
    if pd.isna(v) or v is None: return "0,00 €"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

def load_data(file):
    if os.path.exists(file):
        df = pd.read_csv(file)
        if not df.empty:
            # Μετατροπή ημερομηνιών σε date objects
            date_col = "date" if "date" in df.columns else "DATE"
            df[date_col] = pd.to_datetime(df[date_col]).dt.date
        return df
    return pd.DataFrame()

# CSS - Sleek Slate Dark Mode
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; background: #0f172a !important; color: #f8fafc !important; }
.stApp { background: #0f172a !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 3rem 1.5rem 4rem !important; max-width: 900px !important; margin: 0 auto !important; }

.top-header { background: #1e293b; border-left: 5px solid #10b981; border-radius: 14px; padding: 1.5rem 2rem; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2); }
.header-title { font-size: 0.8rem; font-weight: 700; color: #10b981; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.3rem; }
.header-main { font-size: 1.6rem; font-weight: 800; color: #f8fafc; }
.header-date-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.header-date { font-size: 1rem; font-weight: 600; color: #e2e8f0; }

.cards-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2.5rem; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 2.5rem 1.5rem; text-align: center; transition: transform 0.2s, border-color 0.2s; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2); }
.card:hover { transform: translateY(-4px); border-color: #475569; }
.card-title { font-size: 0.9rem; font-weight: 600; color: #94a3b8; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-val { font-size: 2.4rem; font-weight: 800; color: #f8fafc; margin-bottom: 0.8rem; letter-spacing: -0.02em; }
.stat-label { font-size: 0.8rem; color: #10b981; font-weight: 600; background: rgba(16, 185, 129, 0.1); padding: 0.4rem 0.8rem; border-radius: 20px; display: inline-block; }
.stat-label-blue { color: #3b82f6; background: rgba(59, 130, 246, 0.1); }

.btn-green button { background: #10b981 !important; color: #0f172a !important; border: none !important; padding: 1.2rem !important; font-size: 1rem !important; font-weight: 700 !important; border-radius: 12px !important; transition: all 0.2s !important; }
.btn-green button:hover { background: #059669 !important; transform: scale(1.02); }
.btn-blue button { background: #3b82f6 !important; color: #ffffff !important; border: none !important; padding: 1.2rem !important; font-size: 1rem !important; font-weight: 700 !important; border-radius: 12px !important; transition: all 0.2s !important; }
.btn-blue button:hover { background: #2563eb !important; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# Υπολογισμοί Ημερομηνιών
today = date.today()
start_of_week = today - timedelta(days=today.weekday()) # Βρίσκει πάντα την τρέχουσα Δευτέρα

# Load Data
df_s = load_data(HISTORY_FILE)
df_i = load_data(INV_CACHE)

# Header
st.markdown(f"""
<div class="top-header">
    <div>
        <div class="header-title">AB Σκύρος 1082</div>
        <div class="header-main">Business Hub</div>
    </div>
    <div style="text-align: right;">
        <div class="header-date-label">Σήμερα</div>
        <div class="header-date">{today.strftime('%d/%m/%Y')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Υπολογισμός Εβδομαδιαίου Πωλήσεων (Δευ - Κυρ)
sales_week = 0.0
if not df_s.empty:
    week_mask = (df_s['date'] >= start_of_week) & (df_s['date'] <= today)
    sales_week = df_s[week_mask]['netday'].sum()

# Υπολογισμός Εβδομαδιαίου Τιμολογίων (Δευ - Κυρ)
inv_week = 0.0
if not df_i.empty:
    week_mask = (df_i['DATE'] >= start_of_week) & (df_i['DATE'] <= today)
    inv_val = df_i[week_mask & ~df_i['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
    crd_val = df_i[week_mask & df_i['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
    inv_week = inv_val - crd_val

# UI Cards
st.markdown(f"""
<div class="cards-wrap">
    <div class="card">
        <div class="card-title">📊 Πωλήσεις Καταστήματος</div>
        <div class="stat-val">{fmt_euro(sales_week)}</div>
        <div class="stat-label">Καθαρό Εβδομάδας (Δευ-Κυρ)</div>
    </div>
    <div class="card">
        <div class="card-title">📄 Έλεγχος Τιμολογίων</div>
        <div class="stat-val">{fmt_euro(inv_week)}</div>
        <div class="stat-label stat-label-blue">Καθαρό Εβδομάδας (Δευ-Κυρ)</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Buttons
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="btn-green">', unsafe_allow_html=True)
    if st.button("📊 Αναλυτικές Πωλήσεις →", use_container_width=True):
        st.switch_page("pages/1_Sales.py")
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
    if st.button("📄 Διαχείριση Τιμολογίων →", use_container_width=True):
        st.switch_page("pages/2_Invoices.py")
    st.markdown('</div>', unsafe_allow_html=True)
