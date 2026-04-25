"""Κοινές συναρτήσεις για όλες τις σελίδες."""
import re, json, os, io
import pandas as pd
from datetime import date, datetime
import pytesseract
from pdf2image import convert_from_bytes

HISTORY_FILE = "sales_history.csv"

DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

# ── Μορφοποίηση ───────────────────────────────────────────────────────────────
def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

def parse_num(s: str) -> float:
    if not s: return 0.0
    s = re.sub(r"[^\d,\.]", "", s)
    if "." in s and "," in s:
        s = s.replace(".","").replace(",",".") if s.index(".") < s.index(",") else s.replace(",","")
    elif "," in s:
        s = s.replace(",",".")
    try:    return float(s)
    except: return 0.0

def delta_html(now, prev, is_euro=True):
    if not prev or prev == 0: return ""
    diff = now - prev
    pct  = diff / prev * 100
    sign = "+" if diff >= 0 else ""
    cls  = "delta-pos" if diff >= 0 else "delta-neg"
    val  = fmt_euro(abs(diff)) if is_euro else f"{abs(diff):.0f}"
    return f'<span class="kpi-delta {cls}">{sign}{pct:.1f}%&nbsp;&nbsp;{val}</span>'

# ── CSV History ───────────────────────────────────────────────────────────────
def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        if "depts" not in df.columns:
            df["depts"] = "[]"
        return df.sort_values("date", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","netday","customers","avg_basket","depts"])

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_FILE, index=False)

def upsert(df: pd.DataFrame, record: dict) -> pd.DataFrame:
    mask = df["date"] == record["date"]
    if mask.any():
        for k, v in record.items():
            if v is not None: df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    return df.sort_values("date", ascending=False).reset_index(drop=True)

def period_stats(df, start, end):
    sub = df[(df["date"] >= start) & (df["date"] <= end)]
    if sub.empty:
        return {"total":0,"avg_day":0,"avg_cus":0,"days":0,"peak":None,"peak_val":0}
    return {
        "total":    sub["netday"].sum(),
        "avg_day":  sub["netday"].mean(),
        "avg_cus":  sub["customers"].mean() if "customers" in sub else 0,
        "days":     len(sub),
        "peak":     sub.loc[sub["netday"].idxmax(),"date"],
        "peak_val": sub["netday"].max(),
    }

# ── OCR ───────────────────────────────────────────────────────────────────────
_FUZZY = {
    "NetDaySalDis": r"Net\s*Day\s*Sa[li1]Dis",
    "NumOfCus":     r"Num\s*Of\s*Cus",
    "AvgSalCus":    r"Avg\s*Sa[li1]\s*Cus",
}

def ocr_page(img) -> str:
    return pytesseract.image_to_string(img, lang="ell+eng")

def find_value(text: str, label: str):
    pat = _FUZZY.get(label, re.escape(label))
    idx = re.search(pat, text, re.IGNORECASE)
    if not idx: return None
    snippet = text[idx.end(): idx.end()+60]
    n = re.search(r"([\d][\d\.,]*)", snippet)
    return n.group(1) if n else None

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {"date": None, "netday": None, "customers": None,
              "avg_basket": None, "depts": "[]"}
    try:
        images = convert_from_bytes(pdf_bytes, dpi=180, fmt="jpeg")
        p1 = ocr_page(images[0])

        m = re.search(r"For\s+(\d{2}/\d{2}/\d{4})", p1) or \
            re.search(r"(\d{2}/\d{2}/\d{4})", p1)
        if m:
            try: result["date"] = datetime.strptime(m.group(1), "%d/%m/%Y").date()
            except: pass

        raw = find_value(p1, "NetDaySalDis")
        if raw: result["netday"] = parse_num(raw)

        raw = find_value(p1, "NumOfCus")
        if raw:
            try: result["customers"] = int(parse_num(raw))
            except: pass

        raw = find_value(p1, "AvgSalCus")
        if raw: result["avg_basket"] = parse_num(raw)

        dept_text = p1 + ("\n" + ocr_page(images[1]) if len(images) > 1 else "")
        dept_pat  = re.compile(
            r"(\d{3})\s+([Α-ΩA-Zα-ωa-z][Α-ΩA-Zα-ωa-z\s\-\.\/&]{2,28}?)\s+"
            r"([\d\.,]+)\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+"
        )
        depts, seen = [], set()
        for m in dept_pat.finditer(dept_text):
            net = parse_num(m.group(4))
            nm  = m.group(2).strip()
            if net > 0.5 and nm not in seen:
                depts.append({"code": m.group(1), "name": nm, "sales": net})
                seen.add(nm)
        result["depts"] = json.dumps(
            sorted(depts, key=lambda x: x["sales"], reverse=True),
            ensure_ascii=False
        )
    except Exception as e:
        import streamlit as st
        st.warning(f"OCR: {e}")
    return result

# ── Invoices ──────────────────────────────────────────────────────────────────
def find_header_and_load(file_content: bytes, filename: str):
    try:
        if filename.lower().endswith((".xlsx",".xls")):
            df_raw = pd.read_excel(io.BytesIO(file_content), header=None)
        else:
            try:
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None,
                                     sep=None, engine="python")
            except:
                df_raw = pd.read_csv(io.BytesIO(file_content), header=None,
                                     encoding="cp1253", sep=None, engine="python")
        hi = -1
        for i in range(min(40, len(df_raw))):
            row_str = " ".join(str(x).upper() for x in df_raw.iloc[i].values if pd.notna(x))
            if "ΤΥΠΟΣ" in row_str and "ΗΜΕΡΟΜΗΝΙΑ" in row_str:
                hi = i; break
        if hi == -1: return None
        df = df_raw.iloc[hi+1:].copy()
        df.columns = [str(h).strip().upper() for h in df_raw.iloc[hi]]
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, ~df.columns.str.contains("NAN|UNNAMED", case=False)]
        return df.reset_index(drop=True)
    except:
        return None

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

* { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Base ── */
.stApp { background: #f0f2f5; color: #1a1f2e; }
.block-container { padding: 1.5rem 1.5rem 4rem; max-width: 1280px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #1a1f2e !important;
    border-right: 1px solid #2d3548 !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown div { color: #8892a4 !important; }
section[data-testid="stSidebar"] a {
    display: block; padding: .55rem .9rem; border-radius: 7px;
    color: #8892a4 !important; font-size: .82rem; font-weight: 500;
    text-decoration: none; transition: all .15s; margin-bottom: 2px;
}
section[data-testid="stSidebar"] a:hover { background: #252b3b; color: #e2e8f0 !important; }
section[data-testid="stSidebar"] a[aria-current="page"] {
    background: #1e3a5f; color: #60a5fa !important; font-weight: 600;
}

/* ── Hide chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Page title bar ── */
.page-header {
    background: #1a1f2e;
    border-radius: 12px;
    padding: 1.4rem 1.8rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.page-header-left .eyebrow {
    font-size: .65rem; font-weight: 700; letter-spacing: .14em;
    text-transform: uppercase; color: #60a5fa; margin-bottom: .25rem;
}
.page-header-left h1 {
    font-size: 1.5rem; font-weight: 700; color: #f8fafc;
    margin: 0; letter-spacing: -.02em;
}
.page-header-right { text-align: right; }
.page-header-right .ts-label { font-size: .65rem; color: #4b5563; }
.page-header-right .ts-val { font-family: 'JetBrains Mono'; font-size: .75rem; color: #6b7280; }

/* ── Nav cards ── */
.nav-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
@media (max-width: 640px) { .nav-grid { grid-template-columns: 1fr; } }
.nav-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
    transition: all .18s;
}
.nav-card::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: var(--stripe, #2563eb);
}
.nav-card:hover { border-color: #bfdbfe; box-shadow: 0 4px 16px rgba(37,99,235,.08); transform: translateY(-1px); }
.nav-card .nc-module { font-size: .62rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--stripe,#2563eb); margin-bottom: .5rem; }
.nav-card .nc-title { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: .4rem; }
.nav-card .nc-desc { font-size: .78rem; color: #64748b; line-height: 1.55; }
.nav-card .nc-tags { margin-top: .9rem; display: flex; gap: .4rem; flex-wrap: wrap; }
.nc-tag { font-size: .62rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
           padding: .2rem .55rem; border-radius: 4px; background: #eff6ff; color: #1d4ed8; }

/* ── KPI cards ── */
.kpi-row { display: grid; gap: .9rem; margin: 1rem 0; }
.kpi-row-4 { grid-template-columns: repeat(4, 1fr); }
.kpi-row-3 { grid-template-columns: repeat(3, 1fr); }
.kpi-row-2 { grid-template-columns: repeat(2, 1fr); }
@media (max-width: 900px) { .kpi-row-4 { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 600px) { .kpi-row-4, .kpi-row-3, .kpi-row-2 { grid-template-columns: 1fr; } }

.kpi {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    position: relative;
    overflow: hidden;
}
.kpi::before {
    content: '';
    position: absolute; top: 0; left: 0; bottom: 0; width: 3px;
    background: var(--a, #2563eb);
}
.kpi-lbl { font-size: .67rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #94a3b8; margin-bottom: .45rem; }
.kpi-val { font-family: 'JetBrains Mono'; font-size: 1.55rem; font-weight: 500; color: #0f172a; line-height: 1; }
.kpi-val-sm { font-family: 'JetBrains Mono'; font-size: 1.15rem; font-weight: 500; color: #0f172a; line-height: 1; }
.kpi-delta { display: block; font-size: .72rem; margin-top: .45rem; font-weight: 500; }
.delta-pos { color: #059669; }
.delta-neg { color: #dc2626; }

/* ── Section header ── */
.sec-hdr {
    font-size: .67rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    color: #94a3b8; border-bottom: 1px solid #e2e8f0;
    padding-bottom: .5rem; margin: 1.8rem 0 .9rem;
}

/* ── Dept table ── */
.dept-list { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.dept-row { display: flex; align-items: center; gap: .7rem; padding: .55rem 1rem; border-bottom: 1px solid #f1f5f9; }
.dept-row:last-child { border-bottom: none; }
.dept-rank { font-family: 'JetBrains Mono'; font-size: .68rem; color: #cbd5e1; width: 1.2rem; text-align: right; flex-shrink: 0; }
.dept-name { flex: 1; font-size: .8rem; color: #334155; }
.dept-bar-bg { width: 100px; height: 3px; background: #f1f5f9; border-radius: 2px; flex-shrink: 0; }
.dept-bar-fill { height: 100%; border-radius: 2px; background: #2563eb; }
.dept-val { font-family: 'JetBrains Mono'; font-size: .76rem; color: #64748b; width: 5.5rem; text-align: right; flex-shrink: 0; }

/* ── Comparison table ── */
.cmp-table { width: 100%; border-collapse: collapse; background: #fff;
             border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.cmp-table thead tr { background: #f8fafc; }
.cmp-table th { padding: .65rem .9rem; font-size: .67rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; text-align: right; }
.cmp-table th:first-child { text-align: left; }
.cmp-table td { padding: .6rem .9rem; font-size: .8rem; color: #334155; text-align: right; border-bottom: 1px solid #f1f5f9; font-family: 'JetBrains Mono'; }
.cmp-table td:first-child { font-family: 'Inter'; color: #64748b; text-align: left; }
.cmp-table tr:last-child td { border-bottom: none; }
.th-cur { color: #1d4ed8 !important; }
.cmp-pos { color: #059669; font-weight: 600; }
.cmp-neg { color: #dc2626; font-weight: 600; }

/* ── Status banners ── */
.banner { border-radius: 8px; padding: .7rem 1.1rem; font-size: .8rem; font-weight: 500; margin: .7rem 0; display: flex; align-items: center; gap: .5rem; }
.banner-ok   { background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }
.banner-warn { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
.banner-info { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }

/* ── Tabs ── */
[data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #e2e8f0; gap: .2rem; }
[data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    color: #94a3b8 !important; font-size: .78rem; font-weight: 600;
    letter-spacing: .04em; text-transform: uppercase;
    padding: .55rem 1.1rem !important; border-radius: 6px 6px 0 0 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #1d4ed8 !important; background: #eff6ff !important;
    border-bottom: 2px solid #2563eb !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #2563eb !important; color: #fff !important;
    border: none !important; border-radius: 7px !important;
    font-weight: 600 !important; font-size: .8rem !important;
    padding: .5rem 1.2rem !important; letter-spacing: .02em;
    transition: background .15s !important;
}
.stButton > button:hover { background: #1d4ed8 !important; }
button[kind="secondary"] {
    background: #fff !important; color: #374151 !important;
    border: 1px solid #d1d5db !important;
}
button[kind="secondary"]:hover { background: #f9fafb !important; }

/* ── Inputs ── */
[data-baseweb="select"] > div { background: #fff !important; border-color: #d1d5db !important; }
[data-testid="stDateInput"] input { background: #fff !important; }
[data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }

/* ── Divider ── */
.divider { border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }

/* ── Charts ── */
[data-testid="stVegaLiteChart"] { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; }
</style>
"""
