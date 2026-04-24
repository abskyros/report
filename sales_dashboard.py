import streamlit as st
import pandas as pd
import io, os, re, json
from imap_tools import MailBox, AND
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo # Προσθήκη για σωστή ώρα Ελλάδος
import pytesseract
from pdf2image import convert_from_bytes
import traceback

# ══════════════════════════════════════════════════════════
# ΡΥΘΜΙΣΕΙΣ
# ══════════════════════════════════════════════════════════
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_FROM    = "abf.skyros@gmail.com"
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"          # ← θέμα για γρήγορο φιλτράρισμα
HISTORY_FILE  = "sales_history.csv"

# ══════════════════════════════════════════════════════════
# PAGE CONFIG & CSS (Πιο φωτεινό Dark Mode - Slate)
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
/* Πιο γλυκό, φωτεινό background αντί για κατάμαυρο */
.stApp{background:#334155;color:#f8fafc;}
section[data-testid="stSidebar"]{display:none;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:2rem 2.5rem 4rem;max-width:1400px;}

.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0;}
/* Πιο ανοιχτές κάρτες */
.kpi-card{background:#475569;border:1px solid #64748b;border-radius:12px;padding:1.4rem 1.6rem;position:relative;overflow:hidden;transition:border-color .2s;}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent,#10b981);}
.kpi-card:hover{border-color:#94a3b8;}
.kpi-label{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#cbd5e1;margin-bottom:.5rem;}
.kpi-value{font-family:'DM Mono',monospace;font-size:1.75rem;font-weight:500;color:#f8fafc;line-height:1;}
.kpi-delta{font-size:.78rem;margin-top:.5rem;font-weight:500;}
.delta-up{color:#34d399;} .delta-down{color:#fb7185;}

.sec-header{display:flex;align-items:center;gap:.6rem;font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#f1f5f9;border-bottom:1px solid #64748b;padding-bottom:.6rem;margin:2rem 0 1rem;}
.sec-header span{color:#10b981;}

.dept-row{display:flex;align-items:center;gap:.8rem;padding:.55rem .2rem;border-bottom:1px solid #334155;}
.dept-rank{font-family:'DM Mono';font-size:.7rem;color:#cbd5e1;width:1.4rem;text-align:right;flex-shrink:0;}
.dept-name{flex:1;font-size:.82rem;color:#f8fafc;}
.dept-bar-wrap{width:120px;height:4px;background:#64748b;border-radius:2px;flex-shrink:0;}
.dept-bar{height:100%;border-radius:2px;background:#10b981;}
.dept-val{font-family:'DM Mono';font-size:.78rem;color:#e2e8f0;width:6rem;text-align:right;flex-shrink:0;}

[data-baseweb="tab-list"]{gap:.5rem;background:transparent;border-bottom:1px solid #64748b;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#e2e8f0!important;font-size:.8rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:.6rem 1.2rem!important;border-radius:6px 6px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#10b981!important;background:#475569!important;border-bottom:2px solid #10b981!important;}

.stButton>button{background:#10b981!important;color:#0f172a!important;border:none!important;border-radius:8px!important;font-weight:700!important;font-size:.82rem!important;letter-spacing:.06em;padding:.55rem 1.4rem!important;transition:background .15s!important;}
.stButton>button:hover{background:#059669!important;}
button[kind="secondary"]{background:#475569!important;color:#f8fafc!important;border:1px solid #64748b!important;}
button[kind="secondary"]:hover{background:#64748b!important;}

[data-testid="stDataFrame"]{border:1px solid #64748b;border-radius:10px;overflow:hidden;}
[data-baseweb="select"]>div{background:#475569!important;border-color:#64748b!important;color:#f8fafc!important;}
[data-testid="stAlert"]{background:#475569;border-color:#64748b;color:#f1f5f9;}
.stSpinner>div{border-top-color:#10b981!important;}
details{background:#475569!important;border:1px solid #64748b!important;border-radius:10px!important;color:#f8fafc;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ΒΟΗΘΗΤΙΚΕΣ
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
    elif ',' in s:
        s = s.replace(',','.')
    try:    return float(s)
    except: return 0.0

def delta_html(now, prev, is_euro=True):
    if not prev or prev == 0: return ""
    diff = now - prev
    pct  = diff / prev * 100
    sign = "▲" if diff >= 0 else "▼"
    cls  = "delta-up" if diff >= 0 else "delta-down"
    val  = fmt_euro(abs(diff)) if is_euro else f"{abs(diff):.0f}"
    return f'<div class="kpi-delta {cls}">{sign} {val} ({pct:+.1f}%)</div>'

# ══════════════════════════════════════════════════════════
# ΑΡΧΕΙΟ CSV
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

# ══════════════════════════════════════════════════════════
# OCR  –  ανθεκτικό σε OCR λάθη (l↔i, I↔l κλπ.)
# ══════════════════════════════════════════════════════════
def ocr_page(img) -> str:
    return pytesseract.image_to_string(img, lang='ell+eng')

_FUZZY = {
    'NetDaySalDis': r'Net\s*Day\s*Sa[li1]Dis',
    'NumOfCus':     r'Num\s*Of\s*Cus',
    'AvgSalCus':    r'Avg\s*Sa[li1]\s*Cus',
    'AvgSaiCus':    r'Avg\s*Sa[li1]\s*Cus',   # alias
}

def find_value(text: str, label: str) -> str | None:
    pattern = _FUZZY.get(label, re.escape(label))
    NUM = r'[\s:–\-]*([\d][^\n]{0,30}?)\n'
    m = re.search(pattern + NUM, text, re.IGNORECASE)
    if m:
        candidate = re.search(r'([\d][\d\.,]*)', m.group(1))
        if candidate:
            return candidate.group(1)
    idx = re.search(pattern, text, re.IGNORECASE)
    if not idx: return None
    snippet = text[idx.end(): idx.end() + 60]
    n = re.search(r'([\d][\d\.,]*)', snippet)
    return n.group(1) if n else None

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

        raw = find_value(p1, 'NetDaySalDis')
        if raw: result['netday'] = parse_num(raw)

        raw = find_value(p1, 'NumOfCus')
        if raw:
            try: result['customers'] = int(parse_num(raw))
            except: pass

        raw = find_value(p1, 'AvgSalCus')
        if raw: result['avg_basket'] = parse_num(raw)

        dept_text = p1
        if len(images) > 1:
            dept_text += "\n" + ocr_page(images[1])

        dept_pat = re.compile(
            r'(\d{3})\s+([Α-ΩA-Zα-ωa-z][Α-ΩA-Zα-ωa-z\s\-\.\/&]{2,28}?)\s+'
            r'([\d\.,]+)\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+'
        )
        depts, seen = [], set()
        for m in dept_pat.finditer(dept_text):
            net = parse_num(m.group(4))
            nm  = m.group(2).strip()
            if net > 0.5 and nm not in seen:
                depts.append({'code': m.group(1), 'name': nm, 'sales': net})
                seen.add(nm)
        result['depts'] = json.dumps(
            sorted(depts, key=lambda x: x['sales'], reverse=True),
            ensure_ascii=False
        )

    except Exception as e:
        st.warning(f"OCR Error: {e}")
    return result

# ══════════════════════════════════════════════════════════
# SMART EMAIL SYNC (Από 11/10/2024)
# ══════════════════════════════════════════════════════════
def _pick_folder(mailbox: MailBox) -> str:
    try:
        for f in mailbox.folder.list():
            n = f.name.upper()
            if 'ALL' in n and ('MAIL' in n or 'GMAIL' in n): return f.name
    except: pass
    return 'INBOX'

import unicodedata
def _norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper()

def sync_emails(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    logs   = []
    
    # Λίστα με ημερομηνίες που ΕΧΟΥΜΕ ΗΔΗ
    existing_dates = set(df['date'].values) if not df.empty else set()
    
    # Ημερομηνία Έναρξης συγχρονισμού: 11/10/2024 (Ακριβώς όπως ζητήθηκε)
    since_date = date(2024, 10, 11)
    
    logs.append(f"📡 Αναζήτηση emails από **{since_date.strftime('%d/%m/%Y')}** ...")

    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            try:    mailbox.folder.set(_pick_folder(mailbox))
            except: mailbox.folder.set('INBOX')

            criteria = AND(from_=EMAIL_FROM, date_gte=since_date)

            checked = found = 0
            target_subj = _norm(EMAIL_SUBJECT)

            for msg in mailbox.fetch(criteria, reverse=True, mark_seen=False):
                checked += 1

                if target_subj not in _norm(msg.subject):
                    continue
                
                msg_date = msg.date.date()
                if msg_date in existing_dates or (msg_date - timedelta(days=1)) in existing_dates:
                    continue

                for att in msg.attachments:
                    if not att.filename.lower().endswith('.pdf'): continue

                    data = extract_pdf_data(att.payload)
                    if data['date'] is None: data['date'] = msg_date

                    if data['date'] in existing_dates:
                        continue

                    if data['netday'] and data['netday'] > 0:
                        df    = upsert(df, data)
                        existing_dates.add(data['date'])
                        found += 1
                    break

            logs.append(f"🔎 Emails που ελέγχθηκαν: **{checked}** · Νέες αναφορές που προστέθηκαν: **{found}**")

    except Exception as e:
        logs.append(f"❌ **IMAP σφάλμα:** {e}")
        logs.append("```\n" + traceback.format_exc() + "\n```")

    return df, logs

# ══════════════════════════════════════════════════════════
# ΣΤΑΤΙΣΤΙΚΑ ΠΕΡΙΟΔΟΥ
# ══════════════════════════════════════════════════════════
def period_stats(df, start, end):
    sub = df[(df['date'] >= start) & (df['date'] <= end)]
    if sub.empty:
        return {'total':0,'avg_day':0,'avg_cus':0,'days':0,'peak':None,'peak_val':0}
    return {
        'total':    sub['netday'].sum(),
        'avg_day':  sub['netday'].mean(),
        'avg_cus':  sub['customers'].mean() if 'customers' in sub else 0,
        'days':     len(sub),
        'peak':     sub.loc[sub['netday'].idxmax(),'date'],
        'peak_val': sub['netday'].max(),
    }

# ══════════════════════════════════════════════════════════
# ── UI ─────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════

df = load_history()

if 'auto_synced' not in st.session_state:
    st.session_state['auto_synced'] = False

last_d = df['date'].max() if not df.empty else None
needs_sync = (last_d is None) or (last_d < date.today())

# Σωστή Ώρα Ελλάδος
current_gr_time = datetime.now(ZoneInfo("Europe/Athens")).strftime('%d/%m/%Y %H:%M')

# Header
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.5rem;">
  <div>
    <div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#10b981;margin-bottom:.2rem;">
      ΑΒ ΣΚΥΡΟΣ · ΚΑΤΑΣΤΗΜΑ 1082
    </div>
    <h1 style="font-size:1.9rem;font-weight:700;color:#f8fafc;margin:0;letter-spacing:-.02em;">
      Sales Analytics
    </h1>
  </div>
  <div style="text-align:right;">
    <div style="font-size:.7rem;color:#cbd5e1;">Τελευταία ενημέρωση (Ώρα Ελλάδος)</div>
    <div style="font-family:'DM Mono';font-size:.75rem;color:#e2e8f0;">{current_gr_time}</div>
    {"<div style='font-size:.7rem;color:#f59e0b;margin-top:.3rem;'>⚠ Υπάρχουν νέα δεδομένα</div>" if needs_sync and st.session_state['auto_synced'] else ""}
  </div>
</div>
""", unsafe_allow_html=True)

# Toolbar
tc1, tc2, tc3 = st.columns([1, 1, 4])
with tc1:
    sync_btn   = st.button("⟳  Συγχρονισμός", use_container_width=True, type="primary")
with tc2:
    upload_btn = st.button("↑  PDF Upload",    use_container_width=True, type="secondary")

if sync_btn:
    with st.spinner("Σύνδεση στο Gmail (αναζήτηση από 11/10/2024)..."):
        df, logs = sync_emails(df)
        save_history(df)
        st.session_state['auto_synced'] = True
    for l in logs: st.markdown(l)
    st.rerun()

if needs_sync and not st.session_state['auto_synced']:
    with st.spinner("🔄 Αυτόματη ενημέρωση..."):
        df, logs = sync_emails(df)
        save_history(df)
        st.session_state['auto_synced'] = True
    st.rerun()

if upload_btn:
    st.session_state['show_upload'] = True

if st.session_state.get('show_upload'):
    uploaded = st.file_uploader("PDF", type="pdf", label_visibility="collapsed")
    if uploaded:
        raw = uploaded.read()
        with st.spinner("OCR επεξεργασία..."):
            data = extract_pdf_data(raw)
        if data['netday'] and data['netday'] > 0:
            if data['date'] is None: data['date'] = date.today()
            df = upsert(df, data)
            save_history(df)
            st.success(f"✅ {data['date'].strftime('%d/%m/%Y')} — {fmt_euro(data['netday'])} · {data['customers']} πελάτες")
            st.session_state['show_upload'] = False
            st.rerun()
        else:
            st.error("Δεν βρέθηκαν δεδομένα.")
            with st.expander("Debug (σελ. 1 OCR)"):
                imgs = convert_from_bytes(raw, dpi=180, fmt='jpeg')
                st.text(ocr_page(imgs[0])[:3000])

if df.empty:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#cbd5e1;">
      <div style="font-size:3rem;margin-bottom:1rem;">📭</div>
      <div style="font-size:1rem;font-weight:600;color:#f1f5f9;">Δεν υπάρχουν δεδομένα</div>
      <div style="font-size:.82rem;margin-top:.5rem;">Πατήστε «Συγχρονισμός» ή ανεβάστε PDF</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "📍  Τελευταία Αναφορά", "📈  Τάσεις", "⚖️  Συγκρίσεις", "📋  Ιστορικό"
])

# ════════════════════════════════════════
# TAB 1 – ΤΕΛΕΥΤΑΙΑ ΑΝΑΦΟΡΑ
# ════════════════════════════════════════
with tab1:
    latest = df.iloc[0]
    prev   = df.iloc[1] if len(df) > 1 else None
    prev7r = df[df['date'] == (latest['date'] - timedelta(days=7))]
    prev7  = prev7r.iloc[0] if not prev7r.empty else None

    ld = latest['date']
    st.markdown(
        f'<div style="font-size:.82rem;color:#cbd5e1;margin-bottom:1.2rem;">'
        f'{DAYS_GR[ld.weekday()]} · {ld.day} {MONTHS_GR[ld.month-1]} {ld.year}</div>',
        unsafe_allow_html=True
    )

    def kpi_card(label, value, prev_val, accent, is_euro=True):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return f'<div class="kpi-card" style="--accent:{accent}"><div class="kpi-label">{label}</div><div class="kpi-value">—</div></div>'
        disp = fmt_euro(value) if is_euro else f"{int(value):,}".replace(",",".")
        dlt  = delta_html(value, prev_val, is_euro) if prev_val else ""
        return (f'<div class="kpi-card" style="--accent:{accent}">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{disp}</div>{dlt}</div>')

    st.markdown(f"""<div class="kpi-grid">
      {kpi_card("Πωλήσεις Ημέρας",  latest['netday'],    prev['netday']    if prev is not None else None, "#10b981")}
      {kpi_card("Αριθμός Πελατών",  latest['customers'], prev['customers'] if prev is not None else None, "#3b82f6", False)}
      {kpi_card("Μ.Ό. Καλαθιού",   latest['avg_basket'],prev['avg_basket'] if prev is not None else None, "#8b5cf6")}
      {kpi_card("Σύγκριση -7 ημέρ.",latest['netday'],   prev7['netday']   if prev7 is not None else None, "#f59e0b")}
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-header"><span>▍</span> Ανάλυση Τμημάτων</div>', unsafe_allow_html=True)
    try:
        depts = json.loads(latest.get('depts','[]') or '[]')
        if depts:
            mx   = depts[0]['sales']
            rows = "".join(
                f'<div class="dept-row">'
                f'<div class="dept-rank">{i+1}</div>'
                f'<div class="dept-name">{d["name"]}</div>'
                f'<div class="dept-bar-wrap"><div class="dept-bar" style="width:{d["sales"]/mx*100:.0f}%"></div></div>'
                f'<div class="dept-val">{fmt_euro(d["sales"])}</div>'
                f'</div>'
                for i, d in enumerate(depts[:12])
            )
            st.markdown(
                f'<div style="background:#475569;border:1px solid #64748b;border-radius:10px;padding:.5rem 1rem 0;">{rows}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="color:#cbd5e1;font-size:.82rem;padding:1rem;">Δεν υπάρχουν δεδομένα τμημάτων.</div>', unsafe_allow_html=True)
    except: pass

# ════════════════════════════════════════
# TAB 2 – ΤΑΣΕΙΣ
# ════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-header"><span>▍</span> Εξέλιξη Πωλήσεων</div>', unsafe_allow_html=True)
    period_opt = st.radio("", ["30 ημέρες","90 ημέρες","Όλο το έτος"],
                          horizontal=True, label_visibility="collapsed")
    today = date.today()
    since = (today - timedelta(days=30 if "30" in period_opt else 90)
             if "έτος" not in period_opt else date(today.year, 1, 1))

    ch = df[df['date'] >= since].sort_values('date').copy()
    ch['label'] = ch['date'].apply(lambda d: d.strftime('%d/%m'))

    if not ch.empty:
        st.markdown("**Ημερήσιες Πωλήσεις (€)**")
        st.bar_chart(ch.set_index('label')['netday'], color="#10b981", use_container_width=True, height=220)
        st.markdown("**Αριθμός Πελατών**")
        st.bar_chart(ch.set_index('label')['customers'], color="#3b82f6", use_container_width=True, height=180)

        s = period_stats(df, since, today)
        st.markdown('<div class="sec-header"><span>▍</span> Περίληψη</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);">
          <div class="kpi-card" style="--accent:#10b981"><div class="kpi-label">Σύνολο Πωλήσεων</div><div class="kpi-value" style="font-size:1.3rem;">{fmt_euro(s['total'])}</div></div>
          <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Μ.Ό. Ημέρας</div><div class="kpi-value" style="font-size:1.3rem;">{fmt_euro(s['avg_day'])}</div></div>
          <div class="kpi-card" style="--accent:#f59e0b"><div class="kpi-label">Κορυφή ({s['peak'].strftime('%d/%m') if s['peak'] else '—'})</div><div class="kpi-value" style="font-size:1.3rem;">{fmt_euro(s['peak_val'])}</div></div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Δεν υπάρχουν δεδομένα για αυτή την περίοδο.")

# ════════════════════════════════════════
# TAB 3 – ΣΥΓΚΡΙΣΕΙΣ
# ════════════════════════════════════════
with tab3:
    today = date.today()

    def cmp_table(title_a, title_b, s_a, s_b):
        def row(label, a, b, euro=True):
            fmt = fmt_euro if euro else lambda v: f"{v:.0f}"
            if b == 0: pct_h = "<span style='color:#cbd5e1'>—</span>"
            else:
                pct = (a-b)/b*100
                clr = "#34d399" if pct >= 0 else "#fb7185"
                pct_h = f'<span style="color:{clr}">{"▲" if pct>=0 else "▼"} {abs(pct):.1f}%</span>'
            return (f'<tr style="border-bottom:1px solid #64748b;">'
                    f'<td style="padding:.6rem .4rem;font-size:.82rem;color:#f1f5f9;">{label}</td>'
                    f'<td style="padding:.6rem .8rem;font-family:DM Mono;font-size:.82rem;color:#ffffff;text-align:right;">{fmt(a)}</td>'
                    f'<td style="padding:.6rem .8rem;font-family:DM Mono;font-size:.82rem;color:#cbd5e1;text-align:right;">{fmt(b)}</td>'
                    f'<td style="padding:.6rem .8rem;text-align:right;font-size:.82rem;">{pct_h}</td></tr>')
        th = (f'<tr style="background:#334155;">'
              f'<th style="padding:.7rem .4rem;font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#f8fafc;text-align:left;"></th>'
              f'<th style="padding:.7rem .8rem;font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#10b981;text-align:right;">{title_a}</th>'
              f'<th style="padding:.7rem .8rem;font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#f8fafc;text-align:right;">{title_b}</th>'
              f'<th style="padding:.7rem .8rem;font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#f8fafc;text-align:right;">Μεταβολή</th></tr>')
        body = (row("Σύνολο Πωλήσεων", s_a['total'],    s_b['total'])
              + row("Μ.Ό. Ημέρας",     s_a['avg_day'],  s_b['avg_day'])
              + row("Μ.Ό. Πελατών",    s_a['avg_cus'],  s_b['avg_cus'],  euro=False)
              + row("Ημέρες",           s_a['days'],     s_b['days'],     euro=False)
              + row("Κορυφαία Μέρα",   s_a['peak_val'], s_b['peak_val']))
        return (f'<table style="width:100%;border-collapse:collapse;background:#475569;'
                f'border:1px solid #64748b;border-radius:10px;overflow:hidden;">'
                f'<thead>{th}</thead><tbody>{body}</tbody></table>')

    st.markdown('<div class="sec-header"><span>▍</span> Μηνιαία Σύγκριση</div>', unsafe_allow_html=True)
    cur_ms  = date(today.year, today.month, 1)
    prev_me = cur_ms - timedelta(days=1)
    prev_ms = date(prev_me.year, prev_me.month, 1)
    st.markdown(cmp_table(
        MONTHS_GR[today.month-1], MONTHS_GR[prev_me.month-1],
        period_stats(df, cur_ms, today), period_stats(df, prev_ms, prev_me)
    ), unsafe_allow_html=True)

    st.markdown('<div class="sec-header"><span>▍</span> Εβδομαδιαία Σύγκριση</div>', unsafe_allow_html=True)
    ws  = today - timedelta(days=today.weekday())
    pws = ws - timedelta(days=7)
    st.markdown(cmp_table(
        "Τρέχουσα Εβδ.", "Προηγούμενη",
        period_stats(df, ws, today), period_stats(df, pws, ws - timedelta(days=1))
    ), unsafe_allow_html=True)

# ════════════════════════════════════════
# TAB 4 – ΙΣΤΟΡΙΚΟ & ΦΙΛΤΡΑ
# ════════════════════════════════════════
with tab4:
    st.markdown('<div class="sec-header"><span>▍</span> Ιστορικό & Αναζήτηση</div>', unsafe_allow_html=True)
    
    # --- ΝΕΑ ΦΙΛΤΡΑ ΠΟΥ ΖΗΤΗΣΕΣ ---
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        if not df.empty:
            min_d = df['date'].min()
            max_d = df['date'].max()
            date_range = st.date_input("🗓️ Επιλογή Διαστήματος (Από - Έως):", value=[min_d, max_d], min_value=min_d, max_value=max_d)
        else:
            date_range = []
            
    with f_col2:
        group_by = st.selectbox("📊 Ομαδοποίηση Πωλήσεων ανά:", ["Ημέρα", "Εβδομάδα", "Μήνα"])

    # Εφαρμογή Φίλτρου Ημερομηνιών
    disp_df = df.copy()
    if len(date_range) == 2:
        disp_df = disp_df[(disp_df['date'] >= date_range[0]) & (disp_df['date'] <= date_range[1])]
    elif len(date_range) == 1:
        disp_df = disp_df[disp_df['date'] == date_range[0]]

    # Εφαρμογή Ομαδοποίησης
    if disp_df.empty:
        st.info("Δεν βρέθηκαν δεδομένα για αυτό το διάστημα.")
    else:
        if group_by == "Ημέρα":
            disp = disp_df[['date','netday','customers','avg_basket']].copy()
            disp['date']       = disp['date'].apply(lambda d: d.strftime('%d/%m/%Y'))
            disp['netday']     = disp['netday'].apply(fmt_euro)
            disp['avg_basket'] = disp['avg_basket'].apply(fmt_euro)
            disp['customers']  = disp['customers'].apply(lambda v: f"{int(v)}" if pd.notna(v) else "—")
            disp.columns       = ['Ημερομηνία','Πωλήσεις','Πελάτες','Μ.Ό. Καλαθιού']
        
        elif group_by == "Εβδομάδα":
            disp_df['week'] = pd.to_datetime(disp_df['date']).dt.to_period('W').apply(lambda r: f"{r.start_time.strftime('%d/%m/%Y')} έως {r.end_time.strftime('%d/%m/%Y')}")
            disp = disp_df.groupby('week').agg({'netday':'sum', 'customers':'sum'}).reset_index()
            disp['avg_basket'] = disp['netday'] / disp['customers']
            disp['netday']     = disp['netday'].apply(fmt_euro)
            disp['avg_basket'] = disp['avg_basket'].apply(fmt_euro)
            disp['customers']  = disp['customers'].apply(lambda v: f"{int(v)}" if pd.notna(v) else "—")
            disp.columns       = ['Εβδομάδα','Σύνολο Πωλήσεων','Σύνολο Πελατών','Μ.Ό. Καλαθιού']
            
        elif group_by == "Μήνα":
            disp_df['month'] = pd.to_datetime(disp_df['date']).dt.strftime('%m/%Y')
            disp = disp_df.groupby('month').agg({'netday':'sum', 'customers':'sum'}).reset_index()
            disp['avg_basket'] = disp['netday'] / disp['customers']
            disp['netday']     = disp['netday'].apply(fmt_euro)
            disp['avg_basket'] = disp['avg_basket'].apply(fmt_euro)
            disp['customers']  = disp['customers'].apply(lambda v: f"{int(v)}" if pd.notna(v) else "—")
            disp.columns       = ['Μήνας','Σύνολο Πωλήσεων','Σύνολο Πελατών','Μ.Ό. Καλαθιού']

        st.dataframe(disp, use_container_width=True, hide_index=True, height=450)
        csv = disp.to_csv(index=False).encode('utf-8')
        st.download_button("↓  Εξαγωγή CSV (Βάσει Φίλτρου)", csv, f"ab_skyros_history.csv", "text/csv")
