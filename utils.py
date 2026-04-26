import pandas as pd
import re
from datetime import datetime

def fmt_euro(v):
    """Μορφοποίηση τιμής σε ευρώ με ελληνικό format"""
    if v is None or (isinstance(v, float) and pd.isna(v)): 
        return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

def extract_sales_from_text(text):
    """Εξαγωγή πωλήσεων από OCR κείμενο"""
    patterns = [
        r'NET\s*?[:\-]?\s*?([\d.,]+)',
        r'ΚΑΘΑΡΟ\s*?[:\-]?\s*?([\d.,]+)',
        r'ΤΕΛΙΚΟ\s*?[:\-]?\s*?([\d.,]+)',
        r'€\s*([\d.,]+)(?:\s*€)?$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            val = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(val)
            except:
                pass
    return None

def parse_date_flexible(date_str):
    """Εύκαμπτη ανάλυση ημερομηνίας"""
    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d.%m.%Y",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt).date()
        except:
            continue
    
    try:
        return pd.to_datetime(date_str).date()
    except:
        return None

def validate_email_format(email):
    """Έλεγχος έγκυρης μορφής email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def clean_number(val):
    """Καθαρισμός αριθμού από κείμενο"""
    if isinstance(val, (int, float)):
        return val
    if pd.isna(val):
        return None
    
    val = str(val).strip()
    val = re.sub(r'[€%\s]', '', val)
    val = val.replace('.', '').replace(',', '.')
    
    try:
        return float(val)
    except:
        return None

def apply_iva(amount, iva_percent=24):
    """Υπολογισμός ΦΠΑ"""
    return amount * (1 + iva_percent/100)

def remove_iva(amount, iva_percent=24):
    """Αφαίρεση ΦΠΑ από τιμή"""
    return amount / (1 + iva_percent/100)

def round_euro(value, decimals=2):
    """Στρογγυλοποίηση ευρώ"""
    return round(float(value), decimals) if value else 0.0
