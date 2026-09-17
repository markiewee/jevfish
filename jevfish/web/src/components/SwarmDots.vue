<script setup>
import { computed } from 'vue'
import { seriesVar } from '../lib/palette.js'

// One dot per person (or per k people for big crowds). Solid = yes even at the low end of the
// 90% range, light = inside the range, empty = no.
const props = defineProps({
  n: { type: Number, required: true },
  expected: { type: Number, required: true },
  low: { type: Number, required: true },
  high: { type: Number, required: true },
  index: { type: Number, default: 0 },
  label: { type: String, default: '' },
})
const per = computed(() => (props.n > 300 ? Math.ceil(props.n / 200) : 1))
const count = computed(() => Math.ceil(props.n / per.value))
const lowD = computed(() => Math.max(0, Math.round(props.low / per.value)))
const highD = computed(() => Math.min(count.value, Math.round(props.high / per.value)))
const dots = computed(() => Array.from({ length: count.value }, (_, i) => (i < lowD.value ? 'yes' : i < highD.value ? 'range' : 'no')))
const color = computed(() => seriesVar(props.index))
</script>

<template>
  <div class="swarm">
    <div
      class="dots"
      role="img"
      :aria-label="`${label}: about ${expected.toFixed(1)} of ${n} people say yes, 90% range ${low.toFixed(1)} to ${high.toFixed(1)}`"
    >
      <span v-for="(d, i) in dots" :key="i" class="dot" :class="d" :style="d === 'no' ? null : { '--c': color }"></span>
    </div>
    <p class="small muted key">
      <span><span class="dot yes" :style="{ '--c': color }"></span> yes at the low end</span>
      <span><span class="dot range" :style="{ '--c': color }"></span> inside the 90% range</span>
      <span v-if="per > 1">Each dot is {{ per }} people.</span>
    </p>
  </div>
</template>

<style scoped>
.dots { display: flex; flex-wrap: wrap; gap: 3px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--dot-empty); display: inline-block; flex: none; }
.dot.yes { background: var(--c); }
.dot.range { background: color-mix(in srgb, var(--c) 38%, var(--panel)); }
.key { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 8px; }
.key > span { display: inline-flex; gap: 6px; align-items: center; }
</style>
