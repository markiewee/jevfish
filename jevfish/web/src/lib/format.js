export function pct(p, digits = 0) {
  if (p == null || Number.isNaN(p)) return '-'
  return `${(p * 100).toFixed(digits)}%`
}

export function num(x, digits = 1) {
  if (x == null || Number.isNaN(x)) return '-'
  return Number(x).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function int(x) {
  if (x == null || Number.isNaN(x)) return '-'
  return Math.round(x).toLocaleString('en-US')
}

export function signed(x, digits = 1) {
  if (x == null || Number.isNaN(x)) return '-'
  const v = Number(x)
  const s = Math.abs(v).toFixed(digits)
  if (Number(s) === 0) return (0).toFixed(digits)
  return (v > 0 ? '+' : '−') + s
}

export function usd(x) {
  if (x == null || Number.isNaN(x)) return '-'
  const v = Number(x)
  if (v === 0) return '$0'
  if (v < 0.01) return `$${v.toFixed(4)}`
  return `$${v.toFixed(2)}`
}

export function when(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function plural(n, one, many) {
  return `${n.toLocaleString('en-US')} ${n === 1 ? one : many || one + 's'}`
}

export const STAGE_LABEL = {
  new: 'Needs seed text',
  seeded: 'Seeded',
  graph: 'Graph built',
  prepared: 'Crowd ready',
}

export const RUN_STATUS_LABEL = {
  queued: 'Queued',
  running: 'Running',
  done: 'Finished',
  partial: 'Partly finished',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export const ACTION_LABEL = {
  create_post: 'posted',
  create_comment: 'commented',
  quote_post: 'quoted',
  like_post: 'liked a post by',
  dislike_post: 'disliked a post by',
  repost: 'reshared a post by',
  like_comment: 'liked a comment by',
  follow: 'followed',
  do_nothing: 'scrolled past',
}

export function debounce(fn, ms) {
  let t
  return (...args) => {
    clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
}
