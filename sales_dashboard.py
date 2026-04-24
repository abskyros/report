import streamlit as st
import pandas as pd
import io, os, re, json
from imap_tools import MailBox, AND
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import pytesseract
from pdf2image import convert_from_bytes
import traceback

# ══════════════════════════════════════════════════════════
# ΡΥΘΜΙΣΕΙΣ
# ══════════════════════════════════════════════════════════
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_FROM    = "abf.skyros@gmail.com"
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"
HISTORY_FILE  = "sales_history.csv"

# ══════════════════════════════════════════════════════════
# PAGE CONFIG & CSS (Φωτεινό Slate Blue Theme)
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ · Analytics",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}

/* Ανοιχτό Slate Background */
.stApp {
    background: #475569; 
    color: #f8fafc;
}

section[data-testid="stSidebar"]{display:none;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:2rem 2.5rem 4rem;max-width:1400px;}

/* Κάρτες KPI - Πιο φωτεινές */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0;}
.kpi-card {
    background: #64748b; 
    border: 1px solid #94a3b8;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:var(--accent,#10b981);}
.kpi-label{font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#cbd5e1;margin-bottom:.5rem;}
.kpi-value{font-family:'DM Mono',monospace;font-size:1.85rem;font-weight:600;color:#ffffff;line-height:1;}
.kpi-delta{font-size:.82rem;margin-top:.5rem;font-weight:600;}
.delta-up{color:#6ee7b7;} .delta-down{color:#fca5a5;}

/* Headers */
.sec-header{display:flex;align-items:center;gap:.6rem;font-size:.75rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#f1f5f9;border-bottom:2px solid #94a3b8;padding-bottom:.6rem;margin:2rem 0 1rem;}
.sec-header span{color:#34d399;}

/* Πίνακας Τμημάτων */
.dept-row{display:flex;align-items:center;gap:.8rem;padding:.65rem .2rem;border-bottom:1px solid #475569;}
.dept-name{flex:1;font-size:.85rem;font-weight:500;color:#f8fafc;}
.dept-val{font-family:'DM Mono';font-size:.82rem;color:#f1f5f9;width:6.5rem;text-align:right;}
.dept-bar-wrap{width:120px;height:6px;background:#334155;border-radius:3px;}
.dept-bar{height:100%;border-radius:3px;background:#34d399;}

/* Tabs & Inputs */
[data-baseweb="tab-list"]{gap:.5rem;background:transparent;border-bottom:2px solid #94a3b8;}
[data-baseweb="tab"]{color:#cbd5e1!important;font-weight:700;padding:.8rem 1.5rem!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#34d399!important;background:#334155!important;border-bottom:3px solid #34d399!important;}

.stButton>button{background:#10b981!important;color:#0f172a!important;font-weight:800!important;border:none!important;}
button[kind="secondary"]{background:#334155!important;border:1px solid #94a3b8!important;color:#f8fafc!important;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# ══════════════════════════════════════════════════════════
DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    s = f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return f"{s} €"

def parse_num(s: str) -> float:
    if not s: return 0.0
    s = re.sub(r'[^\d,\.]', '', s)
    if '.' in s and ',' in s:
        s = s.replace('.','').replace(',','.') if s.index('.') < s.index(',') else s.replace(',','')
    elif ',' in s: s = s.replace(',','.')
    try: return float(s)
    except: return 0.0

def delta_html(now, prev, is_euro=True):
    if not prev or prev == 0: return ""
    diff = now - prev
    pct = diff / prev * 100
    sign = "▲" if diff >= 0 else "▼"
    cls = "delta-up" if diff >= 0 else "delta-down"
    val = fmt_euro(abs(diff)) if is_euro else f"{abs(diff):.0f}"
    return f'<div class="kpi-delta {cls}">{sign} {val} ({pct:+.1f}%)</div>'

# ══════════════════════════════════════════════════════════
# DATA ENGINE (CSV & OCR)
# ══════════════════════════════════════════════════════════
def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        if 'depts' not in df.columns: df['depts'] = '[]'
        return df.sort_values('date', ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=['date','netday','customers','avg_basket','depts'])

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_FILE, index=False)

def upsert(df: pd.DataFrame, record: dict) -> pd.DataFrame:
    mask = df['date'] == record['date']
    if mask.any():
        for k, v in record.items():
            if v is not None: df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    return df.sort_values('date', ascending=False).reset_index(drop=True)

def ocr_page(img) -> str:
    return pytesseract.image_to_string(img, lang='ell+eng')

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {'date': None, 'netday': None, 'customers': None, 'avg_basket': None, 'depts': '[]'}
    try:
        images = convert_from_bytes(pdf_bytes, dpi=180, fmt='jpeg', first_page=1, last_page=2)
        if not images: return result
        p1 = ocr_page(images[0])
        
        m = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', p1) or re.search(r'(\d{2}/\d{2}/\d{4})', p1)
        if m:
            try: result['date'] = datetime.strptime(m.group(1), "%d/%m/%Y").date()
            except: pass

        for key, label in [('netday', r'Net\s*Day\s*Sa[li1]Dis'), ('customers', r'Num\s*Of\s*Cus'), ('avg_basket', r'Avg\s*Sa[li1]\s*Cus')]:
            match = re.search(label + r'[\s:–\-]*([\d\.,]+)', p1, re.I)
            if match:
                val = parse_num(match.group(1))
                result[key] = int(val) if key == 'customers' else val

        dept_text = p1 + ("\n" + ocr_page(images[1]) if len(images) > 1 else "")
        dept_pat = re.compile(r'(\d{3})\s+([Α-ΩA-Z\s\-\.\/&]{2,28}?)\s+([\d\.,]+)\s+([\d\.,]+)')
        depts, seen = [], set()
        for m in dept_pat.finditer(dept_text):
            net = parse_num(m.group(4))
            nm = m.group(2).strip()
            if net > 0.5 and nm not in seen:
                depts.append({'code': m.group(1), 'name': nm, 'sales': net})
                seen.add(nm)
        result['depts'] = json.dumps(sorted(depts, key=lambda x: x['sales'], reverse=True), ensure_ascii=False)
    except: pass
    return result

# ══════════════════════════════════════════════════════════
# EMAIL SYNC (Πλήρες ιστορικό από 11/10/2024)
# ══════════════════════════════════════════════════════════
def sync_emails(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    logs = []
    existing_dates = set(df['date'].values) if not df.empty else set()
    
    # Ημερομηνία Έναρξης βάσει του αιτήματός σου
    since_date = date(2024, 10, 11)
    logs.append(f"📡 Έναρξη βαθιάς αναζήτησης από **{since_date.strftime('%d/%m/%Y')}** ...")

    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            mailbox.folder.set('INBOX')
            criteria = AND(from_=EMAIL_FROM, date_gte=since_date)
            
            found = 0
            for msg in mailbox.fetch(criteria, reverse=True, mark_seen=False):
                if "ΑΒ ΣΚΥΡΟΣ" not in msg.subject.upper(): continue
                
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        data = extract_pdf_data(att.payload)
                        d = data['date'] or msg.date.date()
                        if d not in existing_dates and data['netday']:
                            data['date'] = d
                            df = upsert(df, data)
                            existing_dates.add(d)
                            found += 1
                        break
            logs.append(f"✅ Ολοκληρώθηκε! Προστέθηκαν **{found}** νέες αναφορές.")
    except Exception as e:
        logs.append(f"❌ Σφάλμα: {e}")
    return df, logs

# ══════════════════════════════════════════════════════════
# UI - MAIN PAGE
# ══════════════════════════════════════════════════════════
df = load_history()
gr_time = datetime.now(ZoneInfo("Europe/Athens")).strftime('%d/%m/%Y %H:%M')

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
  <div>
    <div style="font-size:.75rem;font-weight:800;letter-spacing:.15em;text-transform:uppercase;color:#34d399;margin-bottom:.2rem;">ΑΒ ΣΚΥΡΟΣ · BI DASHBOARD</div>
    <h1 style="font-size:2.2rem;font-weight:800;color:#ffffff;margin:0;">Στατιστικά Πωλήσεων</h1>
  </div>
  <div style="text-align:right;">
    <div style="font-size:.7rem;color:#cbd5e1;">Τελευταία Ενημέρωση</div>
    <div style="font-family:'DM Mono';font-size:.85rem;color:#f1f5f9;">{gr_time}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Controls
c1, c2, c3 = st.columns([1.2, 2, 2.8])
with c1:
    if st.button("🔄 Πλήρης Συγχρονισμός (από 10/24)", use_container_width=True, type="primary"):
        with st.spinner("Αναζήτηση στο ιστορικό..."):
            df, logs = sync_emails(df)
            save_history(df)
            for l in logs: st.info(l)
            st.rerun()

with c2:
    filter_mode = st.segmented_control("Προβολή ανά:", ["Ημέρα", "Εβδομάδα", "Μήνα", "Εύρος"], default="Ημέρα")

with c3:
    if filter_mode == "Ημέρα":
        selected_date = st.date_input("Επιλογή Ημέρας", value=df['date'].max() if not df.empty else date.today())
        mask = df[df['date'] == selected_date]
    elif filter_mode == "Εβδομάδα":
        ref_date = st.date_input("Επιλογή Εβδομάδας (οποιαδήποτε μέρα)", value=date.today())
        start_w = ref_date - timedelta(days=ref_date.weekday())
        end_w = start_w + timedelta(days=6)
        mask = df[(df['date'] >= start_w) & (df['date'] <= end_w)]
        st.caption(f"Διάστημα: {start_w.strftime('%d/%m')} - {end_w.strftime('%d/%m')}")
    elif filter_mode == "Μήνα":
        m_idx = st.selectbox("Επιλογή Μήνα", range(1, 13), format_func=lambda x: MONTHS_GR[x-1], index=date.today().month-1)
        mask = df[df['date'].apply(lambda x: x.month == m_idx and x.year == date.today().year)]
    else:
        dates = st.date_input("Επιλογή Διαστήματος", value=[date.today() - timedelta(days=7), date.today()])
        if len(dates) == 2:
            mask = df[(df['date'] >= dates[0]) & (df['date'] <= dates[1])]
        else: mask = pd.DataFrame()

# TABS
tab1, tab2, tab3 = st.tabs(["📍 Αναφορά Περιόδου", "📈 Τάσεις", "📋 Ιστορικό"])

if not mask.empty:
    with tab1:
        total_sales = mask['netday'].sum()
        total_cus = mask['customers'].sum()
        avg_basket = total_sales / total_cus if total_cus > 0 else 0
        
        # Υπολογισμός "Προηγούμενης" για το Delta (αν είναι μία μέρα)
        prev_val = None
        if filter_mode == "Ημέρα":
            p_row = df[df['date'] < selected_date].head(1)
            prev_val = p_row.iloc[0] if not p_row.empty else None

        st.markdown(f"""<div class="kpi-grid">
            {kpi_card("Πωλήσεις", total_sales, prev_val['netday'] if prev_val is not None else None, "#10b981")}
            {kpi_card("Πελάτες", total_cus, prev_val['customers'] if prev_val is not None else None, "#3b82f6", False)}
            {kpi_card("Μ.Ό. Καλαθιού", avg_basket, prev_val['avg_basket'] if prev_val is not None else None, "#8b5cf6")}
            {kpi_card("Ημέρες Δείγματος", len(mask), None, "#f59e0b", False)}
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec-header"><span>▍</span> Ανάλυση Τμημάτων (Σύνολα Περιόδου)</div>', unsafe_allow_html=True)
        # Συγκεντρωτικά τμήματα
        agg_depts = {}
        for _, row in mask.iterrows():
            d_list = json.loads(row['depts'])
            for d in d_list:
                agg_depts[d['name']] = agg_depts.get(d['name'], 0) + d['sales']
        
        if agg_depts:
            sorted_depts = sorted(agg_depts.items(), key=lambda x: x[1], reverse=True)
            mx = sorted_depts[0][1]
            rows = "".join(f'<div class="dept-row"><div class="dept-name">{n}</div><div class="dept-bar-wrap"><div class="dept-bar" style="width:{v/mx*100:.0f}%"></div></div><div class="dept-val">{fmt_euro(v)}</div></div>' for n, v in sorted_depts[:12])
            st.markdown(f'<div style="background:#64748b;border-radius:12px;padding:1rem;border:1px solid #94a3b8;">{rows}</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("**Πορεία Πωλήσεων**")
        line_data = mask.sort_values('date')
        line_data['label'] = line_data['date'].apply(lambda x: x.strftime('%d/%m'))
        st.line_chart(line_data.set_index('label')['netday'], color="#10b981")

    with tab3:
        disp = mask[['date','netday','customers']].copy()
        disp['date'] = disp['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        disp.columns = ["Ημερομηνία", "Πωλήσεις", "Πελάτες"]
        st.dataframe(disp, use_container_width=True, hide_index=True)
else:
    st.info("Δεν βρέθηκαν δεδομένα για τις επιλεγμένες παραμέτρους.")
