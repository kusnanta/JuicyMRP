export interface SalesRow {
  date: string          // YYYY-MM-DD
  product_name: string
  sales_qty: number
}

export interface BomRow {
  product_name: string
  material: string
  component_qty: number
}

export type MethodKey = 'prophet' | 'sarima' | 'naive'

export interface ForecastPoint {
  forecast_date: string   // YYYY-MM-DD
  product_name: string
  forecast_qty: number
  forecast_lower: number
  forecast_upper: number
  accuracy_pct: number | null
  model_used: MethodKey
}

export interface MethodResults {
  [method: string]: ForecastPoint[]
}

export interface AllResults {
  [product: string]: MethodResults
}

export interface MrpDailyRow {
  order_date: string
  material: string
  qty_needed: number
}

export interface MrpTotalRow {
  rank: number
  material: string
  total_qty: number
  avg_per_day: number
}

export interface DashboardState {
  dfSales: SalesRow[]
  dfBom: BomRow[]
  allResults: AllResults
  processedAt: string
}
