import type { Analysis, Health, ScanList } from '../types'

const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? `Request failed (${response.status})`)
  return response.json() as Promise<T>
}
export const api = {
  latest: (query = '') => request<ScanList>(`/scans/latest${query}`),
  health: () => request<Health>('/health'),
  run: () => request<{ scan_id: number }>('/scans', { method: 'POST', body: JSON.stringify({ levels: 3 }) }),
  analysis: (symbol: string, levels: number) => request<Analysis>(`/instruments/${symbol}/analysis?levels=${levels}`),
  pine: (symbol: string, levels: number) => request<{ value: string }>(`/instruments/${symbol}/pine-data?levels=${levels}`),
  script: () => request<{ code: string }>('/instruments/pine-script-code'),
}
