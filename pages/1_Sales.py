import streamlit as st
import pandas as pd
import os, re, json, unicodedata, traceback
from imap_tools import MailBox, AND
from datetime import datetime, date, timedelta
from pdf2image import convert_from_bytes
import pytesseract

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sales Analytics — AB Skyros",
                   layout="wide", page_icon=None, initial_sidebar_state="expanded")

HISTORY_FILE  = "sales_history.csv"
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_FROM    = "abf.skyros@gmail.com"
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"
MONTHS_GR = ["Ιανουαριος","Φεβρουαριος","Μαρτιος","Απριλιος","Μαιος","Ιουνιος",
              "Ιουλιος","Αυγουστος","Σεπτεμβριος","Οκτωβριος","Νοεμβριος","Δεκεμβριος"]
DAYS_GR   = ["Δευτερα","Τριτη","Τεταρτη","Πεμπτη","Παρασκευη","Σαββατο","Κυριακη"]

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#f0f2f5;}
.block-container{padding:1.4rem 1.6rem 4rem;max-width:1240px;}
section[data-testid="stSidebar"]{background:#0f172a!important;border-right:1px solid #1e293b!important;min-width:210px!important;max-width:210px!important;}
section[data-testid="stSidebar"] *{color:#64748b!important;}
section[data-testid="stSidebar"] a{display:block;padding:.5rem .85rem;border-radius:6px;color:#64748b!important;font-size:.8rem;font-weight:500;text-decoration:none;transition:all .15s;margin-bottom:2px;}
section[data-testid="stSidebar"] a:hover{background:#1e293b;color:#e2e8f0!important;}
section[data-testid="stSidebar"] a[aria-current="page"]{background:#1e3a5f;color:#60a5fa!important;font-weight:600;}
#MainMenu,footer,header{visibility:hidden;}
.ph{background:#0f172a;border-radius:10px;padding:1.3rem 1.6rem;margin-bottom:1.4rem;display:flex;align-items:center;justify-content:space-between;}
.ph-ey{font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.2rem;}
.ph-h1{font-size:1.5rem;font-weight:700;color:#f8fafc;margin:0;}
.ph-rt{text-align:right;} .ph-lbl{font-size:.62rem;color:#475569;} .ph-val{font-family:'JetBrains Mono';font-size:.73rem;color:#64748b;}
.kr{display:grid;gap:.85rem;margin:.9rem 0;}
.kr4{grid-template-columns:repeat(4,1fr);} .kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:880px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr4,.kr3{grid-template-columns:1fr;}}
.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:1rem 1.2rem;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#2563eb);}
.kl{font-size:.64rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:.4rem;}
.kv{font-family:'JetBrains Mono';font-size:1.45rem;font-weight:500;color:#0f172a;line-height:1.1;}
.kv-sm{font-family:'JetBrains Mono';font-size:1.1rem;font-weight:500;color:#0f172a;line-height:1.1;}
.sh{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;padding-bottom:.45rem;margin:1.6rem 0 .8rem;}
.bn{border-radius:7px;padding:.65rem 1rem;font-size:.78rem;font-weight:500;margin:.6rem 0;}
.bn-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;}
.bn-warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;}
.bn-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;}
.dl{background:#fff;border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;}
.dr{display:flex;align-items:center;gap:.7rem;padding:.5rem .9rem;border-bottom:1px solid #f1f5f9;}
.dr:last-child{border-bottom:none;}
.drk{font-family:'JetBrains Mono';font-size:.67rem;color:#cbd5e1;width:1.2rem;text-align:right;flex-shrink:0;}
.dn{flex:1;font-size:.78rem;color:#334155;}
.dbb{width:95px;height:3px;background:#f1f5f9;border-radius:2px;flex-shrink:0;}
.dbf{height:100%;border-radius:2px;background:#2563eb;}
.dv{font-family:'JetBrains Mono';font-size:.74rem;color:#64748b;width:5rem;text-align:right;flex-shrink:0;}
.ct{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;}
.ct thead tr{background:#f8fafc;}
.ct th{padding:.6rem .85rem;font-size:.64rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#94a3b8;text-align:right;}
.ct th:first-child{text-align:left;}
.ct td{padding:.55rem .85rem;font-size:.78rem;color:#334155;text-align:right;border-bottom:1px solid #f1f5f9;font-family:'JetBrains Mono';}
.ct td:first-child{font-family:'Inter';color:#64748b;text-align:left;}
.ct tr:last-child td{border-bottom:none;}
.cp{color:#059669;font-weight:600;} .cn{color:#dc2626;font-weight:600;} .cth{color:#1d4ed8!important;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #e2e8f0;gap:.2rem;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#94a3b8!important;font-size:.75rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:.5rem 1rem!important;border-radius:6px 6px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#1d4ed8!important;background:#eff6ff!important;border-bottom:2px solid #2563eb!important;}
.stButton>button{background:#2563eb!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.48rem 1.1rem!important;}
.stButton>button:hover{background:#1d4ed8!important;}
button[kind="secondary"]{background:#fff!important;color:#374151!important;border:1px solid #d1d5db!important;}
[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;}
[data-baseweb="select"]>div{background:#fff!important;border-color:#d1d5db!important;}
.stSpinner>div{border-top-color:#2563eb!important;}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.1rem 0 1.2rem;">
      <div style="font-size:.6rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.25rem;">AB SKYROS 1082</div>
      <div style="font-size:.95rem;font-weight:700;color:#f1f5f9;margin-bottom:1.4rem;">Business Hub</div>
      <div style="font-size:.58rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#374151;margin-bottom:.4rem;padding-left:.85rem;">NAVIGATION</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("Home.py",             label="Home")
    st.page_link("pages/1_Sales.py",    label="Sales Analytics")
    st.page_link("pages/2_Invoices.py", label="Invoices")

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

def parse_num(s):
    if not s: return 0.0
    s = re.sub(r"[^\d,\.]","",s)
    if "." in s and "," in s:
        s = s.replace(".","").replace(",",".") if s.index(".")<s.index(",") else s.replace(",","")
    elif "," in s: s = s.replace(",",".")
    try: return float(s)
    except: return 0.0

def delta_html(now, prev, euro=True):
    if not prev or prev == 0: return ""
    diff = now - prev; pct = diff/prev*100
    col = "#059669" if diff>=0 else "#dc2626"
    return f'<div style="font-size:.7rem;color:{col};margin-top:.35rem;">{"+" if diff>=0 else ""}{pct:.1f}%</div>'

def load_history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty: df["date"] = pd.to_datetime(df["date"]).dt.date
        if "depts" not in df.columns: df["depts"] = "[]"
        return df.sort_values("date",ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","netday","customers","avg_basket","depts"])

def save_history(df): df.to_csv(HISTORY_FILE, index=False)

def upsert(df, record):
    mask = df["date"] == record["date"]
    if mask.any():
        for k,v in record.items():
            if v is not None: df.loc[mask,k] = v
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    return df.sort_values("date",ascending=False).reset_index(drop=True)

def period_stats(df, start, end):
    sub = df[(df["date"]>=start)&(df["date"]<=end)]
    if sub.empty: return {"total":0,"avg_day":0,"avg_cus":0,"days":0,"peak":None,"peak_val":0}
    return {"total":sub["netday"].sum(),"avg_day":sub["netday"].mean(),
            "avg_cus":sub["customers"].mean() if "customers" in sub else 0,
            "days":len(sub),"peak":sub.loc[sub["netday"].idxmax(),"date"],
            "peak_val":sub["netday"].max()}

# ─── OCR ────────────────────────────────────────────────────────────────────────
_FUZZY = {"NetDaySalDis":r"Net\s*Day\s*Sa[li1]Dis",
          "NumOfCus":r"Num\s*Of\s*Cus","AvgSalCus":r"Avg\s*Sa[li1]\s*Cus"}

def ocr_page(img): return pytesseract.image_to_string(img, lang="ell+eng")

def find_val(text, label):
    pat = _FUZZY.get(label, re.escape(label))
    idx = re.search(pat, text, re.IGNORECASE)
    if not idx: return None
    n = re.search(r"([\d][\d\.,]*)", text[idx.end():idx.end()+60])
    return n.group(1) if n else None

def extract_pdf(pdf_bytes):
    r = {"date":None,"netday":None,"customers":None,"avg_basket":None,"depts":"[]"}
    try:
        imgs = convert_from_bytes(pdf_bytes, dpi=180, fmt="jpeg")
        p1 = ocr_page(imgs[0])
        m = re.search(r"For\s+(\d{2}/\d{2}/\d{4})",p1) or re.search(r"(\d{2}/\d{2}/\d{4})",p1)
        if m:
            try: r["date"] = datetime.strptime(m.group(1),"%d/%m/%Y").date()
            except: pass
        raw = find_val(p1,"NetDaySalDis")
        if raw: r["netday"] = parse_num(raw)
        raw = find_val(p1,"NumOfCus")
        if raw:
            try: r["customers"] = int(parse_num(raw))
            except: pass
        raw = find_val(p1,"AvgSalCus")
        if raw: r["avg_basket"] = parse_num(raw)
        dt = p1 + ("\n"+ocr_page(imgs[1]) if len(imgs)>1 else "")
        dpat = re.compile(r"(\d{3})\s+([Α-ΩA-Zα-ωa-z][Α-ΩA-Zα-ωa-z\s\-\.\/&]{2,28}?)\s+([\d\.,]+)\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+")
        depts,seen=[],set()
        for m2 in dpat.finditer(dt):
            net=parse_num(m2.group(4)); nm=m2.group(2).strip()
            if net>0.5 and nm not in seen: depts.append({"code":m2.group(1),"name":nm,"sales":net}); seen.add(nm)
        r["depts"] = json.dumps(sorted(depts,key=lambda x:x["sales"],reverse=True),ensure_ascii=False)
    except Exception as e: st.warning(f"OCR: {e}")
    return r

# ─── EMAIL SYNC ─────────────────────────────────────────────────────────────────
def _norm(s):
    s = unicodedata.normalize("NFD",s or "")
    return "".join(c for c in s if unicodedata.category(c)!="Mn").upper()

def _folder(mb):
    try:
        for f in mb.folder.list():
            n=f.name.upper()
            if "ALL" in n and ("MAIL" in n or "GMAIL" in n): return f.name
    except: pass
    return "INBOX"

def sync(df, ph):
    logs=[]; last_d=df["date"].max() if not df.empty else None
    since=(last_d-timedelta(days=1)) if last_d else (date.today()-timedelta(days=365))
    try:
        ph.markdown('<div class="bn bn-info">Συνδεση στο Gmail...</div>',unsafe_allow_html=True)
        with MailBox("imap.gmail.com").login(EMAIL_USER,EMAIL_PASS) as mb:
            try: mb.folder.set(_folder(mb))
            except: mb.folder.set("INBOX")
            hdrs=list(mb.fetch(AND(from_=EMAIL_FROM,date_gte=since),reverse=True,mark_seen=False,headers_only=True))
        rel=[h for h in hdrs if _norm(EMAIL_SUBJECT) in _norm(h.subject)]
        logs.append(f"Βρεθηκαν **{len(rel)}** emails")
        if not rel: ph.empty(); return df,logs
        found=0
        with MailBox("imap.gmail.com").login(EMAIL_USER,EMAIL_PASS) as mb:
            try: mb.folder.set(_folder(mb))
            except: mb.folder.set("INBOX")
            for i,hdr in enumerate(rel):
                ph.markdown(f'<div class="bn bn-info">Επεξεργασια {i+1}/{len(rel)}: {hdr.date.strftime("%d/%m/%Y")} ...</div>',unsafe_allow_html=True)
                full=list(mb.fetch(AND(uid=str(hdr.uid)),mark_seen=False))
                if not full: continue
                for att in full[0].attachments:
                    if not att.filename.lower().endswith(".pdf"): continue
                    data=extract_pdf(att.payload)
                    if data["date"] is None: data["date"]=hdr.date.date()
                    if last_d and data["date"]<=last_d and data["date"]!=date.today(): break
                    if data["netday"] and data["netday"]>0: df=upsert(df,data); found+=1
                    break
        ph.empty(); logs.append(f"Αποθηκευτηκαν **{found}** νεες αναφορες")
    except Exception as e:
        ph.empty(); logs.append(f"Σφαλμα IMAP: {e}")
        logs.append("```\n"+traceback.format_exc()+"\n```")
    return df,logs

# ─── UI ─────────────────────────────────────────────────────────────────────────
df    = load_history()
today = date.today()
last_d = df["date"].max() if not df.empty else None

st.markdown(f"""
<div class="ph">
  <div><div class="ph-ey">AB Skyros — Καταστημα 1082</div><div class="ph-h1">Sales Analytics</div></div>
  <div class="ph-rt"><div class="ph-lbl">Ανανεωση</div><div class="ph-val">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div></div>
</div>""", unsafe_allow_html=True)

if last_d:
    days_old=(today-last_d).days
    if days_old==0: st.markdown('<div class="bn bn-ok">Ενημερωμενο σημερα</div>',unsafe_allow_html=True)
    else: st.markdown(f'<div class="bn bn-warn">Τελευταια αναφορα {days_old} ημερες πισω ({last_d.strftime("%d/%m/%Y")})</div>',unsafe_allow_html=True)

c1,c2=st.columns([1,1])
with c1: sync_btn=st.button("Συγχρονισμος Email",use_container_width=True)
with c2: up_btn=st.button("Ανεβασμα PDF",use_container_width=True,type="secondary")
ph=st.empty()

if sync_btn:
    with st.spinner(""):
        df,logs=sync(df,ph); save_history(df)
    for l in logs: st.markdown(l)
    st.rerun()

if up_btn: st.session_state["show_up"]=True
if st.session_state.get("show_up"):
    up=st.file_uploader("PDF",type="pdf",label_visibility="collapsed")
    if up:
        raw=up.read(); pp=st.empty()
        pp.markdown('<div class="bn bn-info">OCR σε εξελιξη...</div>',unsafe_allow_html=True)
        data=extract_pdf(raw); pp.empty()
        if data["netday"] and data["netday"]>0:
            if data["date"] is None: data["date"]=today
            df=upsert(df,data); save_history(df)
            st.success(f"{data['date'].strftime('%d/%m/%Y')} — {fmt_euro(data['netday'])} · {data['customers']} πελατες")
            st.session_state["show_up"]=False; st.rerun()
        else:
            st.error("Δεν βρεθηκαν δεδομενα.")
            with st.expander("Debug OCR"):
                imgs=convert_from_bytes(raw,dpi=180,fmt="jpeg"); st.text(ocr_page(imgs[0])[:3000])

if df.empty:
    st.markdown('<div class="bn bn-warn" style="margin-top:2rem;">Δεν υπαρχουν δεδομενα. Κανετε συγχρονισμο.</div>',unsafe_allow_html=True)
    st.stop()

# ─── TABS ────────────────────────────────────────────────────────────────────────
t1,t2,t3,t4=st.tabs(["Τελευταια Αναφορα","Τασεις","Συγκρισεις","Ιστορικο"])

with t1:
    lat=df.iloc[0]; prv=df.iloc[1] if len(df)>1 else None
    p7r=df[df["date"]==(lat["date"]-timedelta(days=7))]; p7=p7r.iloc[0] if not p7r.empty else None
    ld=lat["date"]
    st.markdown(f'<p style="font-size:.78rem;color:#94a3b8;margin:.3rem 0 .8rem;">{DAYS_GR[ld.weekday()]} · {ld.day} {MONTHS_GR[ld.month-1]} {ld.year}</p>',unsafe_allow_html=True)
    def kpi(lbl,val,pv,acc,euro=True):
        if val is None or (isinstance(val,float) and pd.isna(val)):
            return f'<div class="kc" style="--a:{acc}"><div class="kl">{lbl}</div><div class="kv">—</div></div>'
        disp=fmt_euro(val) if euro else f"{int(val):,}".replace(",",".")
        dlt=delta_html(val,pv,euro) if pv is not None else ""
        return f'<div class="kc" style="--a:{acc}"><div class="kl">{lbl}</div><div class="kv">{disp}</div>{dlt}</div>'
    st.markdown(f"""<div class="kr kr4">
      {kpi("Πωλησεις Ημερας",lat["netday"],prv["netday"] if prv is not None else None,"#2563eb")}
      {kpi("Πελατες",lat["customers"],prv["customers"] if prv is not None else None,"#7c3aed",False)}
      {kpi("ΜΟ Καλαθιου",lat["avg_basket"],prv["avg_basket"] if prv is not None else None,"#0891b2")}
      {kpi("Πριν 7 Ημερες",lat["netday"],p7["netday"] if p7 is not None else None,"#059669")}
    </div>""",unsafe_allow_html=True)
    st.markdown('<div class="sh">Αναλυση Τμηματων</div>',unsafe_allow_html=True)
    try:
        depts=json.loads(lat.get("depts","[]") or "[]")
        if depts:
            mx=depts[0]["sales"]
            rows="".join(f'<div class="dr"><div class="drk">{i+1}</div><div class="dn">{d["name"]}</div><div class="dbb"><div class="dbf" style="width:{d["sales"]/mx*100:.0f}%"></div></div><div class="dv">{fmt_euro(d["sales"])}</div></div>' for i,d in enumerate(depts[:12]))
            st.markdown(f'<div class="dl">{rows}</div>',unsafe_allow_html=True)
    except: pass

with t2:
    st.markdown('<div class="sh">Εξελιξη Πωλησεων</div>',unsafe_allow_html=True)
    p=st.radio("",["30 ημερες","90 ημερες","Ετος"],horizontal=True,label_visibility="collapsed")
    since=(today-timedelta(days=30 if "30" in p else 90)) if "Ετος" not in p else date(today.year,1,1)
    ch=df[df["date"]>=since].sort_values("date").copy()
    ch["L"]=ch["date"].apply(lambda d:d.strftime("%d/%m"))
    if not ch.empty:
        st.markdown("**Ημερησιες Πωλησεις (EUR)**")
        st.bar_chart(ch.set_index("L")["netday"],color="#2563eb",use_container_width=True,height=200)
        st.markdown("**Πελατες**")
        st.bar_chart(ch.set_index("L")["customers"],color="#7c3aed",use_container_width=True,height=160)
        s=period_stats(df,since,today)
        st.markdown('<div class="sh">Περιληψη</div>',unsafe_allow_html=True)
        st.markdown(f"""<div class="kr kr3">
          <div class="kc" style="--a:#2563eb"><div class="kl">Συνολο</div><div class="kv-sm">{fmt_euro(s["total"])}</div></div>
          <div class="kc" style="--a:#7c3aed"><div class="kl">ΜΟ Ημερας</div><div class="kv-sm">{fmt_euro(s["avg_day"])}</div></div>
          <div class="kc" style="--a:#059669"><div class="kl">Κορυφη ({s["peak"].strftime("%d/%m") if s["peak"] else "—"})</div><div class="kv-sm">{fmt_euro(s["peak_val"])}</div></div>
        </div>""",unsafe_allow_html=True)

with t3:
    def cmp(ta,tb,sa,sb):
        def row(lbl,a,b,euro=True):
            fmt=fmt_euro if euro else lambda v:f"{v:.0f}"
            if b==0: ph2="—"
            else:
                pct=(a-b)/b*100; cls2="cp" if pct>=0 else "cn"
                ph2=f'<span class="{cls2}">{"+" if pct>=0 else ""}{pct:.1f}%</span>'
            return f'<tr><td>{lbl}</td><td>{fmt(a)}</td><td style="color:#94a3b8">{fmt(b)}</td><td>{ph2}</td></tr>'
        return(f'<table class="ct"><thead><tr><th></th><th class="cth">{ta}</th><th>{tb}</th><th>Μεταβολη</th></tr></thead><tbody>'
               +row("Συνολο Πωλησεων",sa["total"],sb["total"])
               +row("ΜΟ Ημερας",sa["avg_day"],sb["avg_day"])
               +row("ΜΟ Πελατων",sa["avg_cus"],sb["avg_cus"],euro=False)
               +row("Ημερες",sa["days"],sb["days"],euro=False)
               +row("Κορυφαια",sa["peak_val"],sb["peak_val"])
               +"</tbody></table>")
    st.markdown('<div class="sh">Μηνιαια Συγκριση</div>',unsafe_allow_html=True)
    ms=date(today.year,today.month,1); pe=ms-timedelta(days=1); ps=date(pe.year,pe.month,1)
    st.markdown(cmp(MONTHS_GR[today.month-1],MONTHS_GR[pe.month-1],period_stats(df,ms,today),period_stats(df,ps,pe)),unsafe_allow_html=True)
    st.markdown('<div class="sh">Εβδομαδιαια Συγκριση</div>',unsafe_allow_html=True)
    ws=today-timedelta(days=today.weekday()); pws=ws-timedelta(days=7)
    st.markdown(cmp("Τρεχουσα","Προηγουμενη",period_stats(df,ws,today),period_stats(df,pws,ws-timedelta(days=1))),unsafe_allow_html=True)

with t4:
    st.markdown('<div class="sh">Πληρες Ιστορικο</div>',unsafe_allow_html=True)
    d2=df[["date","netday","customers","avg_basket"]].copy()
    d2["date"]=d2["date"].apply(lambda x:x.strftime("%d/%m/%Y"))
    d2["netday"]=d2["netday"].apply(fmt_euro)
    d2["avg_basket"]=d2["avg_basket"].apply(fmt_euro)
    d2["customers"]=d2["customers"].apply(lambda v:f"{int(v)}" if pd.notna(v) else "—")
    d2.columns=["Ημερομηνια","Πωλησεις","Πελατες","ΜΟ Καλαθιου"]
    st.dataframe(d2,use_container_width=True,hide_index=True,height=460)
    st.download_button("Εξαγωγη CSV",df.to_csv(index=False).encode("utf-8"),f"sales_{today}.csv","text/csv")
