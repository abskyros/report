"""
Κοινές συναρτήσεις και σταθερές για όλες τις σελίδες.
"""
import re, json, os
import pandas as pd
from datetime import date, datetime
import pytesseract
from pdf2image import convert_from_bytes

# ── Σταθερές ──────────────────────────────────────────────
HISTORY_FILE = "sales_history.csv"

DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

# ── Μορφοποίηση ───────────────────────────────────────────
def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

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
    diff = now - prev; pct = diff / prev * 100
    sign = "▲" if diff >= 0 else "▼"
    cls  = "delta-up" if diff >= 0 else "delta-down"
    val  = fmt_euro(abs(diff)) if is_euro else f"{abs(diff):.0f}"
    return f'<div class="kpi-delta {cls}">{sign} {val} ({pct:+.1f}%)</div>'

# ── Sales History CSV ─────────────────────────────────────
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

# ── OCR ───────────────────────────────────────────────────
_FUZZY = {
    'NetDaySalDis': r'Net\s*Day\s*Sa[li1]Dis',
    'NumOfCus':     r'Num\s*Of\s*Cus',
    'AvgSalCus':    r'Avg\s*Sa[li1]\s*Cus',
}

def ocr_page(img) -> str:
    return pytesseract.image_to_string(img, lang='ell+eng')

def find_value(text: str, label: str):
    pattern = _FUZZY.get(label, re.escape(label))
    idx = re.search(pattern, text, re.IGNORECASE)
    if not idx: return None
    snippet = text[idx.end(): idx.end() + 60]
    n = re.search(r'([\d][\d\.,]*)', snippet)
    return n.group(1) if n else None

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    import streamlit as st
    result = {'date': None, 'netday': None, 'customers': None, 'avg_basket': None, 'depts': '[]'}
    try:
        images = convert_from_bytes(pdf_bytes, dpi=180, fmt='jpeg')
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

        dept_text = p1 + ("\n" + ocr_page(images[1]) if len(images) > 1 else "")
        dept_pat  = re.compile(
            r'(\d{3})\s+([Α-ΩA-Zα-ωa-z][Α-ΩA-Zα-ωa-z\s\-\.\/&]{2,28}?)\s+'
            r'([\d\.,]+)\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+'
        )
        depts, seen = [], set()
        for m in dept_pat.finditer(dept_text):
            net = parse_num(m.group(4)); nm = m.group(2).strip()
            if net > 0.5 and nm not in seen:
                depts.append({'code': m.group(1), 'name': nm, 'sales': net}); seen.add(nm)
        result['depts'] = json.dumps(sorted(depts, key=lambda x: x['sales'], reverse=True), ensure_ascii=False)
    except Exception as e:
        st.warning(f"OCR: {e}")
    return result

# ── Period stats ──────────────────────────────────────────
def period_stats(df, start, end):
    sub = df[(df['date'] >= start) & (df['date'] <= end)]
    if sub.empty: return {'total':0,'avg_day':0,'avg_cus':0,'days':0,'peak':None,'peak_val':0}
    return {'total': sub['netday'].sum(), 'avg_day': sub['netday'].mean(),
            'avg_cus': sub['customers'].mean() if 'customers' in sub else 0,
            'days': len(sub), 'peak': sub.loc[sub['netday'].idxmax(),'date'],
            'peak_val': sub['netday'].max()}

# ── CSS (κοινό για όλες τις σελίδες) ─────────────────────
COMMON_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#0a0e1a;color:#e2e8f0;}
section[data-testid="stSidebar"]{background:#080c16!important;border-right:1px solid #1e2d45!important;}
section[data-testid="stSidebar"] *{color:#94a3b8!important;}
section[data-testid="stSidebar"] .stButton>button{background:#1e293b!important;color:#e2e8f0!important;border:1px solid #1e2d45!important;width:100%;text-align:left!important;}
section[data-testid="stSidebar"] .stButton>button:hover{background:#10b981!important;color:#0a0e1a!important;border-color:#10b981!important;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:2rem 2.5rem 4rem;max-width:1400px;}

.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0;}
.kpi-grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin:1.5rem 0;}
.kpi-grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem;margin:1.5rem 0;}
.kpi-card{background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:1.4rem 1.6rem;position:relative;overflow:hidden;transition:border-color .2s;}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent,#10b981);}
.kpi-card:hover{border-color:#2d4a6e;}
.kpi-label{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748b;margin-bottom:.5rem;}
.kpi-value{font-family:'DM Mono',monospace;font-size:1.75rem;font-weight:500;color:#f1f5f9;line-height:1;}
.kpi-value-sm{font-family:'DM Mono',monospace;font-size:1.3rem;font-weight:500;color:#f1f5f9;line-height:1;}
.kpi-delta{font-size:.78rem;margin-top:.5rem;font-weight:500;}
.delta-up{color:#10b981;} .delta-down{color:#f43f5e;}

.sec-header{display:flex;align-items:center;gap:.6rem;font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#475569;border-bottom:1px solid #1e2d45;padding-bottom:.6rem;margin:2rem 0 1rem;}
.sec-header span{color:#10b981;}

.nav-card{background:#111827;border:1px solid #1e2d45;border-radius:16px;padding:2rem;cursor:pointer;transition:all .2s;text-decoration:none;display:block;}
.nav-card:hover{border-color:#10b981;background:#0f1f2e;transform:translateY(-2px);}
.nav-card .icon{font-size:2.5rem;margin-bottom:1rem;}
.nav-card .title{font-size:1.1rem;font-weight:700;color:#f1f5f9;margin-bottom:.4rem;}
.nav-card .desc{font-size:.8rem;color:#475569;line-height:1.5;}
.nav-card .badge{display:inline-block;background:#10b981;color:#0a0e1a;font-size:.65rem;font-weight:700;padding:.2rem .5rem;border-radius:4px;margin-top:.8rem;letter-spacing:.05em;text-transform:uppercase;}

.dept-row{display:flex;align-items:center;gap:.8rem;padding:.55rem .2rem;border-bottom:1px solid #111827;}
.dept-rank{font-family:'DM Mono';font-size:.7rem;color:#334155;width:1.4rem;text-align:right;flex-shrink:0;}
.dept-name{flex:1;font-size:.82rem;color:#cbd5e1;}
.dept-bar-wrap{width:120px;height:4px;background:#1e293b;border-radius:2px;flex-shrink:0;}
.dept-bar{height:100%;border-radius:2px;background:#10b981;}
.dept-val{font-family:'DM Mono';font-size:.78rem;color:#94a3b8;width:6rem;text-align:right;flex-shrink:0;}

.divider-module{border:none;border-top:1px solid #1e2d45;margin:2.5rem 0;}

[data-baseweb="tab-list"]{gap:.5rem;background:transparent;border-bottom:1px solid #1e2d45;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#475569!important;font-size:.8rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:.6rem 1.2rem!important;border-radius:6px 6px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#10b981!important;background:#0f1f2e!important;border-bottom:2px solid #10b981!important;}

.stButton>button{background:#10b981!important;color:#0a0e1a!important;border:none!important;border-radius:8px!important;font-weight:700!important;font-size:.82rem!important;padding:.55rem 1.4rem!important;}
.stButton>button:hover{background:#059669!important;}
button[kind="secondary"]{background:#1e293b!important;color:#94a3b8!important;border:1px solid #1e2d45!important;}
button[kind="secondary"]:hover{background:#273549!important;}

[data-testid="stDataFrame"]{border:1px solid #1e2d45;border-radius:10px;overflow:hidden;}
[data-baseweb="select"]>div{background:#111827!important;border-color:#1e2d45!important;color:#e2e8f0!important;}
[data-baseweb="input"]>div{background:#111827!important;border-color:#1e2d45!important;color:#e2e8f0!important;}
[data-testid="stAlert"]{background:#0f1f2e;border-color:#1e2d45;color:#94a3b8;}
.stSpinner>div{border-top-color:#10b981!important;}
details{background:#111827;border:1px solid #1e2d45!important;border-radius:10px!important;}

.stale-banner{background:#1a1a0a;border:1px solid #f59e0b;border-radius:10px;padding:.8rem 1.2rem;margin:.8rem 0;font-size:.82rem;color:#f59e0b;}
.ok-banner{background:#0a1a12;border:1px solid #10b981;border-radius:10px;padding:.8rem 1.2rem;margin:.8rem 0;font-size:.82rem;color:#10b981;}
</style>
"""
