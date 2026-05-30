/**
 * lib/mrp.ts — Material Requirement Planning calculations.
 * Pure TypeScript, runs client-side and server-side.
 */

import type { ForecastPoint, BomRow, MrpDailyRow, MrpTotalRow } from './types'

export function calculateDailyMrp(
  forecasts: ForecastPoint[],
  bom: BomRow[],
  products?: string[],
  dateFrom?: string,
  dateTo?: string,
): MrpDailyRow[] {
  let fc = forecasts
  if (products?.length) fc = fc.filter(r => products.includes(r.product_name))
  if (dateFrom) fc = fc.filter(r => r.forecast_date >= dateFrom)
  if (dateTo)   fc = fc.filter(r => r.forecast_date <= dateTo)
  if (!fc.length || !bom.length) return []

  const agg: Record<string, number> = {}
  for (const row of fc) {
    const entries = bom.filter(b => b.product_name === row.product_name)
    for (const b of entries) {
      const key = `${row.forecast_date}||${b.material}`
      agg[key] = (agg[key] ?? 0) + row.forecast_qty * b.component_qty
    }
  }

  return Object.entries(agg)
    .map(([key, qty]) => {
      const [order_date, material] = key.split('||')
      return { order_date, material, qty_needed: Math.round(qty * 1000) / 1000 }
    })
    .sort((a, b) => a.order_date.localeCompare(b.order_date) || a.material.localeCompare(b.material))
}

export function pivotMrp(daily: MrpDailyRow[]): {
  materials: string[]
  dates: string[]
  data: Record<string, Record<string, number>>
  totals: Record<string, number>
} {
  const materials = [...new Set(daily.map(r => r.material))].sort()
  const dates     = [...new Set(daily.map(r => r.order_date))].sort()
  const data: Record<string, Record<string, number>> = {}
  const totals: Record<string, number> = {}

  for (const m of materials) {
    data[m] = {}
    totals[m] = 0
    for (const d of dates) data[m][d] = 0
  }

  for (const row of daily) {
    if (data[row.material]) {
      data[row.material][row.order_date] = Math.round(row.qty_needed * 1000) / 1000
      totals[row.material] = Math.round(((totals[row.material] ?? 0) + row.qty_needed) * 1000) / 1000
    }
  }

  // Sort materials by total descending
  const sortedMats = materials.sort((a, b) => (totals[b] ?? 0) - (totals[a] ?? 0))
  return { materials: sortedMats, dates, data, totals }
}

export function totalMrp(
  forecasts: ForecastPoint[],
  bom: BomRow[],
  products?: string[],
  dateFrom?: string,
  dateTo?: string,
): MrpTotalRow[] {
  const daily = calculateDailyMrp(forecasts, bom, products, dateFrom, dateTo)
  if (!daily.length) return []

  const nDays = new Set(daily.map(r => r.order_date)).size || 1
  const byMat: Record<string, number> = {}
  for (const row of daily) {
    byMat[row.material] = (byMat[row.material] ?? 0) + row.qty_needed
  }

  return Object.entries(byMat)
    .sort(([, a], [, b]) => b - a)
    .map(([material, total], i) => ({
      rank: i + 1,
      material,
      total_qty:   Math.round(total * 1000) / 1000,
      avg_per_day: Math.round((total / nDays) * 1000) / 1000,
    }))
}
