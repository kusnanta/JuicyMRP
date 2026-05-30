import React, { useState, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import Papa from 'papaparse'

import type { SalesRow, BomRow, AllResults, ForecastPoint, MrpTotalRow } from '@/lib/types'
import { flattenForecasts, getBestMethod, ALL_REAL_METHODS, METHOD_DISPLAY } from '@/lib/forecast'
import { calculateDailyMrp, pivotMrp, totalMrp } from '@/lib/mrp'
import { makeSampleSales, makeSampleBom, salesToCsv, bomToCsv } from '@/lib/sample'
import { FcPivotTable, MrpPivotTable, AccPivotTable } from '@/components/PivotTable'
import { MrpTotalTable } from '@/components/MrpTotalTable'
import { MultiSelect } from '@/components/MultiSelect'

const ForecastChart = dynamic(() => import('@/components/ForecastChart'), { ssr: false })

// ── Helpers ───────────────────────────────────────────────────────────
const PROD_COLORS = ['#185FA5','#3B6D11','#854F0B','#A32D2D','#534AB7','#0F6E56','#993C1D']
const pc = (i: number) => PROD_COLORS[i % PROD_COLORS.length]

function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate()+n); return r }
function fmtDate(d: Date) { return d.toISOString().slice(0,10) }
function today0() { const d = new Date(); d.setHours(0,0,0,0); return d }

function downloadCsv(content: string, filename: string) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([content], { type: 'text/csv' }))
  a.download = filename; a.click()
}

function parseCsv<T>(file: File): Promise<T[]> {
  return new Promise((res, rej) => Papa.parse<T>(file, {
    header: true, skipEmptyLines: true, dynamicTyping: true,
    complete: r => res(r.data), error: rej,
  }))
}

function secLabel(text: string) {
  return <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 500, color: '#9ca3af', marginBottom: 8, marginTop: 18 }}>{text}</div>
}

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 16px' }}>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 500, color: '#111827', lineHeight: 1.1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────
export default function Home() {
  const [sales, setSales]         = useState<SalesRow[]>([])
  const [bom, setBom]             = useState<BomRow[]>([])
  const [allResults, setAllResults] = useState<AllResults>({})
  const [loading, setLoading]     = useState(false)
  const [processedAt, setProcessedAt] = useState('')
  const [activeTab, setActiveTab] = useState(0)
  const [selMethod, setSelMethod] = useState<string>('best')

  // Filters
  const [selProds, setSelProds]   = useState<string[]>([])
  const [selMats, setSelMats]     = useState<string[]>([])
  const [dateFrom, setDateFrom]   = useState(() => fmtDate(today0()))
  const [dateTo, setDateTo]       = useState(() => fmtDate(addDays(today0(), 6)))

  const salesRef = useRef<HTMLInputElement>(null)
  const bomRef   = useRef<HTMLInputElement>(null)

  const allProducts  = Object.keys(allResults).sort()
  const allMaterials = [...new Set(bom.map(r => r.material))].sort()
  const activeProds  = selProds.length ? selProds : allProducts
  const activeMats   = selMats.length  ? selMats  : allMaterials

  const fc_df: ForecastPoint[] = flattenForecasts(allResults, selMethod)
  const fc_filtered = fc_df.filter(r => activeProds.includes(r.product_name))

  // Run pipeline via API
  const runPipeline = useCallback(async (s: SalesRow[], b: BomRow[]) => {
    setLoading(true)
    try {
      const res = await fetch('/api/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sales: s, bom: b, horizon: 30 }),
      })
      if (!res.ok) throw new Error(await res.text())
      const { allResults: ar } = await res.json()
      setAllResults(ar)
      setSelProds(Object.keys(ar).sort())
      setSelMats([...new Set(b.map((r: BomRow) => r.material))].sort())
      setProcessedAt(new Date().toLocaleString('id-ID'))
    } finally {
      setLoading(false)
    }
  }, [])

  const loadSample = async () => {
    const s = makeSampleSales(); const b = makeSampleBom()
    setSales(s); setBom(b)
    await runPipeline(s, b)
  }

  const handleSalesUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return
    const rows = await parseCsv<SalesRow>(f)
    setSales(rows)
    if (bom.length) await runPipeline(rows, bom)
  }

  const handleBomUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return
    const rows = await parseCsv<BomRow>(f)
    setBom(rows)
    if (sales.length) await runPipeline(sales, rows)
  }

  // MRP data
  const today = today0()
  const mrpDaily  = calculateDailyMrp(fc_filtered, bom, activeProds, dateFrom, dateTo)
  const mrpDailyF = mrpDaily.filter(r => activeMats.includes(r.material))
  const pivotData = pivotMrp(mrpDailyF)
  const totalData: MrpTotalRow[] = totalMrp(fc_filtered, bom, activeProds, dateFrom, dateTo)
    .filter(r => activeMats.includes(r.material))

  // Dashboard-specific
  const mrp3 = totalMrp(fc_filtered, bom, activeProds,
    fmtDate(today), fmtDate(addDays(today, 2)))
  const topMat = mrp3[0]
  const dates7 = Array.from({ length: 7 }, (_, i) => fmtDate(addDays(today, i)))
  const dateRange = Array.from({ length: (new Date(dateTo).getTime() - new Date(dateFrom).getTime()) / 86400000 + 1 }, (_, i) => fmtDate(addDays(new Date(dateFrom), i)))

  const total30 = fc_filtered.reduce((s, r) => s + r.forecast_qty, 0)
  const avgAcc = (() => {
    const accs = activeProds.map(p => fc_filtered.find(r => r.product_name === p && r.accuracy_pct !== null)?.accuracy_pct).filter((v): v is number => v !== null)
    return accs.length ? accs.reduce((s,v)=>s+v,0)/accs.length : null
  })()

  // ── Tabs ─────────────────────────────────────────────────────────
  const tabs = ['📊 Dashboard','🔮 Forecast','⚙️ MRP','📁 Raw data']

  return (
    <div style={{ minHeight: '100vh', background: '#f9fafb' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 20px' }}>

        {/* Header */}
        <div style={{ marginBottom: 20 }}>
          <span style={{ fontSize: '1.55rem', fontWeight: 800, letterSpacing: '-0.04em', color: '#111827' }}>
            📊 Forecasting &amp; MRP Dashboard
          </span>
          <span style={{ fontSize: '.72rem', color: '#9ca3af', marginLeft: 14, letterSpacing: '.1em', textTransform: 'uppercase' as const, fontWeight: 600 }}>
            Sales Forecast · MRP · Vercel Edition
          </span>
        </div>

        {/* Upload */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
          {[
            { label: 'Historical sales CSV', hint: 'date, product_name, sales_qty', ref: salesRef, onChange: handleSalesUpload, sample: () => downloadCsv(salesToCsv(makeSampleSales()), 'sample_sales.csv') },
            { label: 'Raw material BOM CSV', hint: 'product_name, material, component_qty', ref: bomRef, onChange: handleBomUpload, sample: () => downloadCsv(bomToCsv(makeSampleBom()), 'sample_bom.csv') },
          ].map(u => (
            <div key={u.label} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 16px', background: '#fff' }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 }}>{u.label}</div>
              <div style={{ fontSize: 11, color: '#9ca3af', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>{u.hint}</div>
              <input type="file" accept=".csv" ref={u.ref} style={{ display: 'none' }} onChange={u.onChange} />
              <button onClick={() => u.ref.current?.click()} style={{ width: '100%', padding: 7, fontSize: 12, borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', marginBottom: 6 }}>
                ⬆ Upload CSV
              </button>
              <button onClick={u.sample} style={{ width: '100%', padding: 5, fontSize: 11, borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', background: 'transparent', color: '#9ca3af' }}>
                ⬇ Download sample
              </button>
            </div>
          ))}
        </div>

        {/* Run button */}
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={loadSample}
            disabled={loading}
            style={{ padding: '8px 20px', fontSize: 13, fontWeight: 600, borderRadius: 8, border: 'none', background: loading ? '#9ca3af' : 'linear-gradient(135deg,#1a56db,#0e9f6e)', color: '#fff', cursor: loading ? 'not-allowed' : 'pointer', marginRight: 10 }}
          >
            {loading ? '⏳ Processing…' : '🚀 Run dengan sample data'}
          </button>
          {processedAt && <span style={{ fontSize: 11, color: '#9ca3af' }}>🕐 {processedAt}</span>}
        </div>

        {/* Filters */}
        {allProducts.length > 0 && (
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: '10px 14px', marginBottom: 16, background: '#fff', display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4, fontWeight: 500 }}>Rentang tanggal (MRP &amp; tabel)</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #e5e7eb' }} />
                <span style={{ color: '#9ca3af', fontSize: 11 }}>–</span>
                <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #e5e7eb' }} />
                <button onClick={() => { setDateFrom(fmtDate(today0())); setDateTo(fmtDate(addDays(today0(),6))) }} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', background: 'transparent', color: '#9ca3af' }}>Reset</button>
              </div>
            </div>
            <MultiSelect label="Produk" options={allProducts} selected={selProds} onChange={setSelProds} badge={`(${selProds.length}/${allProducts.length})`} />
            <MultiSelect label="Material (MRP)" options={allMaterials} selected={selMats} onChange={setSelMats} badge={`(${selMats.length}/${allMaterials.length})`} />
          </div>
        )}

        {/* Empty state */}
        {!allProducts.length && !loading && (
          <div style={{ textAlign: 'center', padding: '60px 40px', border: '1px dashed #e5e7eb', borderRadius: 16, background: '#fff' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>📊</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 8 }}>Siap memulai</div>
            <div style={{ color: '#9ca3af', fontSize: '.88rem' }}>
              Upload CSV atau klik <strong>Run dengan sample data</strong>
            </div>
          </div>
        )}

        {/* Tabs */}
        {allProducts.length > 0 && (
          <>
            <div style={{ display: 'flex', gap: 5, marginBottom: 16 }}>
              {tabs.map((t, i) => (
                <button key={i} onClick={() => setActiveTab(i)} style={{
                  padding: '5px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                  background: activeTab === i ? '#dbeafe' : '#f3f4f6',
                  color: activeTab === i ? '#1e40af' : '#6b7280',
                  border: activeTab === i ? '1px solid #bfdbfe' : '1px solid #e5e7eb',
                }}>{t}</button>
              ))}
            </div>

            {/* ── DASHBOARD ── */}
            {activeTab === 0 && (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 16 }}>
                  <KpiCard label="Total forecast 30H" value={Math.round(total30).toLocaleString()} sub={`${activeProds.length} produk`} />
                  <KpiCard label="Rata-rata akurasi" value={avgAcc !== null ? `${avgAcc.toFixed(1)}%` : 'N/A'} sub="100% − MAPE" />
                  <KpiCard label="Material teratas (3H)" value={topMat?.material ?? '—'} sub={topMat ? `${topMat.total_qty.toFixed(3)} unit` : '—'} />
                  <KpiCard label="Total material" value={String(allMaterials.length)} sub="bahan baku aktif" />
                </div>

                {secLabel('Historical 30H + Forecast 30 hari ke depan')}
                <div style={{ overflow: 'hidden', borderRadius: 10, border: '1px solid #e5e7eb', background: '#fff', marginBottom: 16 }}>
                  <ForecastChart sales={sales} forecasts={fc_filtered} products={activeProds} histDays={30} dateFrom={dateFrom} dateTo={dateTo} height={280} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div>
                    {secLabel('Forecast qty produk — 7 hari ke depan')}
                    <FcPivotTable forecasts={fc_filtered} products={activeProds} dates={dates7} />
                  </div>
                  <div>
                    {secLabel('Kebutuhan beli material — 3 hari ke depan')}
                    {(() => {
                      const d3Dates = [fmtDate(today), fmtDate(addDays(today,1)), fmtDate(addDays(today,2))]
                      const d3 = calculateDailyMrp(fc_filtered, bom, activeProds, fmtDate(today), fmtDate(addDays(today,2)))
                      const pv = pivotMrp(d3)
                      return <MrpPivotTable {...pv} />
                    })()}
                  </div>
                </div>
              </div>
            )}

            {/* ── FORECAST ── */}
            {activeTab === 1 && (
              <div>
                {secLabel('Metode forecast')}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
                  {(['best', ...ALL_REAL_METHODS as string[]]).map(m => (
                    <button key={m} onClick={() => setSelMethod(m)} style={{
                      padding: '5px 12px', fontSize: 11, fontWeight: 500, cursor: 'pointer',
                      border: `1px solid ${selMethod===m?'#bfdbfe':'#e5e7eb'}`,
                      background: selMethod===m?'#dbeafe':'transparent',
                      color: selMethod===m?'#1e40af':'#6b7280',
                      borderRadius: 6,
                    }}>
                      {m === 'best' ? '⭐ ' : ''}{METHOD_DISPLAY[m] ?? m}
                    </button>
                  ))}
                  {selMethod === 'best' && activeProds.length > 0 && (
                    <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 4 }}>
                      Auto-pilih: {activeProds.map(p => `${p}: ${getBestMethod(allResults[p]??{})}`).join(' · ')}
                    </span>
                  )}
                </div>

                {secLabel('Historical 30H + Forecast 30 hari ke depan')}
                <div style={{ overflow: 'hidden', borderRadius: 10, border: '1px solid #e5e7eb', background: '#fff', marginBottom: 16 }}>
                  <ForecastChart sales={sales} forecasts={fc_filtered} products={activeProds} histDays={30} dateFrom={dateFrom} dateTo={dateTo} height={280} />
                </div>

                {secLabel('Forecast qty produk — pivot (date range filter)')}
                <FcPivotTable forecasts={fc_filtered} products={activeProds} dates={dateRange} />

                {secLabel('Akurasi forecast per produk × metode — hijau = akurasi tertinggi per produk')}
                <AccPivotTable
                  allResults={allResults}
                  products={activeProds}
                  methods={ALL_REAL_METHODS as string[]}
                  methodLabels={METHOD_DISPLAY}
                  selectedMethod={selMethod}
                  getBestMethod={(r) => getBestMethod(r as AllResults[string])}
                />

                {secLabel('Detail forecast (date range filter)')}
                <div style={{ overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, marginBottom: 8 }}>
                  <table style={{ borderCollapse: 'collapse', fontSize: 11, minWidth: '100%' }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6' }}>
                        {['Tanggal','Produk','Forecast','Lower','Upper','Akurasi','Metode'].map(h=>(
                          <th key={h} style={{ padding: '6px 10px', fontWeight: 500, color: '#6b7280', borderBottom: '1px solid #e5e7eb', textAlign: ['Akurasi','Metode'].includes(h)?'center':'right', ...(h==='Tanggal'||h==='Produk'?{textAlign:'left'}:{}) }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {fc_filtered
                        .filter(r => r.forecast_date >= dateFrom && r.forecast_date <= dateTo)
                        .slice(0, 15)
                        .map((r, i) => {
                          const acc = r.accuracy_pct
                          const accColor = acc===null?'#9ca3af':acc>=90?'#15803d':acc>=80?'#b45309':'#b91c1c'
                          const mBg = r.model_used.includes('prophet')?'background:#dbeafe;color:#1e40af':r.model_used.includes('holt')?'background:#fef3c7;color:#92400e':'background:#f3f4f6;color:#374151'
                          return (
                            <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: i%2?'#f9fafb':'#fff' }}>
                              <td style={{ padding: '5px 10px', color: '#9ca3af', fontFamily: "'IBM Plex Mono',monospace" }}>{r.forecast_date}</td>
                              <td style={{ padding: '5px 10px', fontWeight: 500 }}>{r.product_name}</td>
                              <td style={{ padding: '5px 10px', textAlign: 'right', fontFamily: "'IBM Plex Mono',monospace" }}>{r.forecast_qty.toFixed(1)}</td>
                              <td style={{ padding: '5px 10px', textAlign: 'right', color: '#9ca3af', fontFamily: "'IBM Plex Mono',monospace" }}>{r.forecast_lower.toFixed(1)}</td>
                              <td style={{ padding: '5px 10px', textAlign: 'right', color: '#9ca3af', fontFamily: "'IBM Plex Mono',monospace" }}>{r.forecast_upper.toFixed(1)}</td>
                              <td style={{ padding: '5px 10px', textAlign: 'center', color: accColor, fontWeight: 500 }}>{acc?.toFixed(1) ?? '—'}%</td>
                              <td style={{ padding: '5px 10px', textAlign: 'center' }}>
                                <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 5, ...Object.fromEntries(mBg.split(';').map(s=>{const[k,v]=s.split(':');return[k?.trim().replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),v?.trim()]})) }}>{r.model_used}</span>
                              </td>
                            </tr>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
                <button onClick={() => {
                  const rows = fc_filtered.filter(r => r.forecast_date >= dateFrom && r.forecast_date <= dateTo)
                  const csv = ['forecast_date,product_name,forecast_qty,forecast_lower,forecast_upper,accuracy_pct,model_used',
                    ...rows.map(r=>`${r.forecast_date},${r.product_name},${r.forecast_qty},${r.forecast_lower},${r.forecast_upper},${r.accuracy_pct??''},${r.model_used}`)].join('\n')
                  downloadCsv(csv, `forecast_${dateFrom}_${dateTo}.csv`)
                }} style={{ fontSize: 11, padding: '5px 12px', borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', background: '#fff', color: '#6b7280' }}>
                  ⬇ Download forecast CSV
                </button>
              </div>
            )}

            {/* ── MRP ── */}
            {activeTab === 2 && (
              <div>
                <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8 }}>
                  Produk: <strong style={{ color: '#374151' }}>{activeProds.length === allProducts.length ? 'Semua produk' : `${activeProds.length} produk`}</strong> ·
                  Periode: <strong style={{ color: '#374151' }}>{dateFrom} – {dateTo}</strong> ·
                  Material: <strong style={{ color: '#374151' }}>{activeMats.length} dipilih</strong>
                </p>

                {secLabel('Kebutuhan pembelian per hari (material × tanggal)')}
                <MrpPivotTable {...pivotData} />
                <button onClick={() => {
                  const rows = ['material,order_date,qty_needed', ...mrpDailyF.map(r=>`${r.material},${r.order_date},${r.qty_needed}`)].join('\n')
                  downloadCsv(rows, `mrp_pivot_${dateFrom}_${dateTo}.csv`)
                }} style={{ fontSize: 11, padding: '5px 12px', borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', background: '#fff', color: '#6b7280', marginBottom: 8 }}>
                  ⬇ Pivot CSV
                </button>

                {secLabel('Total kebutuhan (rentang filter) — diurutkan dari tertinggi')}
                <MrpTotalTable rows={totalData} />
                <button onClick={() => {
                  const rows = ['rank,material,total_qty,avg_per_day', ...totalData.map(r=>`${r.rank},${r.material},${r.total_qty},${r.avg_per_day}`)].join('\n')
                  downloadCsv(rows, `mrp_total_${dateFrom}_${dateTo}.csv`)
                }} style={{ fontSize: 11, padding: '5px 12px', borderRadius: 6, border: '1px solid #e5e7eb', cursor: 'pointer', background: '#fff', color: '#6b7280', marginTop: 8 }}>
                  ⬇ Total MRP CSV
                </button>
              </div>
            )}

            {/* ── RAW DATA ── */}
            {activeTab === 3 && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                {[
                  { title: 'Sales data', cols: ['date','product_name','sales_qty'], rows: sales.slice(0,8) as Record<string,unknown>[] },
                  { title: 'BOM data', cols: ['product_name','material','component_qty'], rows: bom as Record<string,unknown>[] },
                ].map(({ title, cols, rows }) => (
                  <div key={title}>
                    {secLabel(title)}
                    <div style={{ overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
                      <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
                        <thead><tr style={{ background: '#f3f4f6' }}>
                          {cols.map(c => <th key={c} style={{ padding: '6px 8px', fontWeight: 500, color: '#6b7280', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>{c}</th>)}
                        </tr></thead>
                        <tbody>
                          {rows.map((r, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: i%2?'#f9fafb':'#fff' }}>
                              {cols.map(c => <td key={c} style={{ padding: '5px 8px', color: '#374151', fontFamily: typeof r[c] === 'number' ? "'IBM Plex Mono',monospace" : undefined, fontSize: 11 }}>{String(r[c])}</td>)}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Footer */}
        <div style={{ marginTop: 32, paddingTop: 16, borderTop: '1px solid #e5e7eb', fontSize: 11, color: '#d1d5db', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <span>🕐 {processedAt || '—'}</span>
          <span>Horizon: 30 hari</span>
          <span>Metode aktif: {selMethod}</span>
          <a href="https://github.com" style={{ marginLeft: 'auto', color: '#9ca3af', textDecoration: 'none' }}>GitHub ↗</a>
        </div>
      </div>
    </div>
  )
}
