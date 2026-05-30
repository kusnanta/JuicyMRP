# 📊 Forecasting & MRP Dashboard — Vercel Edition

> Next.js 14 · TypeScript · Tailwind CSS · Plotly.js  
> Vercel-native: no Python, no Docker required.

---

## Stack

| Layer | Tech |
|---|---|
| Framework | Next.js 14 (Pages Router) |
| Language | TypeScript |
| Styling | Tailwind CSS + custom CSS |
| Charts | Plotly.js (dynamic import, no SSR) |
| CSV parsing | PapaParse |
| Forecasting | Pure TS (Prophet-like Fourier regression, Holt-Winters ES, Rolling Mean) |
| MRP | Pure TS (client + API route) |
| Deployment | Vercel (zero config) |

---

## Project Structure

```
mrp_nextjs/
├── pages/
│   ├── _app.tsx          # App wrapper
│   ├── index.tsx         # Main dashboard page
│   └── api/
│       └── forecast.ts   # Serverless API route for forecasting
├── components/
│   ├── ForecastChart.tsx  # Plotly line chart (dynamic import)
│   ├── PivotTable.tsx     # Forecast pivot, MRP pivot, accuracy pivot
│   ├── MrpTotalTable.tsx  # Total MRP with inline bar chart
│   └── MultiSelect.tsx    # Dropdown multi-select filter
├── lib/
│   ├── types.ts           # Shared TypeScript types
│   ├── forecast.ts        # Forecasting engine (Prophet-like, HW, Naive)
│   ├── mrp.ts             # MRP calculation
│   └── sample.ts          # Sample data generator
├── styles/
│   └── globals.css
├── vercel.json
├── next.config.js
├── tailwind.config.js
└── package.json
```

---

## Quick Start — Local

```bash
cd mrp_nextjs
npm install
npm run dev
# Open http://localhost:3000
```

Click **"Run dengan sample data"** to demo with 5 cafe products.

---

## Deploy to Vercel

### Option A — Vercel CLI
```bash
npm i -g vercel
vercel
# Follow prompts — framework auto-detected as Next.js
```

### Option B — GitHub Integration
1. Push to GitHub
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your repository
4. Vercel auto-detects Next.js — click **Deploy**

No environment variables needed for default operation.

---

## Input CSV Format

### sales.csv
```csv
date,product_name,sales_qty
2025-01-01,Product A,28
2025-01-01,Product B,14
```

### bom.csv
```csv
product_name,material,component_qty
Product A,Sugar,0.050
Product A,Milk,0.150
```

---

## Forecast Methods

| Method | Algorithm | Best for |
|---|---|---|
| Prophet-like | Fourier regression (trend + weekly/yearly seasonality) | Rich data ≥ 21 days |
| Holt-Winters | Triple exponential smoothing (additive) | Medium data ≥ 14 days |
| Rolling Mean | Weighted rolling average + DOW multipliers | Any data size |
| Terbaik (auto) | Picks highest accuracy_pct per product | Default |

Accuracy = 100% − MAPE, computed on last-14-day test split.

---

## Features

- CSV upload (sales + BOM)
- Sample data (5 cafe products, 180 days history)
- Multi-select filter: produk, material, date range
- Forecast method selector with per-product auto-best
- Accuracy pivot table: product × method, best cell highlighted
- Forecast pivot: product × date
- MRP pivot: material × date (qty/day)
- MRP total table with inline bar chart (bar = avg qty/day)
- Export CSV: forecast, MRP pivot, MRP total
- Vercel serverless API route for forecast computation
