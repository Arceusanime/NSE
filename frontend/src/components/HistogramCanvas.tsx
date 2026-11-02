import { useEffect, useRef } from 'react'
import type { Analysis } from '../types'

export function HistogramCanvas({ analysis }: { analysis: Analysis }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const parent = canvas.parentElement
    if (!parent) return
    const draw = () => {
      const ratio = window.devicePixelRatio || 1
      const width = parent.clientWidth
      const height = 300
      canvas.width = width * ratio; canvas.height = height * ratio
      canvas.style.width = `${width}px`; canvas.style.height = `${height}px`
      const ctx = canvas.getContext('2d'); if (!ctx) return
      ctx.scale(ratio, ratio); ctx.clearRect(0, 0, width, height)
      const values = analysis.histogram
      const max = Math.max(...values.map(x => Math.max(x.call_oi, x.put_oi)), 1)
      const pad = { left: 42, right: 18, top: 18, bottom: 32 }
      const chartWidth = Math.max(1, width - pad.left - pad.right)
      const chartHeight = height - pad.top - pad.bottom
      const barWidth = chartWidth / Math.max(values.length, 1)
      ctx.font = '11px Inter, sans-serif'; ctx.textAlign = 'center'
      values.forEach((item, i) => {
        const x = pad.left + i * barWidth + barWidth / 2
        const callH = item.call_oi / max * chartHeight
        const putH = item.put_oi / max * chartHeight
        ctx.fillStyle = '#25c58a'; ctx.fillRect(x - barWidth * .32, pad.top + chartHeight - callH, barWidth * .28, callH)
        ctx.fillStyle = '#ee6574'; ctx.fillRect(x + barWidth * .04, pad.top + chartHeight - putH, barWidth * .28, putH)
        ctx.fillStyle = '#8892a8'; ctx.fillText(item.strike_price, x, height - 10)
      })
      const open = Number(analysis.previous_open_price)
      const min = Number(values[0]?.strike_price ?? open), maxStrike = Number(values.at(-1)?.strike_price ?? open)
      if (maxStrike > min) {
        const x = pad.left + (open - min) / (maxStrike - min) * chartWidth
        ctx.strokeStyle = '#e8bd62'; ctx.setLineDash([5, 4]); ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, pad.top + chartHeight); ctx.stroke(); ctx.setLineDash([])
      }
    }
    draw(); const observer = new ResizeObserver(draw); observer.observe(parent)
    return () => observer.disconnect()
  }, [analysis])
  return <canvas ref={ref} aria-label="Call and put open-interest histogram" />
}
