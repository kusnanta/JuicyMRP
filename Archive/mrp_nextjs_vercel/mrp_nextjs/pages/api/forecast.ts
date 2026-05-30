/**
 * pages/api/forecast.ts
 * POST body: { sales: SalesRow[], bom: BomRow[], horizon?: number }
 * Returns: { allResults: AllResults }
 */

import type { NextApiRequest, NextApiResponse } from 'next'
import { runAllForecasts } from '@/lib/forecast'
import type { SalesRow, BomRow } from '@/lib/types'

export const config = { api: { bodyParser: { sizeLimit: '10mb' } } }

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { sales, bom, horizon = 30 } = req.body as {
      sales: SalesRow[]
      bom: BomRow[]
      horizon?: number
    }

    if (!Array.isArray(sales) || !Array.isArray(bom)) {
      return res.status(400).json({ error: 'sales and bom must be arrays' })
    }

    const allResults = runAllForecasts(sales, Math.min(horizon, 90))
    return res.status(200).json({ allResults })
  } catch (err) {
    console.error('[/api/forecast]', err)
    return res.status(500).json({ error: String(err) })
  }
}
