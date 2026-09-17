<script setup>
import { computed, ref } from 'vue'
import { seriesVar } from '../lib/palette.js'
import { useWidth } from '../lib/useWidth.js'
import ChartTooltip from './ChartTooltip.vue'

// series: [{ id, label, index, points: [{ x, y }] }], y in 0..1
const props = defineProps({
  series: { type: Array, required: true },
  xName: { type: String, default: 'Round' },
  xLabel: { type: Function, default: (x) => String(x) },
  yLabel: { type: String, default: 'Chance of yes' },
  height: { type: Number, default: 260 },
  describe: { type: String, default: '' },
})

const { el, width } = useWidth(320)
const view = ref('chart')
const m = computed(() => ({ l: 46, r: props.series.length <= 4 ? 64 : 16, t: 14, b: 40 }))
const xs = computed(() => [...new Set(props.series.flatMap((s) => s.points.map((p) => p.x)))].sort((a, b) => a - b))
const xMin = computed(() => Math.min(...xs.value, 0))
const xMax = computed(() => Math.max(...xs.value, 1))
const iw = computed(() => width.value - m.value.l - m.value.r)
const ih = computed(() => props.height - m.value.t - m.value.b)
const sx = (x) => m.value.l + ((x - xMin.value) / (xMax.value - xMin.value || 1)) * iw.value
const sy = (y) => m.value.t + (1 - y) * ih.value
const yTicks = [0, 0.25, 0.5, 0.75, 1]
const xTicks = computed(() => {
  const all = xs.value
  if (all.length <= 8) return all
  const step = Math.ceil(all.length / 8)
  return all.filter((_, i) => i % step === 0 || i === all.length - 1)
})
function path(points) {
  return points.map((p, i) => `${i ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join('')
}
const color = (s) => seriesVar(s.index)
const fmt = (y) => `${Math.round(y * 100)}%`

// Direct end labels only when they separate cleanly
const endLabels = computed(() => {
  if (props.series.length > 4 || props.series.length < 2) return []
  const ends = props.series
    .filter((s) => s.points.length)
    .map((s) => ({ s, y: sy(s.points[s.points.length - 1].y), x: sx(s.points[s.points.length - 1].x) }))
    .sort((a, b) => a.y - b.y)
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 14) return []
  return ends
})

const hoverX = ref(null)
const tip = ref({ x: 0, y: 0 })
function onMove(ev) {
  const rect = ev.currentTarget.ownerSVGElement.getBoundingClientRect()
  const px = ev.clientX - rect.left
  let best = null
  for (const x of xs.value) if (best == null || Math.abs(sx(x) - px) < Math.abs(sx(best) - px)) best = x
  hoverX.value = best
  tip.value = { x: ev.clientX, y: ev.clientY }
}
const tipRows = computed(() => {
  if (hoverX.value == null) return []
  return props.series
    .map((s) => ({ s, p: s.points.find((p) => p.x === hoverX.value) }))
    .filter((r) => r.p)
    .sort((a, b) => b.p.y - a.p.y)
    .map((r) => ({ key: r.s.id, value: fmt(r.p.y), label: r.s.label, color: color(r.s), shape: 'line' }))
})
</script>

<template>
  <div class="lc">
    <div class="lc-top">
      <div v-if="series.length > 1" class="legend">
        <span v-for="s in series" :key="s.id"><span class="linekey" :style="{ background: color(s) }"></span>{{ s.label }}</span>
      </div>
      <span class="spacer"></span>
      <div class="seg" role="group" aria-label="Chart or table">
        <button type="button" :aria-pressed="view === 'chart'" @click="view = 'chart'">Chart</button>
        <button type="button" :aria-pressed="view === 'table'" @click="view = 'table'">Table</button>
      </div>
    </div>
    <div v-show="view === 'chart'" ref="el" class="chart-box">
      <svg :width="width" :height="height" role="img" :aria-label="describe || `${yLabel} by ${xName.toLowerCase()}`">
        <g class="grid">
          <g v-for="t in yTicks" :key="t">
            <line :x1="m.l" :x2="width - m.r" :y1="sy(t)" :y2="sy(t)" />
            <text :x="m.l - 8" :y="sy(t)" dy="0.32em" text-anchor="end">{{ fmt(t) }}</text>
          </g>
          <text v-for="x in xTicks" :key="x" :x="sx(x)" :y="height - m.b + 18" text-anchor="middle">{{ xLabel(x) }}</text>
          <text :x="m.l + iw / 2" :y="height - 4" text-anchor="middle" class="axis-title">{{ xName }}</text>
        </g>
        <line v-if="hoverX != null" class="cross" :x1="sx(hoverX)" :x2="sx(hoverX)" :y1="m.t" :y2="m.t + ih" />
        <g v-for="s in series" :key="s.id">
          <path :d="path(s.points)" class="line" :style="{ stroke: color(s) }" />
          <circle
            v-for="p in s.points"
            :key="p.x"
            :cx="sx(p.x)" :cy="sy(p.y)"
            :r="hoverX === p.x ? 5 : 4"
            class="pt"
            :style="{ fill: color(s) }"
          />
        </g>
        <g v-for="e in endLabels" :key="e.s.id">
          <text :x="e.x + 8" :y="e.y" dy="0.32em" class="end">{{ e.s.id.length > 8 ? e.s.id.slice(0, 7) + '…' : e.s.id }}</text>
        </g>
        <rect
          :x="m.l - 10" :y="m.t" :width="iw + 20" :height="ih"
          fill="transparent"
          @pointermove="onMove"
          @pointerleave="hoverX = null"
        />
      </svg>
    </div>
    <div v-if="view === 'table'" class="table-scroll">
      <table class="data">
        <thead>
          <tr><th>{{ xName }}</th><th v-for="s in series" :key="s.id" class="num">{{ s.label }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="x in xs" :key="x">
            <td>{{ xLabel(x, true) }}</td>
            <td v-for="s in series" :key="s.id" class="num">{{ s.points.find((p) => p.x === x) ? fmt(s.points.find((p) => p.x === x).y) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <ChartTooltip :show="hoverX != null && view === 'chart'" :x="tip.x" :y="tip.y" :title="xLabel(hoverX, true)" :rows="tipRows" />
  </div>
</template>

<style scoped>
.lc { display: grid; gap: 8px; }
.lc-top { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.grid line { stroke: var(--grid); stroke-width: 1; }
.grid text { font-size: 12px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.axis-title { font-size: 12px; }
.line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.pt { stroke: var(--panel); stroke-width: 2; }
.cross { stroke: var(--line-strong); stroke-width: 1; }
.end { font-size: 12px; fill: var(--ink-2); }
</style>
