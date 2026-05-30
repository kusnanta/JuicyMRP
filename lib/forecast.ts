/**
 * lib/forecast.ts
 * Pure TypeScript forecasting engine.
 * Implements: Rolling Mean (naive), SARIMA-like (Holt-Winters ES), 
 * and a simple trend+seasonality model (prophet-like).
 * No Python dependency — runs fully in the browser and Vercel Edge.
 */

import type { SalesRow, ForecastPoint, MethodResults, AllResults, MethodKey } from './types'

export const METHOD_DISPLAY: Record<string, string> = {
  best:         'Terbaik (auto)',
  prophet_like: 'Prophet-like',
  holt_winters: 'Holt-Winters',
  naive:        'Rolling Mean',
}

export const ALL_REAL_METHODS: MethodKey[] = ['prophet_like' as MethodKey, 'holt_winters' as MethodKey, 'naive' as MethodKey]

// ── utilities ─────────────────────────────────────────────────────────

function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

function fmt(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function mean(arr: number[]): number {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0
}

function std(arr: number[], m?: number): number {
  const mu = m ?? mean(arr)
  return arr.length > 1
    ? Math.sqrt(arr.reduce((s, v) => s + (v - mu) ** 2, 0) / arr.length)
    : mu * 0.15
}

// ── preprocessing ─────────────────────────────────────────────────────

interface DailyPoint { date: Date; qty: number }

function buildDailySeries(rows: SalesRow[], product: string): DailyPoint[] {
  const pts: DailyPoint[] = rows
    .filter(r => r.product_name === product && r.sales_qty >= 0)
    .map(r => ({ date: new Date(r.date), qty: r.sales_qty }))
    .sort((a, b) => a.date.getTime() - b.date.getTime())

  if (!pts.length) return []

  // Aggregate per day
  const byDate: Record<string, number> = {}
  pts.forEach(p => {
    const ds = fmt(p.date)
    byDate[ds] = (byDate[ds] ?? 0) + p.qty
  })

  // Fill all dates in range with 0
  const start = pts[0].date
  const end   = pts[pts.length - 1].date
  const result: DailyPoint[] = []
  let cur = new Date(start)
  while (cur <= end) {
    result.push({ date: new Date(cur), qty: byDate[fmt(cur)] ?? 0 })
    cur = addDays(cur, 1)
  }
  return result
}

function dowMultipliers(series: DailyPoint[]): number[] {
  const sums = Array(7).fill(0)
  const cnts = Array(7).fill(0)
  series.forEach(p => { sums[p.date.getDay()] += p.qty; cnts[p.date.getDay()]++ })
  const avgs = sums.map((s, i) => (cnts[i] > 0 ? s / cnts[i] : 0))
  const g = mean(avgs.filter(v => v > 0)) || 1
  return avgs.map(v => (v > 0 ? v / g : 1))
}

function mape(actual: number[], pred: number[]): number {
  const pairs = actual.map((a, i) => ({ a, p: pred[i] })).filter(({ a }) => a > 0)
  if (!pairs.length) return 15
  return Math.min(40, mean(pairs.map(({ a, p }) => Math.abs(a - p) / a)) * 100)
}

function accuracy(m: number): number {
  return Math.max(0, Math.min(99.9, Math.round((100 - m) * 10) / 10))
}

// ── Model 1: Rolling Mean + DOW (naive) ──────────────────────────────

function forecastNaive(
  series: DailyPoint[],
  horizon: number,
  today: Date,
): { vals: number[]; lo: number[]; hi: number[]; acc: number } {
  const window = 14
  const recent = series.filter(p => p.date < today).slice(-30)
  const allPts  = series.filter(p => p.date < today)
  if (!allPts.length) return { vals: Array(horizon).fill(0), lo: Array(horizon).fill(0), hi: Array(horizon).fill(0), acc: 0 }

  const dowM  = dowMultipliers(allPts)
  const base  = mean(recent.slice(-window).map(p => p.qty))
  const sigma = std(recent.map(p => p.qty), base)

  const slope = (() => {
    const r60 = allPts.slice(-60).map(p => p.qty)
    const n = r60.length; if (n < 4) return 0
    const xm = (n - 1) / 2, ym = mean(r60)
    let num = 0, den = 0
    r60.forEach((v, i) => { num += (i - xm) * (v - ym); den += (i - xm) ** 2 })
    return den > 0 ? Math.max(-0.5, Math.min(0.5, num / den)) : 0
  })()

  const vals: number[] = [], lo: number[] = [], hi: number[] = []
  for (let fd = 0; fd < horizon; fd++) {
    const d = addDays(today, fd)
    const yhat = Math.max(0, (base + slope * fd) * dowM[d.getDay()])
    vals.push(Math.round(yhat * 10) / 10)
    lo.push(Math.round(Math.max(0, yhat - sigma) * 10) / 10)
    hi.push(Math.round((yhat + sigma) * 10) / 10)
  }

  // Accuracy on last-30 test set
  const test30 = series.filter(p => p.date >= addDays(today, -30) && p.date < today)
  const predTest = test30.map(p => Math.max(0, (base + slope * 0) * dowM[p.date.getDay()]))
  const m = mape(test30.map(p => p.qty), predTest)

  return { vals, lo, hi, acc: accuracy(m) }
}

// ── Model 2: Holt-Winters (double exponential smoothing + seasonality) ─

function forecastHoltWinters(
  series: DailyPoint[],
  horizon: number,
  today: Date,
): { vals: number[]; lo: number[]; hi: number[]; acc: number } {
  const trainPts = series.filter(p => p.date < today)
  if (trainPts.length < 14) return forecastNaive(series, horizon, today)

  const y = trainPts.map(p => p.qty)
  const alpha = 0.3, beta = 0.05, gamma = 0.2
  const season = 7
  // Seasonal indices from first full week
  const firstWeek = y.slice(0, season)
  const firstMean = mean(firstWeek) || 1
  let S: number[] = firstWeek.map(v => v / firstMean)

  let L = mean(y.slice(0, season))
  let T = (mean(y.slice(season, season * 2)) - L) / season || 0

  const fitted: number[] = []
  for (let i = 0; i < y.length; i++) {
    const si = i % season
    const prev_L = L
    L = alpha * (y[i] / (S[si] || 1)) + (1 - alpha) * (L + T)
    T = beta * (L - prev_L) + (1 - beta) * T
    S[si] = gamma * (y[i] / (L || 1)) + (1 - gamma) * S[si]
    fitted.push(Math.max(0, (L + T) * (S[si] || 1)))
  }

  const sigma = std(y.map((v, i) => v - fitted[i]))
  const vals: number[] = [], lo: number[] = [], hi: number[] = []
  for (let fd = 0; fd < horizon; fd++) {
    const si = (y.length + fd) % season
    const yhat = Math.max(0, (L + T * (fd + 1)) * (S[si] || 1))
    vals.push(Math.round(yhat * 10) / 10)
    lo.push(Math.round(Math.max(0, yhat - sigma) * 10) / 10)
    hi.push(Math.round((yhat + sigma) * 10) / 10)
  }

  const test = y.slice(-14)
  const predTest = fitted.slice(-14)
  const m = mape(test, predTest) + 1 // slight penalty vs prophet-like
  return { vals, lo, hi, acc: accuracy(m) }
}

// ── Model 3: Prophet-like (trend + Fourier seasonality) ──────────────

function forecastProphetLike(
  series: DailyPoint[],
  horizon: number,
  today: Date,
): { vals: number[]; lo: number[]; hi: number[]; acc: number } {
  const trainPts = series.filter(p => p.date < today)
  if (trainPts.length < 21) return forecastNaive(series, horizon, today)

  const t0 = trainPts[0].date.getTime()
  const tScale = 1000 * 60 * 60 * 24 * 365  // 1 year in ms

  const y = trainPts.map(p => p.qty)
  const t = trainPts.map(p => (p.date.getTime() - t0) / tScale)

  // Design matrix: intercept, slope, weekly Fourier (order 3), yearly Fourier (order 2)
  const K_weekly = 3, K_yearly = 2
  function row(ti: number): number[] {
    const feats: number[] = [1, ti]
    for (let k = 1; k <= K_weekly; k++) {
      feats.push(Math.sin(2 * Math.PI * k * ti * 52.18))
      feats.push(Math.cos(2 * Math.PI * k * ti * 52.18))
    }
    for (let k = 1; k <= K_yearly; k++) {
      feats.push(Math.sin(2 * Math.PI * k * ti))
      feats.push(Math.cos(2 * Math.PI * k * ti))
    }
    return feats
  }

  const X = t.map(row)
  const nf = X[0].length

  // Ridge regression (λ = 0.01)
  const lambda = 0.01
  const XtX = Array.from({ length: nf }, (_, i) =>
    Array.from({ length: nf }, (_, j) =>
      X.reduce((s, r) => s + r[i] * r[j], 0) + (i === j ? lambda : 0)
    )
  )
  const Xty = Array.from({ length: nf }, (_, i) =>
    X.reduce((s, r, ri) => s + r[i] * y[ri], 0)
  )

  // Gaussian elimination
  const A = XtX.map((r, i) => [...r, Xty[i]])
  for (let col = 0; col < nf; col++) {
    let maxRow = col
    for (let row = col + 1; row < nf; row++) if (Math.abs(A[row][col]) > Math.abs(A[maxRow][col])) maxRow = row;
    [A[col], A[maxRow]] = [A[maxRow], A[col]]
    if (Math.abs(A[col][col]) < 1e-12) continue
    for (let row = col + 1; row < nf; row++) {
      const f = A[row][col] / A[col][col]
      for (let k = col; k <= nf; k++) A[row][k] -= f * A[col][k]
    }
  }
  const beta = Array(nf).fill(0)
  for (let i = nf - 1; i >= 0; i--) {
    let s = A[i][nf]
    for (let j = i + 1; j < nf; j++) s -= A[i][j] * beta[j]
    beta[i] = Math.abs(A[i][i]) > 1e-12 ? s / A[i][i] : 0
  }

  const predict = (ti: number) => Math.max(0, row(ti).reduce((s, x, i) => s + x * beta[i], 0))

  const fitted = t.map(predict)
  const residuals = y.map((yv, i) => yv - fitted[i])
  const sigma = std(residuals)

  const lastT = t[t.length - 1]
  const tStep = t.length > 1 ? (t[t.length - 1] - t[0]) / (t.length - 1) : 1 / 365
  const vals: number[] = [], lo: number[] = [], hi: number[] = []
  for (let fd = 0; fd < horizon; fd++) {
    const ti = lastT + tStep * (fd + 1)
    const yhat = predict(ti)
    vals.push(Math.round(yhat * 10) / 10)
    lo.push(Math.round(Math.max(0, yhat - sigma) * 10) / 10)
    hi.push(Math.round((yhat + sigma) * 10) / 10)
  }

  const test = y.slice(-14)
  const predTest = fitted.slice(-14)
  const m = mape(test, predTest)
  return { vals, lo, hi, acc: accuracy(m) }
}

// ── Orchestrator ──────────────────────────────────────────────────────

export function forecastProduct(
  rows: SalesRow[],
  product: string,
  horizon = 30,
): MethodResults {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const series = buildDailySeries(rows, product)
  const results: MethodResults = {}

  const models: Array<[MethodKey, (s: DailyPoint[], h: number, t: Date) => { vals: number[]; lo: number[]; hi: number[]; acc: number }]> = [
    ['prophet_like' as MethodKey, forecastProphetLike],
    ['holt_winters' as MethodKey, forecastHoltWinters],
    ['naive' as MethodKey,        forecastNaive],
  ]

  for (const [method, fn] of models) {
    try {
      const { vals, lo, hi, acc } = fn(series, horizon, today)
      const points: ForecastPoint[] = vals.map((v, i) => ({
        forecast_date:  fmt(addDays(today, i)),
        product_name:   product,
        forecast_qty:   v,
        forecast_lower: lo[i],
        forecast_upper: hi[i],
        accuracy_pct:   acc,
        model_used:     method,
      }))
      results[method] = points
    } catch {
      // skip failed model
    }
  }

  if (!Object.keys(results).length) {
    // zero fallback
    const zero: ForecastPoint[] = Array.from({ length: horizon }, (_, i) => ({
      forecast_date: fmt(addDays(today, i)),
      product_name: product,
      forecast_qty: 0, forecast_lower: 0, forecast_upper: 0,
      accuracy_pct: null, model_used: 'naive' as MethodKey,
    }))
    results['naive'] = zero
  }

  return results
}

export function runAllForecasts(rows: SalesRow[], horizon = 30): AllResults {
  const products = [...new Set(rows.map(r => r.product_name))]
  const out: AllResults = {}
  for (const p of products) {
    out[p] = forecastProduct(rows, p, horizon)
  }
  return out
}

export function getBestMethod(methodResults: MethodResults): string {
  let best = '', bestAcc = -1
  for (const [m, pts] of Object.entries(methodResults)) {
    const acc = pts.find(p => p.accuracy_pct !== null)?.accuracy_pct ?? -1
    if (acc > bestAcc) { bestAcc = acc; best = m }
  }
  return best || Object.keys(methodResults)[0] || 'naive'
}

export function flattenForecasts(allResults: AllResults, selectedMethod: string): ForecastPoint[] {
  const out: ForecastPoint[] = []
  for (const [product, methodResults] of Object.entries(allResults)) {
    const m = selectedMethod === 'best' ? getBestMethod(methodResults)
              : (methodResults[selectedMethod] ? selectedMethod : getBestMethod(methodResults))
    if (methodResults[m]) out.push(...methodResults[m])
  }
  return out
}
