'use client'
import React, { useEffect, useRef } from 'react'
import type { SalesRow, ForecastPoint } from '@/lib/types'

const PROD_COLORS       = ['#185FA5','#3B6D11','#854F0B','#A32D2D','#534AB7','#0F6E56','#993C1D']
const PROD_COLORS_LIGHT = ['#B5D4F4','#C0DD97','#FAC775','#F09595','#AFA9EC','#9FE1CB','#F5C4B3']

interface Props {
  sales: SalesRow[]
  forecasts: ForecastPoint[]
  products: string[]
  histDays?: number
  dateFrom?: string
  dateTo?: string
  height?: number
}

// Minimal subset of the Plotly API we actually call
interface PlotlySubset {
  react: (
    root: HTMLElement,
    data: object[],
    layout: object,
    config?: object,
  ) => Promise<void>
}

export default function ForecastChart({
  sales, forecasts, products,
  histDays = 30, dateFrom, dateTo, height = 280,
}: Props) {
  const divRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!divRef.current) return
    let cancelled = false

    import('plotly.js-dist-min').then((mod) => {
      if (cancelled || !divRef.current) return

      // Cast to our minimal interface — avoids depending on exact @types/plotly.js version
      const Plotly = mod as unknown as PlotlySubset

      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const histStart = new Date(today)
      histStart.setDate(histStart.getDate() - histDays)
      const todayStr = today.toISOString().slice(0, 10)
      const histStr  = histStart.toISOString().slice(0, 10)

      const traces: object[] = []

      // Highlight band for filter date range
      if (dateFrom && dateTo) {
        traces.push({
          x: [dateFrom, dateTo, dateTo, dateFrom, dateFrom],
          y: [0, 0, 1e9, 1e9, 0],
          fill: 'toself',
          fillcolor: 'rgba(26,86,219,0.05)',
          line: { width: 0 },
          showlegend: false,
          hoverinfo: 'skip',
          type: 'scatter',
        })
      }

      products.forEach((p, idx) => {
        const c  = PROD_COLORS[idx % PROD_COLORS.length]
        const cl = PROD_COLORS_LIGHT[idx % PROD_COLORS_LIGHT.length]

        // Historical
        const hist = sales
          .filter(r => r.product_name === p && r.date >= histStr && r.date < todayStr)
          .sort((a, b) => a.date.localeCompare(b.date))

        if (hist.length) {
          traces.push({
            x: hist.map(r => r.date),
            y: hist.map(r => r.sales_qty),
            mode: 'lines',
            name: `${p} — aktual`,
            line: { color: c, width: 1.8 },
            opacity: 0.85,
            legendgroup: p,
            type: 'scatter',
          })
        }

        // Forecast CI band + dashed line
        const fc = forecasts
          .filter(r => r.product_name === p)
          .sort((a, b) => a.forecast_date.localeCompare(b.forecast_date))

        if (fc.length) {
          const fcDates = fc.map(r => r.forecast_date)
          const bandX   = [...fcDates, ...[...fcDates].reverse()]
          const bandY   = [...fc.map(r => r.forecast_upper), ...[...fc].reverse().map(r => r.forecast_lower)]

          traces.push({
            x: bandX, y: bandY,
            fill: 'toself',
            fillcolor: cl + '55',
            line: { color: 'rgba(0,0,0,0)' },
            showlegend: false,
            hoverinfo: 'skip',
            legendgroup: p,
            type: 'scatter',
          })

          traces.push({
            x: fcDates,
            y: fc.map(r => r.forecast_qty),
            mode: 'lines',
            name: `${p} — forecast`,
            line: { color: c, width: 2, dash: 'dot' },
            legendgroup: p,
            type: 'scatter',
          })
        }
      })

      // "Today" vertical line
      traces.push({
        x: [todayStr, todayStr],
        y: [0, 1e9],
        mode: 'lines',
        line: { color: 'rgba(0,0,0,0.15)', dash: 'dot', width: 1 },
        showlegend: false,
        hoverinfo: 'skip',
        type: 'scatter',
      })

      const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor:  'rgba(0,0,0,0)',
        height,
        margin: { l: 40, r: 8, t: 8, b: 40 },
        hovermode: 'x unified',
        legend: { bgcolor: 'rgba(0,0,0,0)', borderwidth: 0, font: { size: 10 } },
        xaxis: { gridcolor: 'rgba(0,0,0,0.05)', tickformat: '%d %b', type: 'date', showline: false },
        yaxis: { gridcolor: 'rgba(0,0,0,0.05)', showline: false, rangemode: 'tozero' },
        font: { family: 'IBM Plex Sans', size: 11, color: '#6b7280' },
      }

      Plotly.react(divRef.current!, traces, layout, { responsive: true, displayModeBar: false })
    })

    return () => { cancelled = true }
  }, [sales, forecasts, products, histDays, dateFrom, dateTo, height])

  return <div ref={divRef} style={{ width: '100%', height }} />
}
