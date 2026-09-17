<script setup>
// rows: [{ key, value, label, color, shape: 'line' | 'rect' }]
defineProps({
  show: Boolean,
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  title: { type: String, default: '' },
  rows: { type: Array, default: () => [] },
})
function place(x, y) {
  const w = typeof window !== 'undefined' ? window.innerWidth : 1000
  const left = x + 16 + 260 > w ? Math.max(8, x - 16 - 260) : x + 16
  return { left: left + 'px', top: Math.max(8, y - 12) + 'px' }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="chart-tooltip" :style="place(x, y)" role="presentation">
      <div v-if="title" class="tt-title">{{ title }}</div>
      <div v-for="r in rows" :key="r.key" class="tt-row">
        <span :class="r.shape === 'rect' ? 'swatch' : 'linekey'" :style="{ background: r.color }"></span>
        <strong>{{ r.value }}</strong>
        <span>{{ r.label }}</span>
      </div>
    </div>
  </Teleport>
</template>
