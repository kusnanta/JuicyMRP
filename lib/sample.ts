/**
 * lib/sample.ts — generates reproducible sample data for demo.
 */

import type { SalesRow, BomRow } from './types'

function addDays(d: Date, n: number): Date {
  const r = new Date(d); r.setDate(r.getDate() + n); return r
}
function fmt(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// LCG RNG for reproducibility
function makeLcg(seed: number) {
  let s = seed
  return (mn: number, mx: number) => {
    s = (s * 1664525 + 1013904223) & 0xffffffff
    return mn + ((s >>> 0) / 0xffffffff) * (mx - mn)
  }
}

export function makeSampleSales(nDays = 180): SalesRow[] {
  const rand = makeLcg(42)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const products = [
    { name: 'Kopi Susu',    base: 25, std: 6 },
    { name: 'Matcha Latte', base: 18, std: 5 },
    { name: 'Croissant',    base: 40, std: 10 },
    { name: 'Sandwich',     base: 30, std: 8 },
    { name: 'Smoothie',     base: 15, std: 4 },
  ]
  const rows: SalesRow[] = []
  for (let i = 0; i < nDays; i++) {
    const d = addDays(today, i - nDays)
    for (const p of products) {
      const dow = (d.getDay() === 0 || d.getDay() === 6) ? 1.3 : 1
      const trend = 1 + 0.0003 * i
      const qty = Math.max(0, Math.round(p.base * dow * trend + rand(-p.std, p.std)))
      rows.push({ date: fmt(d), product_name: p.name, sales_qty: qty })
    }
  }
  return rows
}

export function makeSampleBom(): BomRow[] {
  return [
    { product_name: 'Kopi Susu',    material: 'Susu Segar',     component_qty: 0.15 },
    { product_name: 'Kopi Susu',    material: 'Kopi Bubuk',     component_qty: 0.015 },
    { product_name: 'Kopi Susu',    material: 'Gula Pasir',     component_qty: 0.02 },
    { product_name: 'Kopi Susu',    material: 'Es Batu',        component_qty: 0.1 },
    { product_name: 'Matcha Latte', material: 'Susu Segar',     component_qty: 0.18 },
    { product_name: 'Matcha Latte', material: 'Matcha Powder',  component_qty: 0.01 },
    { product_name: 'Matcha Latte', material: 'Gula Pasir',     component_qty: 0.015 },
    { product_name: 'Matcha Latte', material: 'Es Batu',        component_qty: 0.08 },
    { product_name: 'Croissant',    material: 'Tepung Terigu',  component_qty: 0.08 },
    { product_name: 'Croissant',    material: 'Mentega',        component_qty: 0.04 },
    { product_name: 'Croissant',    material: 'Telur',          component_qty: 0.05 },
    { product_name: 'Croissant',    material: 'Gula Pasir',     component_qty: 0.01 },
    { product_name: 'Sandwich',     material: 'Roti Tawar',     component_qty: 0.1 },
    { product_name: 'Sandwich',     material: 'Daging Ayam',    component_qty: 0.08 },
    { product_name: 'Sandwich',     material: 'Sayuran Mix',    component_qty: 0.05 },
    { product_name: 'Smoothie',     material: 'Buah Mix',       component_qty: 0.2 },
    { product_name: 'Smoothie',     material: 'Susu Segar',     component_qty: 0.1 },
    { product_name: 'Smoothie',     material: 'Es Batu',        component_qty: 0.15 },
    { product_name: 'Smoothie',     material: 'Madu',           component_qty: 0.015 },
  ]
}

export function salesToCsv(rows: SalesRow[]): string {
  return ['date,product_name,sales_qty', ...rows.map(r => `${r.date},${r.product_name},${r.sales_qty}`)].join('\n')
}

export function bomToCsv(rows: BomRow[]): string {
  return ['product_name,material,component_qty', ...rows.map(r => `${r.product_name},${r.material},${r.component_qty}`)].join('\n')
}
