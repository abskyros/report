# AB Skyros — Business Hub 📊

Streamlit application για διαχείριση πωλήσεων και τιμολογίων του καταστήματος AB Skyros 1082.

## Δυνατότητες

✅ **Home Dashboard** — Συνοψη πωλησεων + τιμολογιων  
✅ **Sales Analytics** — Ημερησιος τζιρος, πελατες, τμηματα  
✅ **Email Integration** — Αυτοματη ανακτηση δεδομενων απο email  
✅ **OCR Processing** — Εξαγωγη τιμων απο PDF/εικονες  
✅ **Invoice Tracking** — Παρακολουθηση τιμολογιων και πιστωτικων  
✅ **Mobile Responsive** — Σχεδιασμος για desktop και mobile  
✅ **No Sidebar** — Καθαρη προβολη απο κινητο  

## Εγκατάσταση

### 1. Clone το repository
```bash
git clone <repo-url>
cd skyros-business-hub
```

### 2. Εγκατασταση requirements

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y $(cat packages.txt)
pip install -r requirements.txt
```

**macOS (με Homebrew):**
```bash
brew install tesseract tesseract-lang poppler
pip install -r requirements.txt
```

**Windows:**
- Εγκατασταση [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- Εγκατασταση [Poppler](https://blog.alivate.com.au/poppler-windows/)
```bash
pip install -r requirements.txt
```

### 3. Δημιουργια φακέλου `pages/`
```bash
mkdir -p pages
mv 1_Sales.py pages/
mv 2_Invoices.py pages/
```

## Εκτέλεση

```bash
streamlit run Home.py
```

Θα ανοίξει στο `http://localhost:8501`

## Δομή Project

```
.
├── Home.py                    # Main dashboard
├── pages/
│   ├── 1_Sales.py            # Sales analytics page
│   └── 2_Invoices.py         # Invoices tracking page
├── utils.py                   # Helper functions
├── requirements.txt           # Python dependencies
├── packages.txt              # System dependencies
└── README.md                 # This file
```

## Αρχεία Δεδομένων

Τα δεδομένα αποθηκεύονται σε CSV:
- `sales_history.csv` — Ιστορικό πωλήσεων
- `invoices_data.csv` — Τιμολόγια και πιστωτικά

## Χρήση

### Home Dashboard
1. **Email Checking** — Συνδεθείτε με το Gmail και διαβάστε τα πρώτα 20 emails
2. **Sales Summary** — Βλέπετε τον τζίρο της σημερινής ημέρας
3. **Invoice Summary** — Σύνοψη εβδομαδιαίων/μηνιαίων τιμολογίων
4. **Combined Total** — Συνολικό καθαρό τζίρο από Sales + Invoices

### Sales Analytics
- **History Tab** — Ολο το ιστορικό πωλήσεων
- **Email Reading** — Ανάγνωση emails και εξαγωγή δεδομένων
- **Manual Entry** — Χειροκίνητη εισαγωγή δεδομένων

### Invoices
- **Summary** — Εβδομαδιαίες και μηνιαίες στατιστικές
- **All Records** — Ολες τις εγγραφές με δυνατότητα εξαγωγής CSV
- **New Entry** — Προσθήκη νέου τιμολογίου ή πιστωτικού

## Mobile Design

- ✅ Κρυμένη sidebar για καθαρή προβολή
- ✅ Responsive grid layouts
- ✅ Optimized font sizes
- ✅ Touch-friendly buttons
- ✅ Scrollable tables

## Email Configuration

**Gmail:**
1. Ενεργοποίηση 2FA
2. Δημιουργία [App Password](https://myaccount.google.com/apppasswords)
3. Χρήση App Password στο login

**Άλλοι providers:**
Τροποποίηση του IMAP server στο `1_Sales.py`:
```python
mb = MailBox('imap.your-provider.com')
```

## Troubleshooting

### OCR δεν λειτουργεί
```bash
# Check Tesseract installation
tesseract --version

# Install Greek language pack
sudo apt-get install tesseract-ocr-ell
```

### PDF errors
```bash
# Reinstall pdf2image
pip install --upgrade pdf2image
```

### Email connection failed
- Ελεγχος διαδικτύου
- Ελεγχος credentials
- Ελεγχος 2FA στο Gmail

## API Integration (Future)

Δυνατότητα ενοποίησης με:
- Point of Sale (POS) systems
- Accounting software (e.g., MyDATA AADE)
- Banking APIs

## Support

Για προβλήματα ή suggestions, επικοινωνήστε με τον admin.

---

**Last Updated:** April 2026  
**Version:** 2.0  
**Status:** Production Ready ✅
