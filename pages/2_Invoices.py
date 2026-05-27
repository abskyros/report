import streamlit as st
import pandas as pd
import io
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND

st.set_page_config(page_title="Τιμολόγια — AB Σκύρος", page_icon="📄", layout="wide", initial_sidebar_state="collapsed")

from gsheets_helper import load_invoices, merge_invoices

# ── CONFIG ────────────────────────────────────────────────────────────────────
INV_EMAIL_USER   = "abf.skyros@gmail.com"
INV_EMAIL_SENDER = "Notifications@WeDoConnect.com"
DEEP_SCAN_YEARS  = 2

# ── SECRETS ───────────────────────────────────────────────────────────────────
_SECRET_PW = ""
try:
    _SECRET_PW = st.secrets.get("EMAIL_PASS", "")
except:
    pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#e8f4fb!important;color:#0f172a!important;}
.stApp{background:#e8f4fb!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1.5rem 4rem!important;max-width:960px!important;margin:0 auto!important;}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:2px solid #bae6fd;}
.ptitle{font-size:1.25rem;font-weight:800;color:#003d6b;}
.sh{font-size:.58rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#0369a1;margin:1.8rem 0 .7rem;border-bottom:1px solid #e0f2fe;padding-bottom:.4rem;}
.kr{display:grid;gap:.75rem;margin:.5rem 0 1.2rem;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:900px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr4,.kr3{grid-template-columns:1fr;}.block-container{padding:1rem 1rem 3rem!important;}}
.kc{background:#fff;border:1px solid #e0f2fe;border-radius:12px;padding:.9rem 1rem;position:relative;overflow:hidden;box-shadow:0 2px 8px rgba(0,61,107,0.06);}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#003d6b);}
.kl{font-size:.58rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748b;margin-bottom:.3rem;}
.kv{font-size:1.1rem;font-weight:800;color:#0f172a;}
.kv-green{color:#0369a1;}
.kv-red{color:#dc2626;}
.stButton>button{border-radius:9px!important;font-family:'Inter',sans-serif!important;font-size:.82rem!important;font-weight:700!important;padding:.6rem 1rem!important;transition:all .15s!important;}
.btn-b>button{background:#003d6b!important;border:none!important;color:#fff!important;}
.btn-b>button:hover{background:#004f8a!important;}
.btn-back>button{background:#fff!important;border:1px solid #bae6fd!important;color:#003d6b!important;font-weight:700!important;}
.btn-back>button:hover{background:#e0f2fe!important;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #bae6fd!important;gap:.2rem!important;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#64748b!important;font-size:.74rem!important;font-weight:700!important;letter-spacing:.05em!important;text-transform:uppercase!important;padding:.5rem .9rem!important;border-radius:8px 8px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#003d6b!important;background:#e0f2fe!important;border-bottom:2px solid #003d6b!important;}
[data-testid="stDataFrame"]{border:1px solid #bae6fd;border-radius:10px;overflow:hidden;}
.info-box{background:#e0f2fe;border:1px solid #bae6fd;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#0369a1;margin:.6rem 0;}
.warn-box{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#92400e;margin:.6rem 0;}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    if v == int(v):
        return f"{int(v):,}€".replace(",",".")
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def find_header_and_load(file_content, filename):
    try:
        is_excel = filename.lower().endswith(('.xlsx', '.xls'))
        if is_excel:
            df_raw = pd.read_excel(io.BytesIO(file_content), header=None)
        else:
            try:
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None, sep=None, engine='python')
            except:
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None, encoding='cp1253', sep=None, engine='python')

        header_row_index = -1
        for i in range(min(40, len(df_raw))):
            row_values = [str(x).upper() for x in df_raw.iloc[i].values if pd.notna(x)]
            row_str = " ".join(row_values)
            if "ΤΥΠΟΣ" in row_str and "ΗΜΕΡΟΜΗΝΙΑ" in row_str:
                header_row_index = i; break

        if header_row_index == -1: return None

        df = df_raw.iloc[header_row_index + 1:].copy()
        headers = [str(h).strip().upper() for h in df_raw.iloc[header_row_index]]
        df.columns = headers
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.str.contains('NAN|UNNAMED', case=False)]
        return df.reset_index(drop=True)
    except:
        return None

def fetch_invoices_incremental(password, full_scan=False):
    df_existing = load_invoices()
    cutoff_dt   = None

    if not full_scan and not df_existing.empty:
        last_dt   = df_existing["DATE"].max()
        cutoff_dt = last_dt - timedelta(days=5)

    new_rows       = []
    errors         = []
    emails_checked = 0

    try:
        with MailBox("imap.gmail.com").login(INV_EMAIL_USER, password) as mb:
            criteria = AND(from_=INV_EMAIL_SENDER)
            messages = list(mb.fetch(criteria, limit=500 if full_scan else 50, reverse=True))

            for msg in messages:
                msg_date = msg.date
                if not full_scan and cutoff_dt and msg_date and msg_date < cutoff_dt:
                    continue
                if full_scan:
                    cutoff_full = datetime.now() - timedelta(days=365*DEEP_SCAN_YEARS)
                    if msg_date and msg_date < cutoff_full:
                        continue

                for att in msg.attachments:
                    if not att.filename: continue
                    fname = att.filename.lower()
                    if not (fname.endswith('.xlsx') or fname.endswith('.xls') or fname.endswith('.csv')):
                        continue
                    emails_checked += 1
                    df_parsed = find_header_and_load(att.payload, att.filename)
                    if df_parsed is None: continue

                    col_map = {}
                    for c in df_parsed.columns:
                        cu = c.upper()
                        if "ΤΥΠΟΣ" in cu: col_map[c] = "TYPE"
                        elif "ΗΜΕΡΟΜΗΝΙΑ" in cu: col_map[c] = "DATE"
                        elif "ΑΞΙΑ" in cu or "VALUE" in cu or "ΠΟΣΟ" in cu: col_map[c] = "VALUE"
                    df_parsed = df_parsed.rename(columns=col_map)

                    if not all(c in df_parsed.columns for c in ["DATE","TYPE","VALUE"]):
                        continue

                    df_parsed = df_parsed[["DATE","TYPE","VALUE"]].copy()
                    df_parsed["DATE"]  = pd.to_datetime(df_parsed["DATE"], errors="coerce", dayfirst=True)
                    df_parsed["VALUE"] = pd.to_numeric(df_parsed["VALUE"], errors="coerce")
                    df_parsed = df_parsed.dropna(subset=["DATE","VALUE"])
                    if not df_parsed.empty:
                        new_rows.append(df_parsed)
    except Exception as e:
        errors.append(str(e))

    return new_rows, errors, emails_checked

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df    = load_invoices()
today = date.today()

import time as _time
# Auto-sync αφαιρέθηκε — έκανε IMAP requests στο page load.
# Ενημέρωση μόνο από την καρτέλα "Ενημέρωση".

# ── RENDER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="ptitle">📄 Έλεγχος Τιμολογίων</div>
</div>
""", unsafe_allow_html=True)

col_back, _ = st.columns([1, 4])
with col_back:
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("← Αρχική", key="back"):
        st.switch_page("Home.py")
    st.markdown("</div>", unsafe_allow_html=True)

tab_week, tab_month, tab_update = st.tabs(["📅 Εβδομαδιαία", "📆 Μηνιαία", "🔄 Ενημέρωση"])

# ═══════════════════════════════════════════════════════════════════════════════
with tab_week:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα. Μεταβείτε στην καρτέλα <b>Ενημέρωση</b>.</div>', unsafe_allow_html=True)
    else:
        sel_date = st.date_input("Επίλεξε ημέρα για εβδομάδα:", today)
        ws_dt    = datetime.combine(sel_date, datetime.min.time())
        start_w, end_w = get_week_range(ws_dt)
        st.markdown(f'<div class="info-box">📅 Εβδομάδα: <b>{start_w.strftime("%d/%m/%Y")}</b> — <b>{end_w.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)

        mask_w = (df["DATE"] >= start_w) & (df["DATE"] <= end_w)
        w_df   = df[mask_w]

        if not w_df.empty:
            inv_w = w_df[~w_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
            crd_w = w_df[ w_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
            net_w = inv_w - crd_w

            st.markdown(f"""<div class="kr kr3">
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Τιμολόγια Εβδ.</div><div class="kv">{fmt(inv_w)}</div></div>
              <div class="kc" style="--a:#c04a4a"><div class="kl">Πιστωτικά Εβδ.</div><div class="kv kv-red">{fmt(crd_w)}</div></div>
              <div class="kc" style="--a:#5a9f7a"><div class="kl">Καθαρό Σύνολο</div><div class="kv kv-green">{fmt(net_w)}</div></div>
            </div>""", unsafe_allow_html=True)

            disp = w_df.copy()
            disp["DATE"] = disp["DATE"].dt.strftime("%d/%m/%Y %H:%M")
            st.dataframe(
                disp.rename(columns={"DATE":"ΗΜΕΡΟΜΗΝΙΑ","TYPE":"ΤΥΠΟΣ","VALUE":"ΑΞΙΑ"})
                    .style.format({"ΑΞΙΑ": lambda v: fmt(v) if pd.notna(v) else "—"}),
                use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν εγγραφές για αυτή την εβδομάδα.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_month:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            s_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1], index=today.month-1)
        with col_b:
            available_years = sorted(df["DATE"].dt.year.unique(), reverse=True)
            s_y = st.selectbox("Έτος", available_years)

        mask_m = (df["DATE"].dt.month == s_m) & (df["DATE"].dt.year == s_y)
        m_df   = df[mask_m]

        if not m_df.empty:
            inv_m = m_df[~m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
            crd_m = m_df[ m_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
            net_m = inv_m - crd_m

            st.markdown(f"""<div class="kr kr3">
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Τιμολόγια Μήνα</div><div class="kv">{fmt(inv_m)}</div></div>
              <div class="kc" style="--a:#c04a4a"><div class="kl">Πιστωτικά Μήνα</div><div class="kv kv-red">{fmt(crd_m)}</div></div>
              <div class="kc" style="--a:#5a9f7a"><div class="kl">Καθαρό Μήνα</div><div class="kv kv-green">{fmt(net_m)}</div></div>
            </div>""", unsafe_allow_html=True)

            disp = m_df.copy()
            disp["DATE"] = disp["DATE"].dt.strftime("%d/%m/%Y %H:%M")
            st.dataframe(
                disp.rename(columns={"DATE":"ΗΜΕΡΟΜΗΝΙΑ","TYPE":"ΤΥΠΟΣ","VALUE":"ΑΞΙΑ"})
                    .style.format({"ΑΞΙΑ": lambda v: fmt(v) if pd.notna(v) else "—"}),
                use_container_width=True, hide_index=True)

            csv = m_df.rename(columns={"DATE":"ΗΜΕΡΟΜΗΝΙΑ","TYPE":"ΤΥΠΟΣ","VALUE":"ΑΞΙΑ"}).to_csv(index=False).encode("utf-8-sig")
            st.download_button(f"📥 Λήψη {MONTHS_GR[s_m-1]} {s_y} CSV", csv, f"invoices_{s_y}_{s_m:02d}.csv", "text/csv")
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν εγγραφές για αυτόν τον μήνα.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_update:
    st.markdown('<div class="sh">Σύνδεση Email</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">📧 Λογαριασμός: <b>{INV_EMAIL_USER}</b> — Αποστολέας: <b>{INV_EMAIL_SENDER}</b><br>Χρησιμοποιήστε <b>App Password</b> του Gmail.</div>', unsafe_allow_html=True)

    if _SECRET_PW:
        st.markdown('<div class="info-box">🔐 App Password φορτώθηκε αυτόματα από Streamlit Secrets.</div>', unsafe_allow_html=True)
        inv_pw = _SECRET_PW
    else:
        st.markdown('<div class="warn-box">⚠️ Δεν βρέθηκε <b>EMAIL_PASS</b> στα Secrets.</div>', unsafe_allow_html=True)
        inv_pw = st.text_input("🔐 Gmail App Password", type="password", key="inv_pw")

    col_inc, col_full = st.columns(2)
    run_inc  = col_inc.button("⚡ Γρήγορη Ενημέρωση (Νέα μόνο)", use_container_width=True)
    run_full = col_full.button("🔍 Βαθιά Σάρωση (2 χρόνια)",     use_container_width=True)

    if (run_inc or run_full) and inv_pw:
        lbl = "Βαθιά σάρωση 2 ετών..." if run_full else "Φόρτωση νέων emails..."
        with st.spinner(lbl):
            new_dfs, errs, checked = fetch_invoices_incremental(inv_pw, full_scan=run_full)
        if errs:
            st.error(f"❌ Σφάλμα: {errs[0]}")
        elif not new_dfs:
            st.markdown(f'<div class="info-box">✅ Ελέγχθηκαν {checked} emails — δεν βρέθηκαν νέα δεδομένα.</div>', unsafe_allow_html=True)
        else:
            n_new = merge_invoices(new_dfs)
            st.success(f"✅ Ενημερώθηκε! {n_new} νέες γραμμές από {checked} emails — αποθηκεύτηκαν στο Google Sheets.")
            st.rerun()

    elif (run_inc or run_full) and not inv_pw:
        st.error("Εισάγετε App Password.")

    if not df.empty:
        st.markdown('<div class="sh">Στατιστικά Google Sheets</div>', unsafe_allow_html=True)
        oldest = df["DATE"].min().strftime("%d/%m/%Y")
        newest = df["DATE"].max().strftime("%d/%m/%Y")
        st.markdown(f"""<div class="kr kr3">
          <div class="kc" style="--a:#6b8fd4"><div class="kl">Σύνολο Εγγραφών</div><div class="kv">{len(df)}</div></div>
          <div class="kc" style="--a:#5a9f7a"><div class="kl">Από</div><div class="kv" style="font-size:.85rem;">{oldest}</div></div>
          <div class="kc" style="--a:#5a9f7a"><div class="kl">Έως</div><div class="kv" style="font-size:.85rem;">{newest}</div></div>
        </div>""", unsafe_allow_html=True)
