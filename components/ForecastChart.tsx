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
      const Plotly = mod as unknown as PlotlySubset

      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const histStart = new Date(today)
      histStart.setDate(histStart.getDate() - histDays)
      const todayStr = today.toISOString().slice(0, 10)
      const histStr  = histStart.toISOString().slice(0, 10)

      const traces: object[] = []

      // ── Highlight band for filter date range ──────────────────────
      // Use null y-values + fill — Plotly autoscales, band stays invisible
      if (dateFrom && dateTo) {
        traces.push({
          x: [dateFrom, dateTo],
          y: [null, null],           // no actual data — won't distort y-axis
          type: 'scatter',
          mode: 'none',
          fill: 'tozeroy',
          fillcolor: 'rgba(26,86,219,0.06)',
          showlegend: false,
          hoverinfo: 'skip',
        })
      }

      products.forEach((p, idx) => {
        const c  = PROD_COLORS[idx % PROD_COLORS.length]
        const cl = PROD_COLORS_LIGHT[idx % PROD_COLORS_LIGHT.length]

        // Historical solid line
        const hist = sales
          .filter(r => r.product_name === p && r.date >= histStr && r.date < todayStr)
          .sort((a, b) => a.date.localeCompare(b.date))

        if (hist.length) {
          traces.push({
            x: hist.map(r => r.date),
            y: hist.map(r => r.sales_qty),
            type: 'scatter',
            mode: 'lines',
            name: `${p} — aktual`,
            line: { color: c, width: 1.8 },
            opacity: 0.85,
            legendgroup: p,
          })
        }

        // Forecast CI band + dashed line
        const fc = forecasts
          .filter(r => r.product_name === p)
          .sort((a, b) => a.forecast_date.localeCompare(b.forecast_date))

        if (fc.length) {
          const fcDates = fc.map(r => r.forecast_date)
          const bandX   = [...fcDates, ...[...fcDates].reverse()]
          const bandY   = [
            ...fc.map(r => r.forecast_upper),
            ...[...fc].reverse().map(r => r.forecast_lower),
          ]

          traces.push({
            x: bandX,
            y: bandY,
            type: 'scatter',
            fill: 'toself',
            fillcolor: cl + '55',
            line: { color: 'rgba(0,0,0,0)' },
            showlegend: false,
            hoverinfo: 'skip',
            legendgroup: p,
          })

          traces.push({
            x: fcDates,
            y: fc.map(r => r.forecast_qty),
            type: 'scatter',
            mode: 'lines',
            name: `${p} — forecast`,
            line: { color: c, width: 2, dash: 'dot' },
            legendgroup: p,
          })
        }
      })

      // ── "Today" vertical line via shape (not a trace) ──────────────
      // Using shapes avoids adding a data point that could distort y-axis
      const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor:  'rgba(0,0,0,0)',
        height,
        margin: { l: 48, r: 8, t: 8, b: 40 },
        hovermode: 'x unified',
        legend: {
          bgcolor: 'rgba(0,0,0,0)',
          borderwidth: 0,
          font: { size: 10 },
        },
        xaxis: {
          gridcolor: 'rgba(0,0,0,0.05)',
          tickformat: '%d %b',
          type: 'date',
          showline: false,
        },
        yaxis: {
          gridcolor: 'rgba(0,0,0,0.05)',
          showline: false,
          rangemode: 'tozero',
          // do NOT set a fixed range — let Plotly autoscale from real data
        },
        font: { family: 'IBM Plex Sans', size: 11, color: '#6b7280' },
        shapes: [
          // "Today" vertical dashed line — uses axis-relative coords, no y-data
          {
            type: 'line',
            x0: todayStr,
            x1: todayStr,
            y0: 0,
            y1: 1,
            yref: 'paper',   // 0=bottom, 1=top of plot area — not data units
            line: { color: 'rgba(0,0,0,0.18)', dash: 'dot', width: 1 },
          },
        ],
        annotations: [
          {
            x: todayStr,
            y: 1,
            yref: 'paper',
            xanchor: 'left',
            yanchor: 'top',
            text: 'Hari ini',
            showarrow: false,
            font: { size: 9, color: '#9ca3af' },
            xshift: 4,
          },
        ],
      }

      Plotly.react(divRef.current!, traces, layout, {
        responsive: true,
        displayModeBar: false,
      })
    })

    return () => { cancelled = true }
  }, [sales, forecasts, products, histDays, dateFrom, dateTo, height])

  return <div ref={divRef} style={{ width: '100%', height }} />
}
