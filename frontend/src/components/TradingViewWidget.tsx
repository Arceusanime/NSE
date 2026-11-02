import { useEffect, useRef } from 'react'

export function TradingViewWidget({ symbol, expanded, onToggle }: { symbol: string; expanded: boolean; onToggle: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const holder = ref.current; if (!holder) return
    holder.innerHTML = ''
    const script = document.createElement('script'); script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'; script.async = true
    script.innerHTML = JSON.stringify({ autosize: true, symbol: `NSE:${symbol}`, interval: 'D', timezone: 'Asia/Kolkata', theme: document.documentElement.dataset.theme === 'light' ? 'light' : 'dark', style: '1', locale: 'en', hide_side_toolbar: true, allow_symbol_change: false })
    holder.appendChild(script)
  }, [symbol])
  return <section className={`chart-card ${expanded ? 'fullscreen' : ''}`}><div className="chart-heading"><span>TradingView · NSE:{symbol}</span><button onClick={onToggle}>{expanded ? 'Minimize' : 'Enlarge'}</button></div><div className="tv-container" ref={ref} /></section>
}
