import { inject } from 'vue'

export const WS_KEY = Symbol('workspace')

export function useWorkspace() {
  return inject(WS_KEY)
}

export const FINISHED = new Set(['done', 'partial'])
export const ACTIVE_RUN = new Set(['queued', 'running'])

export function runLabel(r) {
  if (!r) return ''
  const c = r.config || {}
  const d = new Date(r.created_at)
  const t = Number.isNaN(d.getTime())
    ? r.id
    : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  const status = { queued: 'queued', running: 'running', done: 'finished', partial: 'partly finished', failed: 'failed', cancelled: 'cancelled' }[r.status] || r.status
  return `${t}, ${c.platform || 'reddit'}, ${c.rounds ?? '?'} rounds, ${status}`
}
