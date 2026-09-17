<script setup>
import { computed, ref } from 'vue'
import { seriesVar } from '../lib/palette.js'
import { useWidth } from '../lib/useWidth.js'
import ChartTooltip from './ChartTooltip.vue'

// categories: string[]; series: [{ id, label, index, values: number[] (0..1 shares), counts?: number[] }]
const props = defineProps({
  categories: { type: Array, required: true },
  series: { type: Array, required: true },
  height: { type: Number, default: 280 },
  valueName: { type: String, default: 'Share of people' },
  describe: { type: String, default: '' },
})

const { el, width } = useWidth(480)
const view = ref('chart')
const m = { l: 46, r: 12, t: 14, b: 52 }
const iw = computed(() => width.value - m.l - m.r)
const ih = computed(() => props.height - m.t - m.b)
const maxV = computed(() => {
  const mx = Math.max(0.05, ...props.series.flatMap((s) => s.values))
  return Math.min(1, Math.ceil(mx * 10) / 10)
})
const ticks = computed(() => {
  const step = maxV.value > 0.5 ? 0.25 : maxV.value > 0.2 ? 0.1 : 0.05
  const out = []
  for (let v = 0; v <= maxV.value + 1e-9; v += step) out.push(Math.round(v * 100) / 100)
  return out
})
const top = computed(() => Math.max(maxV.value, ticks.value[ticks.value.length - 1]))
const sy = (v) => m.t + (1 - v / top.value) * ih.value
const band = computed(() => iw.value / Math.max(1, props.categories.length))
const barW = computed(() => Math.min(24, Math.max(4, (band.value * 0.7 - 2 * (props.series.length - 1)) / Math.max(1, props.series.length))))
function barX(ci, si) {
  const groupW = props.series.length * barW.value + (props.series.length - 1) * 2
  return m.l + ci * band.value + (band.value - groupW) / 2 + si * (barW.value + 2)
}
// Rounded data end, square baseline
function barPath(x, v) {
  const y0 = sy(0)
  const y1 = sy(v)
  const h = y0 - y1
  if (h <= 0) return ''
  const w = barW.value
  const r = Math.min(4, h, w / 2)
  return `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 + r}V${y0}Z`
}
function wrap(label, max) {
  const words = String(label).split(/\s+/)
  const lines = ['']
  for (const w of words) {
    const cur = lines[lines.length - 1]
    if ((cur + ' ' + w).trim().length > max && cur) {
      if (lines.length === 2) {
        lines[1] = (lines[1] + ' ' + w).trim()
        continue
      }
      lines.push(w)
    } else lines[lines.length - 1] = (cur + ' ' + w).trim()
  }
  return lines.map((l) => (l.length > max + 4 ? l.slice(0, max + 3) + '…' : l))
}
const pct = (v) => `${Math.round(v * 100)}%`

const hover = ref(null)
const tip = ref({ x: 0, y: 0 })
function enter(ev, ci, si) {
  hover.value = { ci, si }
  tip.value = { x: ev.clientX, y: ev.clientY }
}
const tipRows = computed(() => {
  if (!hover.value) return []
  const s = props.series[hover.value.si]
  const c = s.counts ? ` (${s.counts[hover.value.ci]} people)` : ''
  return [{ key: s.id, value: pct(s.values[hover.value.ci]) + c, label: s.label, color: seriesVar(s.index), shape: 'rect' }]
})
</script>

<template>
  <div class="gb">
    <div class="gb-top">
      <div v-if="series.length > 1" class="legend">
        <span v-for="s in series" :key="s.id"><span class="swatch" :style="{ background: seriesVar(s.index) }"></span>{{ s.label }}</span>
      </div>
      <span class="spacer"></span>
      <div class="seg" role="group" aria-label="Chart or table">
        <button type="button" :aria-pressed="view === 'chart'" @click="view = 'chart'">Chart</button>
        <button type="button" :aria-pressed="view === 'table'" @click="view = 'table'">Table</button>
      </div>
    </div>
    <div v-show="view === 'chart'" ref="el" class="chart-box">
      <svg :width="width" :height="height" role="img" :aria-label="describe || valueName">
        <g class="grid">
          <g v-for="t in ticks" :key="t">
            <line :x1="m.l" :x2="width - m.r" :y1="sy(t)" :y2="sy(t)" />
            <text :x="m.l - 8" :y="sy(t)" dy="0.32em" text-anchor="end">{{ pct(t) }}</text>
          </g>
          <text v-for="(c, ci) in categories" :key="ci" :x="m.l + ci * band + band / 2" :y="height - m.b + 18" text-anchor="middle">
            <tspan v-for="(ln, li) in wrap(c, Math.max(8, Math.floor(band / 7)))" :key="li" :x="m.l + ci * band + band / 2" :dy="li ? 14 : 0">{{ ln }}</tspan>
          </text>
        </g>
        <g v-for="(s, si) in series" :key="s.id">
          <g v-for="(v, ci) in s.values" :key="ci">
            <path
              :d="barPath(barX(ci, si), v)"
              class="bar"
              :class="{ lifted: hover && hover.ci === ci && hover.si === si }"
              :style="{ fill: seriesVar(s.index) }"
            />
            <rect
              :x="barX(ci, si) - 1" :y="m.t" :width="barW + 2" :height="ih"
              fill="transparent"
              tabindex="0"
              :aria-label="`${s.label}, ${categories[ci]}: ${pct(v)}`"
              @pointerenter="enter($event, ci, si)"
              @pointermove="enter($event, ci, si)"
              @pointerleave="hover = null"
              @focus="hover = { ci, si }; tip = { x: $event.target.getBoundingClientRect().right, y: $event.target.getBoundingClientRect().top + 40 }"
              @blur="hover = null"
            />
          </g>
        </g>
        <line class="base" :x1="m.l" :x2="width - m.r" :y1="sy(0)" :y2="sy(0)" />
      </svg>
    </div>
    <div v-if="view === 'table'" class="table-scroll">
      <table class="data">
        <thead><tr><th></th><th v-for="s in series" :key="s.id" class="num">{{ s.label }}</th></tr></thead>
        <tbody>
          <tr v-for="(c, ci) in categories" :key="ci">
            <td>{{ c }}</td>
            <td v-for="s in series" :key="s.id" class="num">{{ pct(s.values[ci]) }}<span v-if="s.counts" class="muted"> ({{ s.counts[ci] }})</span></td>
          </tr>
        </tbody>
      </table>
    </div>
    <ChartTooltip :show="!!hover && view === 'chart'" :x="tip.x" :y="tip.y" :title="hover ? categories[hover.ci] : ''" :rows="tipRows" />
  </div>
</template>

<style scoped>
.gb { display: grid; gap: 8px; }
.gb-top { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.grid line { stroke: var(--grid); stroke-width: 1; }
.grid text { font-size: 12px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.base { stroke: var(--line-strong); stroke-width: 1; }
.bar { transition: opacity 0.15s; }
.bar.lifted { opacity: 0.8; }
rect:focus { outline: none; }
rect:focus-visible { stroke: var(--focus); stroke-width: 2; }
</style>
