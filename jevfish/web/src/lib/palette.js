// Fixed categorical order. Charts reference the CSS variables so the theme switch recolours them.
export const SERIES_COUNT = 8
export function seriesVar(i) {
  return i < SERIES_COUNT ? `var(--s${i + 1})` : 'var(--s-other)'
}
