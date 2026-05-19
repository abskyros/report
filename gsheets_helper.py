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


# ── CONNECTION ────────────────────────────────────────────────────────────────

def _get_client():
    """
    Δημιουργεί gspread client κάθε φορά — αποφεύγει stale cache issues.
    Χρησιμοποιεί gspread.service_account_from_dict() που χειρίζεται
    σωστά το private_key ανεξάρτητα από τη μορφή \n.
    """
    info = {k: v for k, v in st.secrets["gcp_service_account"].items()}

    # Διόρθωση private_key: literal \n → πραγματικό newline
    pk = str(info.get("private_key", ""))
    pk = pk.replace("\\n", "\n")
    # Αν ακόμα δεν έχει newlines, προσθέτουμε μετά τα headers
    if "-----BEGIN" in pk and "\n" not in pk.replace("-----BEGIN RSA PRIVATE KEY-----", "").replace("-----END RSA PRIVATE KEY-----", "").replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", ""):
        pk = pk.replace("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----\n")
        pk = pk.replace("-----END RSA PRIVATE KEY-----", "\n-----END RSA PRIVATE KEY-----")
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        pk = pk.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
    info["private_key"] = pk

    # Βεβαιωνόμαστε ότι υπάρχουν τα απαραίτητα πεδία
    if "token_uri" not in info:
        info["token_uri"] = "https://oauth2.googleapis.com/token"
    if "type" not in info:
        info["type"] = "service_account"

    try:
        return gspread.service_account_from_dict(info)
    except Exception as e:
        pk_preview = info.get("private_key","")[:100]
        first_line = pk_preview.split("\n")[0]
        raise RuntimeError(
            f"Google Auth αποτυχία. "
            f"private_key πρώτη γραμμή: '{first_line}' | "
            f"Σφάλμα: {e}"
        ) from e


def _ws(sheet_name: str):
    """Επιστρέφει το worksheet — fresh connection κάθε φορά."""
    return _get_client().open_by_key(st.secrets["SPREADSHEET_ID"]).worksheet(sheet_name)


# ── SALES ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_sales() -> pd.DataFrame:
    """Φορτώνει πωλήσεις. Cache 2 λεπτά."""
    try:
        rows = _ws(SALES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])
        df = pd.DataFrame(rows)
        df["date"]       = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["net_sales"]  = pd.to_numeric(df["net_sales"],  errors="coerce")
        df["customers"]  = pd.to_numeric(df["customers"],  errors="coerce")
        df["avg_basket"] = pd.to_numeric(df["avg_basket"], errors="coerce")
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
        elif r["net_sales"] > ex.iloc[0]["net_sales"]:
            base    = base[base["date"] != r["date"]]
            base    = pd.concat([base, r.to_frame().T], ignore_index=True)
            changed += 1
    if changed > 0:
        _save_sales(base)
    return changed


# ── INVOICES ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_invoices() -> pd.DataFrame:
    """Φορτώνει τιμολόγια. Cache 2 λεπτά."""
    try:
        rows = _ws(INVOICES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["DATE","TYPE","VALUE"])
        df = pd.DataFrame(rows)
        df["DATE"]  = pd.to_datetime(df["DATE"], errors="coerce")
        df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
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
