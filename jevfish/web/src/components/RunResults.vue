<script setup>
import { computed } from 'vue'
import { int, num, pct, signed, usd } from '../lib/format.js'
import { seriesVar } from '../lib/palette.js'
import LineChart from './LineChart.vue'
import SwarmDots from './SwarmDots.vue'

const props = defineProps({
  summary: { type: Object, required: true },
  run: { type: Object, default: null },
})

const variants = computed(() => props.summary.variants.map((v, index) => ({ ...v, index })))
const series = computed(() =>
  variants.value.map((v) => ({ id: v.id, label: v.label, index: v.index, points: v.polls.map((p) => ({ x: p.round, y: p.mean_outcome })) })),
)
const labelOf = computed(() => Object.fromEntries(variants.value.map((v) => [v.id, v.label])))
function roundLabel(x, long) {
  if (x == null) return ''
  if (long) return x === 0 ? 'Before round 1' : `After round ${x}`
  return String(x)
}
function shift(v) {
  if (!v.final || !v.baseline) return null
  return { people: v.final.expected_yes - v.baseline.expected_yes, points: (v.final.mean_outcome - v.baseline.mean_outcome) * 100, from: v.baseline.round }
}
const VERDICT = { higher: 'Higher', lower: 'Lower', 'within noise': 'Within noise' }
const judge = computed(() => props.summary.judge || {})
const llm = computed(() => props.summary.llm)
</script>

<template>
  <div class="results stack-lg">
    <div v-if="summary.partial" class="notice warn">This run stopped early: {{ summary.partial }}. The numbers cover the rounds that finished.</div>

    <div class="tiles">
      <article v-for="v in variants" :key="v.id" class="tile">
        <header class="tile-head">
          <span class="swatch" :style="{ background: seriesVar(v.index) }"></span>
          <h3 class="break">{{ v.label }}</h3>
          <span class="muted small">{{ v.id }}</span>
        </header>
        <template v-if="v.final">
          <p class="big">
            <span class="figure">{{ num(v.final.expected_yes) }}</span>
            <span class="of">of {{ int(v.final.n) }} expected to say yes</span>
          </p>
          <dl class="facts">
            <div><dt>90% range</dt><dd class="tnum">{{ num(v.final.low) }} to {{ num(v.final.high) }}</dd></div>
            <div><dt>Mean chance of yes</dt><dd class="tnum">{{ pct(v.final.mean_outcome, 1) }}</dd></div>
            <div v-if="shift(v)">
              <dt>Shift from first poll</dt>
              <dd class="tnum">{{ signed(shift(v).people) }} people ({{ signed(shift(v).points) }} points)</dd>
            </div>
            <div><dt>Posts written</dt><dd class="tnum">{{ int(v.posts_total) }}</dd></div>
          </dl>
          <SwarmDots :n="v.final.n" :expected="v.final.expected_yes" :low="v.final.low" :high="v.final.high" :index="v.index" :label="v.label" />
        </template>
        <p v-else class="muted">No final poll recorded.</p>
      </article>
    </div>
    <p class="caveat">Ranges cover chance only, not model error. The crowd is synthetic.</p>

    <section v-if="summary.comparisons?.length" class="stack">
      <h3>Compared with {{ labelOf[summary.comparisons[0].baseline] || summary.comparisons[0].baseline }}</h3>
      <ul class="compare">
        <li v-for="c in summary.comparisons" :key="c.variant">
          <span class="c-name break">{{ labelOf[c.variant] || c.variant }}</span>
          <span class="tnum">{{ signed(c.diff_expected_yes) }} expected yes</span>
          <span class="muted small tnum">90% range {{ signed(c.low) }} to {{ signed(c.high) }}, chance of yes {{ signed(c.diff_mean_outcome * 100) }} points</span>
          <span class="pill" :class="{ accent: c.verdict !== 'within noise' }">{{ VERDICT[c.verdict] || c.verdict }}</span>
        </li>
      </ul>
    </section>

    <section class="stack">
      <h3>Mean chance of yes at each poll</h3>
      <LineChart :series="series" x-name="Poll round" :x-label="roundLabel" describe="Mean chance of yes at each poll round, one line per variant" />
    </section>

    <section class="usage">
      <h3 class="sr-only">Usage</h3>
      <dl class="usage-grid">
        <div><dt>Jev requests</dt><dd class="tnum">{{ int(judge.requests) }}<span v-if="run?.planned_requests" class="muted small"> of {{ int(run.planned_requests) }} planned</span></dd></div>
        <div><dt>Cache hits</dt><dd class="tnum">{{ int(judge.cache_hits) }}</dd></div>
        <div><dt>Estimated Jev cost</dt><dd class="tnum">{{ usd(judge.est_cost_usd) }}</dd></div>
        <div><dt>Jev input tokens</dt><dd class="tnum">{{ int(judge.input_tokens) }}</dd></div>
        <div v-if="llm"><dt>Language model calls</dt><dd class="tnum">{{ int(llm.calls) }}<span v-if="llm.failures" class="muted small">, {{ llm.failures }} failed</span></dd></div>
        <div><dt>Crowd</dt><dd class="tnum">{{ int(summary.crowd.size) }} people</dd></div>
      </dl>
      <p class="small muted">Judge model {{ judge.model }}<template v-if="judge.fake">, a test stand-in, so these numbers are noise</template>.</p>
    </section>
  </div>
</template>

<style scoped>
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.tile { border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; display: grid; gap: 14px; align-content: start; background: var(--panel); }
.tile-head { display: flex; gap: 8px; align-items: center; }
.tile-head h3 { flex: 1; min-width: 0; }
.big { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.figure { font-size: 40px; font-weight: 650; letter-spacing: -0.02em; line-height: 1; }
.of { color: var(--ink-2); }
.facts { margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 16px; }
.facts dt { font-size: 13px; color: var(--muted); }
.facts dd { margin: 0; font-weight: 600; }
.compare { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.compare li { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; padding: 10px 12px; background: var(--panel-2); border-radius: var(--radius-sm); }
.c-name { font-weight: 600; flex: 1 1 180px; }
.usage { border-top: 1px solid var(--line); padding-top: 16px; }
.usage-grid { margin: 0 0 8px; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.usage-grid dt { font-size: 13px; color: var(--muted); }
.usage-grid dd { margin: 0; font-size: 18px; font-weight: 600; }
</style>
