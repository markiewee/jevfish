<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from 'd3-force'
import { seriesVar } from '../lib/palette.js'

const props = defineProps({
  nodes: { type: Array, required: true },
  edges: { type: Array, required: true },
  types: { type: Array, required: true },
  selectedId: { type: String, default: '' },
  highlightEdge: { type: String, default: '' },
})
const emit = defineEmits(['select'])

const box = ref(null)
const width = ref(800)
const height = ref(520)
const tick = ref(0)
const simNodes = shallowRef([])
const simLinks = shallowRef([])
const view = ref({ x: 0, y: 0, k: 1 })
const hover = ref(null)
const tip = ref({ x: 0, y: 0 })
let sim = null
let ro = null

const typeIndex = computed(() => Object.fromEntries(props.types.map((t, i) => [t, i])))
function colorFor(type) {
  const i = typeIndex.value[type]
  return i == null ? 'var(--s-other)' : seriesVar(i)
}
function radius(n) {
  return 5 + Math.sqrt(n.degree || 0) * 3.2
}

const labelled = computed(() => {
  tick.value
  const ranked = [...simNodes.value].sort((a, b) => (b.degree || 0) - (a.degree || 0))
  const keep = new Set(ranked.slice(0, simNodes.value.length > 60 ? 14 : 30).map((n) => n.id))
  if (props.selectedId) keep.add(props.selectedId)
  if (hover.value) keep.add(hover.value.id)
  return keep
})

const neighbours = computed(() => {
  const s = new Set()
  if (!props.selectedId) return s
  for (const l of simLinks.value) {
    if (l.source.id === props.selectedId) s.add(l.target.id)
    if (l.target.id === props.selectedId) s.add(l.source.id)
  }
  return s
})

function build() {
  if (sim) sim.stop()
  const old = new Map(simNodes.value.map((n) => [n.id, n]))
  const w = width.value
  const h = height.value
  const nodes = props.nodes.map((n) => {
    const prev = old.get(n.id)
    return { ...n, x: prev?.x ?? w / 2 + (Math.random() - 0.5) * w * 0.5, y: prev?.y ?? h / 2 + (Math.random() - 0.5) * h * 0.5 }
  })
  const ids = new Set(nodes.map((n) => n.id))
  const links = props.edges.filter((e) => ids.has(e.source) && ids.has(e.target) && e.source !== e.target).map((e) => ({ ...e }))
  simNodes.value = nodes
  simLinks.value = links
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  sim = forceSimulation(nodes)
    .force('link', forceLink(links).id((d) => d.id).distance(70).strength(0.4))
    .force('charge', forceManyBody().strength((nodes.length > 150 ? -90 : -220) * Math.min(1, Math.max(0.45, w / 800))))
    .force('center', forceCenter(w / 2, h / 2))
    .force('x', forceX(w / 2).strength(0.04))
    .force('y', forceY(h / 2).strength(0.06))
    .force('collide', forceCollide((d) => radius(d) + 6))
    .on('tick', () => {
      clamp()
      tick.value++
    })
  if (reduce) {
    sim.stop()
    for (let i = 0; i < 300; i++) {
      sim.tick()
      clamp()
    }
    tick.value++
  }
}

// Keep every dot inside the box so nothing drifts out of view
function clamp() {
  const w = width.value
  const h = height.value
  for (const n of simNodes.value) {
    const pad = radius(n) + 6
    n.x = Math.max(pad + 20, Math.min(w - pad - 20, n.x))
    n.y = Math.max(pad, Math.min(h - pad - 14, n.y))
  }
}

function measure() {
  if (!box.value) return
  const w = Math.max(240, box.value.clientWidth)
  const h = w < 600 ? 380 : 520
  if (Math.abs(w - width.value) > 4 || h !== height.value) {
    width.value = w
    height.value = h
    if (sim) {
      sim.force('center', forceCenter(w / 2, h / 2)).force('x', forceX(w / 2).strength(0.04)).force('y', forceY(h / 2).strength(0.06))
      sim.alpha(0.3).restart()
    }
  }
}

onMounted(() => {
  measure()
  build()
  ro = new ResizeObserver(measure)
  ro.observe(box.value)
})
onBeforeUnmount(() => {
  if (sim) sim.stop()
  if (ro) ro.disconnect()
})
watch(() => [props.nodes, props.edges], build)

// Pan, zoom and drag
const svg = ref(null)
let drag = null
function toGraph(ev) {
  const rect = svg.value.getBoundingClientRect()
  const v = view.value
  return { x: (ev.clientX - rect.left - v.x) / v.k, y: (ev.clientY - rect.top - v.y) / v.k }
}
function onNodeDown(ev, n) {
  ev.stopPropagation()
  svg.value.setPointerCapture(ev.pointerId)
  drag = { kind: 'node', node: n, moved: false, sx: ev.clientX, sy: ev.clientY }
  n.fx = n.x
  n.fy = n.y
}
function onBgDown(ev) {
  svg.value.setPointerCapture(ev.pointerId)
  drag = { kind: 'pan', sx: ev.clientX, sy: ev.clientY, vx: view.value.x, vy: view.value.y, moved: false }
}
function onMove(ev) {
  if (!drag) return
  const dx = ev.clientX - drag.sx
  const dy = ev.clientY - drag.sy
  if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true
  if (drag.kind === 'pan') {
    view.value = { ...view.value, x: drag.vx + dx, y: drag.vy + dy }
  } else if (drag.moved) {
    const p = toGraph(ev)
    drag.node.fx = p.x
    drag.node.fy = p.y
    hover.value = null
    sim.alphaTarget(0.2).restart()
  }
}
function onUp() {
  if (!drag) return
  if (drag.kind === 'node') {
    const n = drag.node
    n.fx = null
    n.fy = null
    sim.alphaTarget(0)
    if (!drag.moved) emit('select', n.id === props.selectedId ? '' : n.id)
  } else if (!drag.moved) {
    emit('select', '')
  }
  drag = null
}
function zoomBy(f, cx = width.value / 2, cy = height.value / 2) {
  const v = view.value
  const k = Math.min(4, Math.max(0.3, v.k * f))
  const r = k / v.k
  view.value = { k, x: cx - (cx - v.x) * r, y: cy - (cy - v.y) * r }
}
function onWheel(ev) {
  if (!(ev.ctrlKey || ev.metaKey)) return
  ev.preventDefault()
  const rect = svg.value.getBoundingClientRect()
  zoomBy(Math.exp(-ev.deltaY * 0.01), ev.clientX - rect.left, ev.clientY - rect.top)
}
function resetView() {
  view.value = { x: 0, y: 0, k: 1 }
  if (sim) sim.alpha(0.5).restart()
}

function onEnter(ev, n) {
  if (drag) return
  hover.value = n
  moveTip(ev)
}
function moveTip(ev) {
  const pad = 14
  const x = Math.min(ev.clientX + pad, window.innerWidth - 300)
  const y = Math.min(ev.clientY + pad, window.innerHeight - 140)
  tip.value = { x: Math.max(8, x), y }
}
function onKey(ev, n) {
  if (ev.key === 'Enter' || ev.key === ' ') {
    ev.preventDefault()
    emit('select', n.id === props.selectedId ? '' : n.id)
  }
}

// Centre on the selected node when it changes from outside (search)
watch(
  () => props.selectedId,
  (id) => {
    if (!id) return
    const n = simNodes.value.find((x) => x.id === id)
    if (!n) return
    const v = view.value
    const sx = n.x * v.k + v.x
    const sy = n.y * v.k + v.y
    if (sx < 40 || sx > width.value - 40 || sy < 40 || sy > height.value - 40) {
      view.value = { ...v, x: width.value / 2 - n.x * v.k, y: height.value / 2 - n.y * v.k }
    }
  },
)

function short(s, n = 22) {
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}
</script>

<template>
  <div class="fg">
    <div ref="box" class="fg-box" :style="{ height: height + 'px' }">
      <svg
        ref="svg"
        :width="width"
        :height="height"
        role="img"
        :aria-label="`Knowledge graph with ${nodes.length} entities and ${edges.length} relations`"
        @pointerdown="onBgDown"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointercancel="onUp"
        @wheel="onWheel"
      >
        <g :transform="`translate(${view.x},${view.y}) scale(${view.k})`" :data-tick="tick">
          <g class="links">
            <line
              v-for="l in simLinks"
              :key="l.id"
              :x1="l.source.x" :y1="l.source.y" :x2="l.target.x" :y2="l.target.y"
              :class="{
                hot: selectedId && (l.source.id === selectedId || l.target.id === selectedId),
                dim: selectedId && l.source.id !== selectedId && l.target.id !== selectedId,
                edgehit: highlightEdge === l.id,
              }"
            />
          </g>
          <g class="nodes">
            <g
              v-for="n in simNodes"
              :key="n.id"
              class="node"
              :class="{ sel: n.id === selectedId, dim: selectedId && n.id !== selectedId && !neighbours.has(n.id) }"
              :transform="`translate(${n.x},${n.y})`"
              tabindex="0"
              role="button"
              :aria-label="`${n.name}, ${n.type}, ${n.degree} connections`"
              @pointerdown="onNodeDown($event, n)"
              @pointerenter="onEnter($event, n)"
              @pointermove="moveTip"
              @pointerleave="hover = null"
              @keydown="onKey($event, n)"
              @focus="hover = null"
            >
              <circle class="hit" :r="Math.max(12, radius(n) + 4)" />
              <circle class="dot" :r="radius(n)" :style="{ fill: colorFor(n.type) }" />
              <text v-if="labelled.has(n.id)" :y="radius(n) + 13" text-anchor="middle">{{ short(n.name) }}</text>
            </g>
          </g>
        </g>
      </svg>
      <div class="fg-tools">
        <button class="btn small icon" type="button" aria-label="Zoom in" @click="zoomBy(1.25)">+</button>
        <button class="btn small icon" type="button" aria-label="Zoom out" @click="zoomBy(0.8)">&minus;</button>
        <button class="btn small" type="button" @click="resetView">Reset</button>
      </div>
    </div>
    <p class="small muted hint">Drag to pan, drag a dot to move it, click a dot for its facts. Hold Ctrl or Cmd and scroll to zoom.</p>
    <Teleport to="body">
      <div v-if="hover" class="chart-tooltip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
        <div class="tt-row"><span class="swatch" :style="{ background: colorFor(hover.type) }"></span><strong>{{ hover.name }}</strong></div>
        <div class="tt-title">{{ hover.type }}, {{ hover.degree }} {{ hover.degree === 1 ? 'connection' : 'connections' }}</div>
        <div v-if="hover.summary">{{ hover.summary.length > 180 ? hover.summary.slice(0, 179) + '…' : hover.summary }}</div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.fg-box { position: relative; border-radius: var(--radius-sm); background: var(--panel-2); border: 1px solid var(--line); overflow: hidden; touch-action: none; }
svg { display: block; cursor: grab; user-select: none; }
svg:active { cursor: grabbing; }
.links line { stroke: var(--line-strong); stroke-width: 1; }
.links line.hot { stroke: var(--ink-2); stroke-width: 1.5; }
.links line.dim { opacity: 0.35; }
.links line.edgehit { stroke: var(--ink); stroke-width: 2.5; opacity: 1; }
.node { cursor: pointer; outline: none; }
.node .hit { fill: transparent; }
.node .dot { stroke: var(--panel-2); stroke-width: 2; }
.node:hover .dot, .node:focus-visible .dot { stroke: var(--ink); stroke-width: 2; }
.node.sel .dot { stroke: var(--ink); stroke-width: 3; }
.node.dim { opacity: 0.3; }
.node text { font-size: 11px; fill: var(--ink); paint-order: stroke; stroke: var(--panel-2); stroke-width: 3px; stroke-linejoin: round; pointer-events: none; }
.node.sel text { font-weight: 700; }
.fg-tools { position: absolute; right: 8px; top: 8px; display: flex; gap: 4px; }
.hint { margin-top: 6px; }
</style>
