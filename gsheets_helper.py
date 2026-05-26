"""
gsheets_helper.py — Κεντρική αποθήκη δεδομένων μέσω Google Sheets.
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SALES_SHEET    = "sales"
INVOICES_SHEET = "invoices"


# ── ROBUST NUMBER PARSER ──────────────────────────────────────────────────────
# CRITICAL FIX: το gspread.get_all_records() γυρνάει τους αριθμούς ως FORMATTED
# strings σε ελληνικό locale (πχ "406,22" αντί 406.22). Το pd.to_numeric()
# αποτυγχάνει σε αυτά και επιστρέφει NaN, οπότε το dropna() τα πετάει.
# Αυτή η συνάρτηση χειρίζεται σωστά όλες τις μορφές:
#   - Ελληνικά:    "406,22"      → 406.22
#   - Ελληνικά:    "2.763,73"    → 2763.73   (χιλιάδες + δεκαδικό)
#   - Αγγλικά:     "2,763.73"    → 2763.73
#   - Καθαρά:      406.22 (float)→ 406.22
#   - Κενά/None:   ""/None       → None

def _to_float(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("€", "").replace(" ", "").replace("\xa0", "")
    if not s:
        return None
    s = s.rstrip(".,")
    has_dot   = "." in s
    has_comma = "," in s
    if has_dot and has_comma:
        # Και τα δύο: το δεξιότερο είναι το δεκαδικό
        if s.rfind(",") > s.rfind("."):
            # Ελληνικά: 2.763,73 → 2763.73
            s = s.replace(".", "").replace(",", ".")
        else:
            # Αγγλικά: 2,763.73 → 2763.73
            s = s.replace(",", "")
    elif has_comma:
        # Μόνο κόμμα → ελληνικό δεκαδικό
        s = s.replace(",", ".")
    # Μόνο τελεία ή τίποτα → άφησέ το, η float() χειρίζεται
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ── PEM FIX ───────────────────────────────────────────────────────────────────

def _fix_pem(key: str) -> str:
    key = key.strip().replace("\r\n", "\n").replace("\r", "\n")
    if "\\n" in key:
        key = key.replace("\\n", "\n")
    if "-----BEGIN RSA PRIVATE KEY-----" in key:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        try:
            load_pem_private_key(key.encode(), password=None)
        except Exception:
            alt = (key
                   .replace("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----")
                   .replace("-----END RSA PRIVATE KEY-----",   "-----END PRIVATE KEY-----"))
            try:
                load_pem_private_key(alt.encode(), password=None)
                key = alt
            except Exception:
                pass
    return key


# ── CONNECTION ────────────────────────────────────────────────────────────────

def _get_client():
    raw  = st.secrets["gcp_service_account"]
    info = {k: v for k, v in raw.items()}
    info["private_key"] = _fix_pem(str(info.get("private_key", "")))
    if "token_uri" not in info:
        info["token_uri"] = "https://oauth2.googleapis.com/token"
    if "type" not in info:
        info["type"] = "service_account"
    try:
        return gspread.service_account_from_dict(info)
    except Exception as e:
        raise RuntimeError(f"Google Auth αποτυχία: {e}") from e


def _ws(sheet_name: str):
    """
    Ανοίγει το worksheet. Αν το spreadsheet δεν βρεθεί (404),
    εμφανίζει χρήσιμο μήνυμα με το ID που ψάχνει και τις οδηγίες.
    """
    sid = st.secrets.get("SPREADSHEET_ID", "ΔΕΝ ΟΡΙΣΤΗΚΕ")
    try:
        spreadsheet = _get_client().open_by_key(sid)
    except gspread.exceptions.APIError as e:
        if "404" in str(e) or "NOT_FOUND" in str(e).upper():
            st.error(
                f"❌ **Google Sheet δεν βρέθηκε!**\n\n"
                f"Το SPREADSHEET_ID που χρησιμοποιείται: `{sid}`\n\n"
                f"**Λύση — έλεγξε 2 πράγματα:**\n"
                f"1. Το SPREADSHEET_ID στα Streamlit Secrets είναι **λάθος ή placeholder**. "
                f"Πήγαινε στο Google Sheet σου, κοίτα το URL και αντιγραφε το σωστό ID.\n"
                f"2. Το Sheet δεν έχει **Share** με το service account email "
                f"(`{st.secrets.get('gcp_service_account', {}).get('client_email', '???')}`). "
                f"Άνοιξε το Sheet → Share → επικόλλησε αυτό το email → Editor."
            )
            raise
        raise
    except Exception as e:
        st.error(f"❌ Σφάλμα σύνδεσης Google Sheets (ID: `{sid}`): {e}")
        raise

    existing = {ws.title.lower(): ws for ws in spreadsheet.worksheets()}
    if sheet_name.lower() in existing:
        return existing[sheet_name.lower()]
    # Tab δεν υπάρχει → το δημιουργούμε αυτόματα
    ws = spreadsheet.add_worksheet(title=sheet_name, rows=2000, cols=20)
    if sheet_name == SALES_SHEET:
        ws.update([["date","net_sales","customers","avg_basket"]])
    elif sheet_name == INVOICES_SHEET:
        ws.update([["DATE","TYPE","VALUE"]])
    return ws


# ── SALES ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_sales() -> pd.DataFrame:
    try:
        rows = _ws(SALES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])
        df = pd.DataFrame(rows)
        df["date"]       = pd.to_datetime(df["date"], errors="coerce").dt.date
        # FIX: χρησιμοποιούμε τον robust parser αντί για pd.to_numeric
        df["net_sales"]  = df["net_sales"].apply(_to_float)
        df["customers"]  = df["customers"].apply(_to_float)
        df["avg_basket"] = df["avg_basket"].apply(_to_float)
        df = df.dropna(subset=["date","net_sales"])
        return (df.sort_values("net_sales", ascending=False)
                  .drop_duplicates("date", keep="first")
                  .sort_values("date", ascending=False)
                  .reset_index(drop=True))
    except Exception as e:
        st.warning(f"⚠️ Σφάλμα φόρτωσης πωλήσεων: {e}")
        return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])


def _save_sales(df: pd.DataFrame):
    out = (df.sort_values("date", ascending=False)
             .drop_duplicates("date", keep="first")
             .reset_index(drop=True).copy())
    out["date"] = out["date"].astype(str)
    data = [out.columns.tolist()] + out.fillna("").values.tolist()
    ws = _ws(SALES_SHEET)
    ws.clear()
    ws.update(data)
    load_sales.clear()


def merge_sales(recs: list) -> int:
    if not recs:
        return 0
    ndf = pd.DataFrame(recs)
    ndf["date"]      = pd.to_datetime(ndf["date"], errors="coerce").dt.date
    ndf["net_sales"] = pd.to_numeric(ndf["net_sales"], errors="coerce")
    ndf = (ndf.dropna(subset=["date","net_sales"])
              .sort_values("net_sales", ascending=False)
              .drop_duplicates("date", keep="first"))
    existing = load_sales()
    changed  = 0
    base     = existing.copy()
    for _, r in ndf.iterrows():
        ex = existing[existing["date"] == r["date"]]
        if ex.empty:
            base    = pd.concat([base, r.to_frame().T], ignore_index=True)
            changed += 1
        else:
            row = ex.iloc[0]
            needs_update = False
            if pd.notna(r["net_sales"]) and r["net_sales"] > row["net_sales"]:
                needs_update = True
            new_c = r.get("customers"); old_c = row.get("customers")
            if pd.notna(new_c) and new_c > 0:
                if pd.isna(old_c) or old_c < 50 or (old_c > 0 and (new_c/old_c > 2.5 or new_c/old_c < 0.4)):
                    needs_update = True
            new_a = r.get("avg_basket"); old_a = row.get("avg_basket")
            if pd.notna(new_a) and new_a > 0 and (pd.isna(old_a) or old_a < 5):
                needs_update = True
            if needs_update:
                base    = base[base["date"] != r["date"]]
                base    = pd.concat([base, r.to_frame().T], ignore_index=True)
                changed += 1
    if changed > 0:
        _save_sales(base)
    return changed


def already_known_sale_dates() -> set:
    df = load_sales()
    if df.empty: return set()
    good = df[(df["net_sales"] > 2000) & (df["customers"].fillna(0) > 50)]
    return set(good["date"].tolist())


# ── INVOICES ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_invoices() -> pd.DataFrame:
    try:
        rows = _ws(INVOICES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["DATE","TYPE","VALUE"])
        df = pd.DataFrame(rows)
        df["DATE"]  = pd.to_datetime(df["DATE"], errors="coerce")
        # FIX: χρησιμοποιούμε τον robust parser αντί για pd.to_numeric
        df["VALUE"] = df["VALUE"].apply(_to_float)
        df = df.dropna(subset=["DATE","VALUE"])
        return df.sort_values("DATE", ascending=False).reset_index(drop=True)
    except Exception as e:
        st.warning(f"⚠️ Σφάλμα φόρτωσης τιμολογίων: {e}")
        return pd.DataFrame(columns=["DATE","TYPE","VALUE"])


def _save_invoices(df: pd.DataFrame):
    out = df.sort_values("DATE", ascending=False).reset_index(drop=True).copy()
    out["DATE"] = out["DATE"].astype(str)
    data = [out.columns.tolist()] + out.fillna("").values.tolist()
    ws = _ws(INVOICES_SHEET)
    ws.clear()
    ws.update(data)
    load_invoices.clear()


def merge_invoices(new_dfs: list) -> int:
    if not new_dfs:
        return 0
    new_df   = pd.concat(new_dfs, ignore_index=True)
    existing = load_invoices()
    merged   = (pd.concat([existing, new_df])
                  .drop_duplicates(subset=["DATE","TYPE","VALUE"])
                  .sort_values("DATE", ascending=False)
                  .reset_index(drop=True))
    n_new = len(merged) - len(existing)
    if n_new > 0:
        _save_invoices(merged)
    return max(n_new, 0)
