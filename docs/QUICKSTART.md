# ⚡ Quick Start Guide — 5 Minutes Setup

## Βήμα 1: Κατεβάστε και εγκαταστήστε (2 λεπτά)

```bash
# Linux/Mac
git clone <repo>
cd skyros-business-hub
sudo apt-get install -y tesseract-ocr tesseract-ocr-ell poppler-utils
pip install -r requirements.txt
mkdir -p pages
mv 1_Sales.py pages/
mv 2_Invoices.py pages/
```

## Βήμα 2: Ξεκινήστε την εφαρμογή (30 δευτερόλεπτα)

```bash
streamlit run Home.py
```

Ανοίγει αυτόματα στο: **http://localhost:8501**

## Βήμα 3: Δοκιμάστε τις δυνατότητες (2.5 λεπτά)

### 📧 Email Reading
1. Πατήστε **"📧 Διαβάστε τα emails για έλεγχο"**
2. Εισάγετε το Gmail address και App Password
3. Δείτε τα πρώτα 20 emails

### 📊 Add Sales Data
1. Πάει στη σελίδα **"Sales Analytics"**
2. Πατήστε το tab **"📸 Manual Entry"**
3. Εισάγετε δεδομένα (τζίρος, πελάτες, κ.α.)
4. Πατήστε **"✓ Προσθήκη"**

### 📄 Add Invoice
1. Πάει στη σελίδα **"Invoices"**
2. Πατήστε το tab **"➕ New Entry"**
3. Εισάγετε ένα τιμολόγιο ή πιστωτικό
4. Δείτε τα δεδομένα στο tab **"📊 Summary"**

## 📱 Mobile View

Για να δείτε την εφαρμογή στο κινητό:
1. Πάτε το menu ☰ (πάνω δεξιά)
2. Επιλέγετε **"Settings"**
3. Ενεργοποιείτε **"Wide mode"** για καλύτερη εμπειρία

## 🔧 Troubleshooting

### Error: "Tesseract not found"
```bash
# Ubuntu
sudo apt-get install tesseract-ocr

# Mac
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Error: "Email login failed"
- ✅ Gmail: Χρησιμοποιήστε App Password (όχι κανονικό password)
- ✅ Δείτε: https://myaccount.google.com/apppasswords

### Error: "poppler not found"
```bash
sudo apt-get install poppler-utils  # Linux
brew install poppler  # Mac
```

## 📊 File Structure

```
skyros-business-hub/
├── Home.py                 ← Ξεκινήστε εδώ!
├── pages/
│   ├── 1_Sales.py
│   └── 2_Invoices.py
├── .streamlit/
│   └── config.toml
├── utils.py
├── requirements.txt
├── packages.txt
└── README.md
```

## 💾 Data Files (Auto-created)

Αφού εισάγετε δεδομένα:
- `sales_history.csv` — Όλες οι πωλήσεις
- `invoices_data.csv` — Όλα τα τιμολόγια

## 🎯 Next Steps

1. ✅ Δοκιμάστε χειροκίνητη εισαγωγή δεδομένων
2. ✅ Συνδεθείτε με Gmail για email reading
3. ✅ Εξερευνήστε τα analytics
4. ✅ Κατεβάστε τα δεδομένα σε CSV

## 📞 Support

Αν αντιμετωπίσετε προβλήματα:
1. Ελεγχος internet connection
2. Ελεγχος Python version: `python --version` (≥3.8)
3. Ελεγχος Streamlit: `streamlit --version` (≥1.28)

---

**Ready? Run `streamlit run Home.py` and start! 🚀**
