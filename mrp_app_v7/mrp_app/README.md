# 📊 Forecasting & MRP Dashboard — CSV Edition

Sales forecast 30 hari ke depan + Material Requirement Planning harian.
Input dari CSV upload. Tidak perlu database atau API eksternal.

---

## Struktur project

```
mrp_app/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── .env.example
├── config/
│   ├── __init__.py
│   └── settings.py         # Config dari .env
├── data/
│   ├── __init__.py
│   ├── loader.py           # CSV validation & loading
│   └── sample.py           # Sample data generator
├── forecasting/
│   ├── __init__.py
│   ├── preprocessor.py     # Cleaning, imputation, classification
│   ├── models.py           # Prophet, SARIMA, Naive
│   ├── metrics.py          # Accuracy, MAPE, MAE, RMSE
│   └── engine.py           # Orchestrator per produk
├── mrp/
│   ├── __init__.py
│   └── calculator.py       # Daily MRP, pivot, total
└── ui/
    ├── __init__.py
    ├── styles.py            # CSS injection
    ├── charts.py            # Plotly chart builders
    └── filters.py           # Filter helpers
```

---

## Quick start

```bash
cd mrp_app

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # opsional, nilai default sudah cukup

streamlit run app.py
```

Buka **http://localhost:8501**.
Klik **"Run dengan sample data"** untuk langsung demo.

---

## Format CSV

### sales.csv
```csv
date,product_name,sales_qty
2025-01-01,Product A,28
2025-01-01,Product B,14
2025-01-02,Product A,31
```

### bom.csv
```csv
product_name,material,component_qty
Product A,Sugar,0.050
Product A,Milk,0.150
Product B,Sugar,0.030
```

---

## Fitur

| Fitur | Detail |
|---|---|
| CSV upload | Upload langsung dari browser, tidak perlu setup |
| Sample data | 5 produk kafe, 180 hari historis |
| Forecast | Prophet → SARIMA → Naive (auto-fallback) |
| Akurasi | 100% − MAPE, dihitung via train/test split |
| Filter tanggal | Pilih start–end date untuk forecast & MRP |
| Multi-select produk | Toggle produk mana yang dianalisis |
| Filter material | Tampilkan hanya material tertentu di MRP |
| MRP pivot | Material (baris) × Tanggal (kolom), qty beli per hari |
| Export CSV | Download forecast, pivot MRP, total MRP |
| Line chart | Historis 90 hari + forecast, granularity harian |

---

## Model selection otomatis

| Data historis | Model |
|---|---|
| ≥ 60 hari, ≥ 30 non-zero | Prophet (jika terinstall) → SARIMA → Naive |
| 30–59 hari | Prophet → SARIMA → Naive |
| 14–29 hari | SARIMA → Naive |
| < 14 hari | Naive (rolling mean + pola DOW) |

---

## Environment variables (.env)

```dotenv
FORECAST_HORIZON_DAYS=30
TRAIN_TEST_SPLIT_RATIO=0.8
MIN_DATA_POINTS=14
LOG_LEVEL=INFO
```

---

## Install Prophet (opsional, untuk akurasi lebih baik)

Prophet butuh C++ compiler.

```bash
# Ubuntu/Debian
sudo apt install build-essential
pip install prophet

# macOS
xcode-select --install
pip install prophet

# Windows: install Visual Studio Build Tools terlebih dahulu
pip install prophet
```

Tanpa Prophet, program tetap berjalan menggunakan SARIMA atau Naive.

---

## Docker

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t mrp-app .
docker run -p 8501:8501 mrp-app
```
