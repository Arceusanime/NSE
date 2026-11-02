export type ScanResult = {
  rank: number; symbol: string; name: string; instrument_type: 'INDEX' | 'EQUITY'
  previous_open_price: string; max_overall_point_gap: string; max_gap_strike: string | null
  max_gap_side: string | null; macro_spread: string; expiry: string
}
export type ScanList = { scan_id: number; target_trading_date: string | null; status: string; total_instruments: number; successful_instruments: number; items: ScanResult[]; total: number }
export type Level = { strike_price: string; oi: number; oi_change: number; side: 'UPPER' | 'LOWER'; point_gap: string; percentage_gap: string; rank_within_side: number; call_oi: number; put_oi: number }
export type Histogram = { strike_price: string; call_oi: number; put_oi: number; selected_side: 'UPPER' | 'LOWER' | null; selected_rank: number | null }
export type Analysis = { symbol: string; name: string; instrument_type: string; session_date: string; expiry: string; previous_open_price: string; atm_strike: string; max_point_gap: string; macro_spread: string; upper_levels: Level[]; lower_levels: Level[]; histogram: Histogram[] }
export type Health = { status: string; database: string; market_session: string; provider: string; provider_status: string }
