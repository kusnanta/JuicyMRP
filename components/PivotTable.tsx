import React from 'react'
import type { ForecastPoint } from '@/lib/types'

const PROD_COLORS = ['#185FA5','#3B6D11','#854F0B','#A32D2D','#534AB7','#0F6E56','#993C1D']
const pc = (i: number) => PROD_COLORS[i % PROD_COLORS.length]

function fmtShort(ds: string): string {
  const d = new Date(ds + 'T00:00:00')
  return `${d.getMonth()+1}/${d.getDate()}`
}

// ── Forecast pivot: product × date ───────────────────────────────────
interface FcPivotProps {
  forecasts: ForecastPoint[]
  products: string[]
  dates: string[]       // YYYY-MM-DD strings
}

export function FcPivotTable({ forecasts, products, dates }: FcPivotProps) {
  const lookup: Record<string, number> = {}
  forecasts.forEach(f => { lookup[`${f.product_name}||${f.forecast_date}`] = f.forecast_qty })

  return (
    <div className="pivot-wrap">
      <table className="pivot-tbl">
        <thead>
          <tr>
            <th className="tl">Produk</th>
            {dates.map(d => <th key={d}>{fmtShort(d)}</th>)}
            <th className="tot">Total</th>
          </tr>
        </thead>
        <tbody>
          {products.map((p, ri) => {
            const vals = dates.map(d => lookup[`${p}||${d}`] ?? 0)
            const total = vals.reduce((s, v) => s + v, 0)
            return (
              <tr key={p}>
                <td className="tl">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: pc(ri), display: 'inline-block', flexShrink: 0 }} />
                    {p}
                  </span>
                </td>
                {vals.map((v, i) => <td key={i}>{v.toFixed(1)}</td>)}
                <td className="tot">{total.toFixed(1)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── MRP pivot: material × date ────────────────────────────────────────
interface MrpPivotData {
  materials: string[]
  dates: string[]
  data: Record<string, Record<string, number>>
  totals: Record<string, number>
}

export function MrpPivotTable({ materials, dates, data, totals }: MrpPivotData) {
  if (!materials.length) return <p className="text-sm text-gray-400">Tidak ada data MRP.</p>
  return (
    <div className="pivot-wrap">
      <table className="pivot-tbl">
        <thead>
          <tr>
            <th className="tl">Material</th>
            <th className="tot">TOTAL</th>
            {dates.map(d => <th key={d}>{fmtShort(d)}</th>)}
          </tr>
        </thead>
        <tbody>
          {materials.map((m, ri) => (
            <tr key={m}>
              <td className="tl">{m}</td>
              <td className="tot">{(totals[m] ?? 0).toFixed(3)}</td>
              {dates.map(d => {
                const v = data[m]?.[d] ?? 0
                return <td key={d} style={{ color: v > 0 ? '#111827' : '#d1d5db' }}>{v.toFixed(3)}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Accuracy pivot: product × method ─────────────────────────────────
interface AccPivotProps {
  allResults: Record<string, Record<string, ForecastPoint[]>>
  products: string[]
  methods: string[]
  methodLabels: Record<string, string>
  selectedMethod: string
  getBestMethod: (r: Record<string, ForecastPoint[]>) => string
}

export function AccPivotTable({ allResults, products, methods, methodLabels, selectedMethod, getBestMethod }: AccPivotProps) {
  return (
    <div className="pivot-wrap">
      <table className="acc-tbl">
        <thead>
          <tr>
            <th className="tl">Produk</th>
            {methods.map(m => (
              <th key={m} className={selectedMethod === m ? 'active-col' : ''} style={{ color: selectedMethod === m ? '#1a56db' : undefined }}>
                {selectedMethod === m ? '✓ ' : ''}{methodLabels[m] ?? m}
              </th>
            ))}
            <th>Metode aktif</th>
          </tr>
        </thead>
        <tbody>
          {products.map((p, ri) => {
            const mr = allResults[p] ?? {}
            const accs: Record<string, number | null> = {}
            methods.forEach(m => {
              const pts = mr[m]
              accs[m] = pts?.find(pt => pt.accuracy_pct !== null)?.accuracy_pct ?? null
            })
            const validAccs = Object.values(accs).filter((v): v is number => v !== null)
            const maxAcc = validAccs.length ? Math.max(...validAccs) : null
            const eff = selectedMethod === 'best' ? getBestMethod(mr) : (mr[selectedMethod] ? selectedMethod : getBestMethod(mr))
            const color = pc(ri)
            const effMethod = methodLabels[eff] ?? eff
            const effBg = eff.includes('prophet') ? 'background:#dbeafe;color:#1e40af' : eff.includes('holt') ? 'background:#fef3c7;color:#92400e' : 'background:#f3f4f6;color:#374151'
            return (
              <tr key={p}>
                <td className="tl">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
                    {p}
                  </span>
                </td>
                {methods.map(m => {
                  const acc = accs[m]
                  const isBest = acc !== null && maxAcc !== null && Math.abs(acc - maxAcc) < 0.01
                  const isActive = m === eff
                  return (
                    <td key={m} className={isActive ? 'active-col' : ''}>
                      {acc === null ? <span className="na-val" style={{ color: '#d1d5db', fontSize: 11 }}>—</span>
                        : isBest ? <span className="best-badge">{acc.toFixed(1)}%</span>
                        : <span className="other-val">{acc.toFixed(1)}%</span>}
                    </td>
                  )
                })}
                <td>
                  <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 5, display: 'inline-block', ...Object.fromEntries(effBg.split(';').map(s => { const [k,v]=s.split(':'); return [k?.trim().replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),v?.trim()] })) }}>
                    {eff}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
