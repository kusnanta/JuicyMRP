import React from 'react'
import type { MrpTotalRow } from '@/lib/types'

interface Props {
  rows: MrpTotalRow[]
}

export function MrpTotalTable({ rows }: Props) {
  if (!rows.length) return <p className="text-sm text-gray-400">Tidak ada data MRP.</p>
  const maxAvg = rows[0]?.avg_per_day || 1

  return (
    <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
      <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
        <thead>
          <tr style={{ background: '#f3f4f6' }}>
            {['Rank','Material','Total qty','Per hari','Distribusi (qty/hari)'].map(h => (
              <th key={h} style={{ padding: '7px 10px', fontWeight: 500, fontSize: 11, color: '#6b7280', borderBottom: '1px solid #e5e7eb', textAlign: h === 'Distribusi (qty/hari)' ? 'left' : h === 'Material' ? 'left' : 'right', whiteSpace: 'nowrap', minWidth: h === 'Distribusi (qty/hari)' ? 160 : undefined }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => {
            const bg = ri % 2 === 1 ? '#f9fafb' : '#fff'
            const pct = Math.round((r.avg_per_day / maxAvg) * 100)
            const opacity = Math.max(0.28, 1 - (r.rank - 1) * 0.075)
            return (
              <tr key={r.material} style={{ borderBottom: '1px solid #f3f4f6', background: bg }}>
                <td style={{ padding: '7px 10px', color: '#9ca3af', fontSize: 11 }}>{r.rank}</td>
                <td style={{ padding: '7px 10px', fontWeight: 500 }}>{r.material}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>{r.total_qty.toFixed(3)}</td>
                <td style={{ padding: '7px 10px', textAlign: 'right', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>{r.avg_per_day.toFixed(3)}</td>
                <td style={{ padding: '7px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ flex: 1, height: 10, background: '#f3f4f6', borderRadius: 3, overflow: 'hidden', minWidth: 60 }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: `rgba(24,95,165,${opacity.toFixed(2)})`, borderRadius: 3 }} />
                    </div>
                    <span style={{ fontSize: 10, color: '#6b7280', fontFamily: "'IBM Plex Mono', monospace", whiteSpace: 'nowrap', flexShrink: 0 }}>
                      {r.avg_per_day.toFixed(3)}/hr
                    </span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
