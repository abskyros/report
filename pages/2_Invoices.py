import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
import logging

logging.basicConfig(level=logging.WARNING)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Invoices — AB Skyros",
    layout="wide",
    initial_sidebar_state="collapsed",
)

INVOICES_FILE = "invoices_data.csv"
MONTHS_GR = ["Ιανουαριος","Φεβρουαριος","Μαρτιος","Απριλιος","Μαιος","Ιουνιος",
              "Ιουλιος","Αυγουστος","Σεπτεμβριος","Οκτωβριος","Νοεμβριος","Δεκεμβριος"]
DAYS_GR   = ["Δευτερα","Τριτη","Τεταρτη","Πεμπτη","Παρασκευη","Σαββατο","Κυριακη"]

def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

def load_invoices():
    if os.path.exists(INVOICES_FILE):
        df = pd.read_csv(INVOICES_FILE)
        if not df.empty:
            df["DATE"] = pd.to_datetime(df["DATE"])
        return df
    return pd.DataFrame(columns=["DATE","TYPE","VALUE","NOTES"])

def save_invoices(df):
    df.to_csv(INVOICES_FILE, index=False)

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

.sh{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;padding-bottom:.45rem;margin:1.6rem 0 .8rem;}

.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:.9rem 1rem;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#2563eb);}
.kl{font-size:.6rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:.35rem;}
.kv{font-family:monospace;font-size:1rem;font-weight:500;color:#0f172a;}

.kr{display:grid;gap:.85rem;margin:.9rem 0;}
.kr4{grid-template-columns:repeat(4,1fr);}
@media(max-width:1024px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:640px){.kr4{grid-template-columns:1fr;}}

.bn{border-radius:7px;padding:.6rem .9rem;font-size:.75rem;font-weight:500;margin:.6rem 0;}
.bn-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;}
.bn-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;}

.stButton>button{background:#2563eb!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.45rem 1rem!important;}
.stButton>button:hover{background:#1d4ed8!important;}

@media(max-width:640px){
  .ph{padding:.8rem;flex-direction:column;}
  .ph-h1{font-size:1.1rem;}
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ──────────────────────────────────────────────────────────────
if "invoices_data" not in st.session_state:
    st.session_state.invoices_data = load_invoices()

# Store to Home.py
st.session_state.invoice_data = st.session_state.invoices_data

# ─── HEADER ────────────────────────────────────────────────────────────────────
today = date.today()
st.markdown(f"""
<div class="ph">
  <div>
    <div class="ph-h1">📄 Invoices & Credits</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Summary", "📋 All Records", "➕ New Entry"])

# ─── TAB 1: SUMMARY ────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="sh">Weekly & Monthly Summary</div>', unsafe_allow_html=True)
    
    df = st.session_state.invoices_data
    
    if not df.empty:
        # Weekly stats
        ws = today - timedelta(days=today.weekday())
        w_mask = (df["DATE"].dt.date >= ws) & (df["DATE"].dt.date <= today)
        
        w_inv = df[w_mask & ~df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        w_crd = df[w_mask &  df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        w_net = w_inv - w_crd
        
        # Monthly stats
        m_mask = (df["DATE"].dt.month == today.month) & (df["DATE"].dt.year == today.year)
        m_inv = df[m_mask & ~df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        m_crd = df[m_mask &  df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        m_net = m_inv - m_crd
        
        st.markdown(f"""<div class="kr kr4">
          <div class="kc" style="--a:#0891b2"><div class="kl">Τιμολογια Εβδ.</div><div class="kv">{fmt_euro(w_inv)}</div></div>
          <div class="kc" style="--a:#dc2626"><div class="kl">Πιστωτικα Εβδ.</div><div class="kv">{fmt_euro(w_crd)}</div></div>
          <div class="kc" style="--a:#059669"><div class="kl">Καθαρο Εβδ.</div><div class="kv">{fmt_euro(w_net)}</div></div>
          <div class="kc" style="--a:#f59e0b"><div class="kl">Εβδ. Εγγραφες</div><div class="kv">{len(df[w_mask])}</div></div>
        </div>""", unsafe_allow_html=True)
        
        st.markdown('<div class="sh">Monthly</div>', unsafe_allow_html=True)
        
        st.markdown(f"""<div class="kr kr4">
          <div class="kc" style="--a:#0891b2"><div class="kl">Τιμολογια Μηνα</div><div class="kv">{fmt_euro(m_inv)}</div></div>
          <div class="kc" style="--a:#dc2626"><div class="kl">Πιστωτικα Μηνα</div><div class="kv">{fmt_euro(m_crd)}</div></div>
          <div class="kc" style="--a:#059669"><div class="kl">Καθαρο Μηνα</div><div class="kv">{fmt_euro(m_net)}</div></div>
          <div class="kc" style="--a:#f59e0b"><div class="kl">Μηνιαιες Εγγραφες</div><div class="kv">{len(df[m_mask])}</div></div>
        </div>""", unsafe_allow_html=True)
        
        # Daily chart
        st.markdown('<div class="sh">Daily Trend</div>', unsafe_allow_html=True)
        daily = df[df["DATE"].dt.month == today.month].groupby(df["DATE"].dt.date)["VALUE"].sum().sort_index().tail(15)
        st.line_chart(daily, height=200)
    else:
        st.markdown('<div class="bn bn-info">Δεν υπάρχουν δεδομένα</div>', unsafe_allow_html=True)

# ─── TAB 2: ALL RECORDS ────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="sh">All Invoices & Credits</div>', unsafe_allow_html=True)
    
    df = st.session_state.invoices_data
    if not df.empty:
        # Sort by date descending
        df_display = df.sort_values("DATE", ascending=False).copy()
        df_display["DATE_STR"] = df_display["DATE"].dt.strftime("%d/%m/%Y %H:%M")
        
        # Display with columns
        cols_display = ["DATE_STR", "TYPE", "VALUE", "NOTES"]
        df_display = df_display[cols_display].rename(columns={"DATE_STR": "Date"})
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Export button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"invoices_{today.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.markdown('<div class="bn bn-info">Δεν υπάρχουν δεδομένα</div>', unsafe_allow_html=True)

# ─── TAB 3: NEW ENTRY ──────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="sh">Add New Invoice or Credit Note</div>', unsafe_allow_html=True)
    
    with st.form("invoice_form"):
        col1, col2 = st.columns(2)
        with col1:
            inv_date = st.date_input("📅 Date", value=today)
        with col2:
            inv_type = st.selectbox("📄 Type", ["Τιμολογιο", "Πιστωτικο"])
        
        col3, col4 = st.columns(2)
        with col3:
            inv_value = st.number_input("💰 Value (€)", min_value=0.0, step=0.01)
        with col4:
            inv_notes = st.text_input("📝 Notes", placeholder="Optional")
        
        if st.form_submit_button("✓ Add Entry", use_container_width=True):
            new_invoice = pd.DataFrame({
                "DATE": [pd.to_datetime(inv_date)],
                "TYPE": [f"ΠΙΣΤΩΤΙΚΟ" if "Πιστ" in inv_type else "Τιμολογιο"],
                "VALUE": [inv_value],
                "NOTES": [inv_notes]
            })
            
            df = st.session_state.invoices_data
            df = pd.concat([new_invoice, df], ignore_index=True)
            save_invoices(df)
            st.session_state.invoices_data = df
            st.session_state.invoice_data = df
            
            st.success(f"✓ Entry added for {inv_date.strftime('%d/%m/%Y')}")
            st.rerun()
