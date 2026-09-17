<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from './lib/api.js'

const health = ref(null)
const healthError = ref('')
const theme = ref('auto')

try {
  const t = localStorage.getItem('jevfish-theme')
  if (t === 'light' || t === 'dark') theme.value = t
} catch (e) {
  /* storage unavailable */
}

function setTheme(t) {
  theme.value = t
  const el = document.documentElement
  if (t === 'auto') el.removeAttribute('data-theme')
  else el.setAttribute('data-theme', t)
  try {
    if (t === 'auto') localStorage.removeItem('jevfish-theme')
    else localStorage.setItem('jevfish-theme', t)
  } catch (e) {
    /* storage unavailable */
  }
}

onMounted(async () => {
  try {
    health.value = await api.health()
  } catch (e) {
    healthError.value = e.message
  }
})

const warnings = computed(() => {
  const h = health.value
  if (!h) return []
  const out = []
  const fake = h.judge === 'fake' || h.llm === 'fake'
  if (fake) out.push('Fake mode: numbers are noise. The server is running with test stand-ins for Jev or the language model.')
  if (h.judge && h.judge !== 'jev' && h.judge !== 'fake') out.push(`Jev is not set up (${h.judge}). Runs and crowd questions will fail until it is.`)
  if (h.llm && h.llm !== 'fake' && String(h.llm).startsWith('missing')) out.push(`No language model is set up (${h.llm}). Graphs, crowds, posts and reports need one.`)
  return out
})
</script>

<template>
  <header class="topbar">
    <div class="wrap topbar-inner">
      <RouterLink to="/" class="brand" aria-label="JevFish home">
        <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="8" class="brand-tile" />
          <g class="brand-dots">
            <circle cx="9" cy="12" r="2.2" /><circle cx="15" cy="9" r="2.2" /><circle cx="15" cy="16" r="2.2" />
            <circle cx="21" cy="12" r="2.2" /><circle cx="21" cy="19" r="2.2" /><circle cx="9" cy="20" r="2.2" />
            <circle cx="15" cy="23" r="2.2" />
          </g>
        </svg>
        <span>JevFish</span>
      </RouterLink>
      <span class="tagline muted">Swarm predictions, one Jev decision per person</span>
      <span class="spacer"></span>
      <div class="seg" role="group" aria-label="Colour theme">
        <button type="button" :aria-pressed="theme === 'auto'" @click="setTheme('auto')">Auto</button>
        <button type="button" :aria-pressed="theme === 'light'" @click="setTheme('light')">Light</button>
        <button type="button" :aria-pressed="theme === 'dark'" @click="setTheme('dark')">Dark</button>
      </div>
    </div>
  </header>
  <div v-if="warnings.length || healthError" class="wrap banner-wrap">
    <div v-if="healthError" class="notice error" role="alert">{{ healthError }}</div>
    <div v-for="w in warnings" :key="w" class="notice warn" role="status">{{ w }}</div>
  </div>
  <main class="wrap main">
    <RouterView />
  </main>
</template>

<style scoped>
.topbar { background: var(--panel); border-bottom: 1px solid var(--line); }
.topbar-inner { display: flex; align-items: center; gap: 16px; min-height: 56px; flex-wrap: wrap; padding-top: 8px; padding-bottom: 8px; }
.brand { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; color: var(--ink); font-weight: 700; font-size: 17px; letter-spacing: -0.01em; }
.brand-tile { fill: var(--accent); }
.brand-dots { fill: var(--accent-ink); }
.tagline { font-size: 13px; }
@media (max-width: 700px) { .tagline { display: none; } }
.banner-wrap { margin-top: 16px; display: grid; gap: 8px; }
.main { padding-top: 24px; padding-bottom: 64px; }
</style>
