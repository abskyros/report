import streamlit as st
import pandas as pd
import io, os
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND

st.set_page_config(page_title="Τιμολόγια — AB Σκύρος", page_icon="📄", layout="wide", initial_sidebar_state="collapsed")

# ── CONFIG ────────────────────────────────────────────────────────────────────
INV_EMAIL_USER   = "abf.skyros@gmail.com"
INV_EMAIL_SENDER = "Notifications@WeDoConnect.com"
INV_CACHE        = "invoices_cache.csv"
INV_ARCHIVE      = "invoices_archive.csv"
DEEP_SCAN_YEARS  = 2

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#f8f9fb!important;color:#111827!important;}
.stApp{background:#f8f9fb!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1.5rem 4rem!important;max-width:960px!important;margin:0 auto!important;}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid #e5e7eb;}
.ptitle{font-size:1.3rem;font-weight:700;color:#111827;}
.sh{font-size:.58rem;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:#9ca3af;margin:1.8rem 0 .7rem;border-bottom:1px solid #f3f4f6;padding-bottom:.4rem;}
.kr{display:grid;gap:.75rem;margin:.5rem 0 1.2rem;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:900px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr4,.kr3{grid-template-columns:1fr;}.block-container{padding:1rem 1rem 3rem!important;}}
.kc{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:.9rem 1rem;position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#3b82f6);}
.kl{font-size:.58rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#9ca3af;margin-bottom:.3rem;}
.kv{font-size:1.1rem;font-weight:700;color:#111827;}
.kv-green{color:#059669;}
.kv-red{color:#dc2626;}
.stButton>button{border-radius:9px!important;font-family:'Inter',sans-serif!important;font-size:.82rem!important;font-weight:600!important;padding:.6rem 1rem!important;transition:all .15s!important;}
.btn-b>button{background:#3b82f6!important;border:none!important;color:#fff!important;}
.btn-b>button:hover{opacity:.88!important;}
.btn-back>button{background:#fff!important;border:1px solid #d1d5db!important;color:#374151!important;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #e5e7eb!important;gap:.2rem!important;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#6b7280!important;font-size:.74rem!important;font-weight:600!important;letter-spacing:.05em!important;text-transform:uppercase!important;padding:.5rem .9rem!important;border-radius:8px 8px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#3b82f6!important;background:#eff6ff!important;border-bottom:2px solid #3b82f6!important;}
[data-testid="stDataFrame"]{border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.info-box{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#1d4ed8;margin:.6rem 0;}
.warn-box{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#92400e;margin:.6rem 0;}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def load_cache():
    if os.path.exists(INV_CACHE):
        df = pd.read_csv(INV_CACHE)
        if not df.empty: df["DATE"] = pd.to_datetime(df["DATE"])
        return df
    return pd.DataFrame(columns=["DATE","TYPE","VALUE"])

def load_all():
    parts = []
    for f in [INV_CACHE, INV_ARCHIVE]:
        if os.path.exists(f):
            df = pd.read_csv(f)
            if not df.empty:
                df["DATE"] = pd.to_datetime(df["DATE"])
                parts.append(df)
    if parts:
        combined = pd.concat(parts)
        combined = combined.drop_duplicates(subset=["DATE","TYPE","VALUE"])
        return combined.sort_values("DATE", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["DATE","TYPE","VALUE"])

def save_and_archive(df_all):
    cutoff = datetime.now() - timedelta(days=365*DEEP_SCAN_YEARS)
    recent = df_all[df_all["DATE"] >= cutoff].copy()
    old    = df_all[df_all["DATE"]  < cutoff].copy()
    recent.to_csv(INV_CACHE, index=False)
    if not old.empty:
        if os.path.exists(INV_ARCHIVE):
            existing = pd.read_csv(INV_ARCHIVE)
            existing["DATE"] = pd.to_datetime(existing["DATE"])
            old = pd.concat([existing, old]).drop_duplicates(subset=["DATE","TYPE","VALUE"])
        old.to_csv(INV_ARCHIVE, index=False)

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
                header_row_index = i
                break

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
    """Smart incremental fetch για τιμολόγια"""
    df_existing = load_cache()
    cutoff_dt   = None

    if not full_scan and not df_existing.empty:
        last_dt    = df_existing["DATE"].max()
        cutoff_dt  = last_dt - timedelta(days=5)  # 5 μέρες overlap

    new_rows = []
    errors   = []
    emails_checked = 0

    try:
        with MailBox("imap.gmail.com").login(INV_EMAIL_USER, password) as mb:
            criteria = AND(from_=INV_EMAIL_SENDER)
            messages = list(mb.fetch(criteria, limit=500 if full_scan else 50, reverse=True))

            for msg in messages:
                msg_date = msg.date

                # Skip παλιά emails σε incremental mode
                if not full_scan and cutoff_dt and msg_date and msg_date < cutoff_dt:
                    continue

                # Skip πάρα πολύ παλιά σε full scan
                if full_scan:
                    cutoff_year = datetime.now().year - DEEP_SCAN_YEARS
                    if msg_date and msg_date.year < cutoff_year:
                        continue

                emails_checked += 1

                for att in msg.attachments:
                    if att.filename and att.filename.lower().endswith(('.xlsx', '.csv', '.xls')):
                        df = find_header_and_load(att.payload, att.filename)
                        if df is not None:
                            col_date  = next((c for c in df.columns if 'ΗΜΕΡΟΜΗΝΙΑ' in c), None)
                            col_value = next((c for c in df.columns if 'ΑΞΙΑ' in c or 'ΣΥΝΟΛΟ' in c), None)
                            col_type  = next((c for c in df.columns if 'ΤΥΠΟΣ' in c), None)

                            if col_date and col_value and col_type:
                                temp_df = df[[col_date, col_type, col_value]].copy()
                                temp_df.columns = ['DATE', 'TYPE', 'VALUE']
                                temp_df['DATE']  = pd.to_datetime(temp_df['DATE'], errors='coerce')
                                if temp_df['VALUE'].dtype == object:
                                    temp_df['VALUE'] = temp_df['VALUE'].astype(str).str.replace('€','').str.replace(',','.').str.strip()
                                temp_df['VALUE'] = pd.to_numeric(temp_df['VALUE'], errors='coerce').fillna(0)
                                temp_df = temp_df.dropna(subset=['DATE'])

                                # Filter: keep only rows after cutoff
                                if not full_scan and cutoff_dt:
                                    temp_df = temp_df[temp_df['DATE'] >= cutoff_dt]

                                new_rows.append(temp_df)

    except Exception as e:
        errors.append(str(e))

    return new_rows, errors, emails_checked

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df  = load_all()
today = date.today()

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

# ── TABS ─────────────────────────────────────────────────────────────────────
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
                    .style.format({"ΑΞΙΑ": "{:.2f} €"}),
                use_container_width=True, hide_index=True
            )
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
                    .style.format({"ΑΞΙΑ": "{:.2f} €"}),
                use_container_width=True, hide_index=True
            )

            csv = m_df.rename(columns={"DATE":"ΗΜΕΡΟΜΗΝΙΑ","TYPE":"ΤΥΠΟΣ","VALUE":"ΑΞΙΑ"}).to_csv(index=False).encode("utf-8-sig")
            st.download_button(f"📥 Λήψη {MONTHS_GR[s_m-1]} {s_y} CSV", csv, f"invoices_{s_y}_{s_m:02d}.csv", "text/csv")
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν εγγραφές για αυτόν τον μήνα.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_update:
    st.markdown('<div class="sh">Σύνδεση Email</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">📧 Λογαριασμός: <b>{INV_EMAIL_USER}</b> — Αποστολέας: <b>{INV_EMAIL_SENDER}</b><br>Χρησιμοποιήστε <b>App Password</b> του Gmail.</div>', unsafe_allow_html=True)

    inv_pw = st.text_input("🔐 Gmail App Password", type="password", key="inv_pw")

    col_inc, col_full = st.columns(2)
    run_inc  = col_inc.button("⚡ Γρήγορη Ενημέρωση (Νέα μόνο)", use_container_width=True)
    run_full = col_full.button("🔍 Βαθιά Σάρωση (2 χρόνια)", use_container_width=True)

    if (run_inc or run_full) and inv_pw:
        lbl = "Βαθιά σάρωση 2 ετών..." if run_full else "Φόρτωση νέων emails..."
        with st.spinner(lbl):
            new_dfs, errs, checked = fetch_invoices_incremental(inv_pw, full_scan=run_full)

        if errs:
            st.error(f"❌ Σφάλμα: {errs[0]}")
        elif not new_dfs:
            st.markdown(f'<div class="info-box">✅ Ελέγχθηκαν {checked} emails — δεν βρέθηκαν νέα δεδομένα.</div>', unsafe_allow_html=True)
        else:
            combined_new = pd.concat(new_dfs, ignore_index=True)
            old_all = load_all()
            merged  = pd.concat([old_all, combined_new]).drop_duplicates(subset=["DATE","TYPE","VALUE"]).sort_values("DATE", ascending=False).reset_index(drop=True)
            save_and_archive(merged)
            n_new = len(combined_new)
            st.success(f"✅ Ενημερώθηκε! Βρέθηκαν {n_new} νέες γραμμές από {checked} emails.")
            st.rerun()

    elif (run_inc or run_full) and not inv_pw:
        st.error("Εισάγετε App Password.")

    # Stats
    if not df.empty:
        st.markdown('<div class="sh">Στατιστικά Cache</div>', unsafe_allow_html=True)
        n_cache = len(pd.read_csv(INV_CACHE)) if os.path.exists(INV_CACHE) else 0
        n_arch  = len(pd.read_csv(INV_ARCHIVE)) if os.path.exists(INV_ARCHIVE) else 0
        oldest  = df["DATE"].min().strftime("%d/%m/%Y") if not df.empty else "—"
        newest  = df["DATE"].max().strftime("%d/%m/%Y") if not df.empty else "—"
        st.markdown(f"""<div class="kr kr4">
          <div class="kc" style="--a:#6b8fd4"><div class="kl">Εγγραφές Cache</div><div class="kv">{n_cache}</div></div>
          <div class="kc" style="--a:#7c5abf"><div class="kl">Εγγραφές Archive</div><div class="kv">{n_arch}</div></div>
          <div class="kc" style="--a:#5a9f7a"><div class="kl">Από</div><div class="kv" style="font-size:.85rem;">{oldest}</div></div>
          <div class="kc" style="--a:#5a9f7a"><div class="kl">Έως</div><div class="kv" style="font-size:.85rem;">{newest}</div></div>
        </div>""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
