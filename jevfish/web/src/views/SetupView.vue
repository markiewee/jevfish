<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../lib/api.js'
import { health, refreshHealth } from '../lib/health.js'

const saved = ref(null)
const loadError = ref('')
const typesafeKey = ref('')
const provider = ref('gemini')
const llmKey = ref('')
const baseUrl = ref('')
const model = ref('')
const busy = ref('')
const formError = ref('')
const checks = ref(null)
const stopped = ref(false)

async function load() {
  try {
    const s = await api.settings()
    saved.value = s
    provider.value = s.llm_provider
    baseUrl.value = s.llm_base_url
    model.value = s.llm_model
  } catch (e) {
    loadError.value = e.message
  }
}
onMounted(load)

const firstRun = computed(() => saved.value && saved.value.setup_needed && !saved.value.test_mode)
const savedLlmKey = computed(() => (saved.value ? (provider.value === 'gemini' ? saved.value.gemini_key : saved.value.llm_key) : null))
// Offer to start only when the keys are in place and the last check (if any) passed.
const ready = computed(() => {
  if (!health.value || health.value.setup_needed) return false
  return !checks.value || (checks.value.jev.ok && checks.value.llm.ok)
})

function savedText(h) {
  if (h === null || h === undefined) return ''
  return h ? `A key ending in ${h} is saved. Leave this blank to keep it.` : 'A key is saved. Leave this blank to keep it.'
}

function form() {
  const f = { typesafe_key: typesafeKey.value, llm_provider: provider.value, llm_key: llmKey.value }
  if (provider.value === 'openai') Object.assign(f, { llm_base_url: baseUrl.value, llm_model: model.value })
  return f
}

async function saveAndCheck() {
  formError.value = ''
  checks.value = null
  if (!typesafeKey.value.trim() && !(saved.value && saved.value.typesafe_key !== null)) {
    formError.value = 'Paste your Jev key first.'
    return
  }
  busy.value = 'save'
  try {
    saved.value = await api.saveSettings(form())
    typesafeKey.value = ''
    llmKey.value = ''
    await refreshHealth()
    busy.value = 'check'
    checks.value = await api.checkKeys({ llm_provider: provider.value })
  } catch (e) {
    formError.value = e.message
  } finally {
    busy.value = ''
  }
}

async function setTestMode(on) {
  formError.value = ''
  busy.value = 'test'
  try {
    checks.value = null
    saved.value = await api.saveSettings({ test_mode: on })
    await refreshHealth()
  } catch (e) {
    formError.value = e.message
  } finally {
    busy.value = ''
  }
}

async function stop() {
  const n = saved.value ? saved.value.active_tasks : 0
  const extra = n ? ` ${n} running ${n === 1 ? 'job' : 'jobs'} will stop too.` : ''
  if (!window.confirm(`Stop JevFish on this computer?${extra}`)) return
  try {
    await api.shutdown()
    stopped.value = true
  } catch (e) {
    formError.value = e.message
  }
}
</script>

<template>
  <div v-if="stopped" class="panel empty">
    <h3>JevFish has stopped</h3>
    <p>You can close this tab. Open JevFish.app to start it again.</p>
  </div>
  <div v-else class="stack-lg setup">
    <section class="intro">
      <h1>{{ firstRun ? 'Set up JevFish' : 'Settings' }}</h1>
      <p class="muted">
        JevFish needs two keys. Jev decides what each simulated person does, and a language model writes the graph, the crowd and
        the posts. Keys stay in a file on this computer.
      </p>
    </section>

    <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>

    <form v-if="saved" class="stack-lg" @submit.prevent="saveAndCheck">
      <section class="panel stack" aria-labelledby="jev-head">
        <div class="panel-head">
          <h2 id="jev-head">Jev</h2>
          <p>Get a key at <a href="https://console.typesafe.ai" target="_blank" rel="noopener">console.typesafe.ai</a>. A typical run costs about US$0.04.</p>
        </div>
        <label class="field">
          <span class="label">TypeSafe API key</span>
          <input v-model="typesafeKey" type="password" autocomplete="off" spellcheck="false" :placeholder="saved.typesafe_key !== null ? 'Saved' : 'Paste the key'" />
          <span class="hint">{{ savedText(saved.typesafe_key) }}</span>
        </label>
        <div v-if="checks" class="notice" :class="checks.jev.ok ? 'ok' : 'error'" role="status">{{ checks.jev.message }}</div>
      </section>

      <section class="panel stack" aria-labelledby="llm-head">
        <div class="panel-head">
          <h2 id="llm-head">Language model</h2>
          <span class="spacer"></span>
          <div class="seg" role="group" aria-label="Model provider">
            <button type="button" :aria-pressed="provider === 'gemini'" @click="provider = 'gemini'">Gemini</button>
            <button type="button" :aria-pressed="provider === 'openai'" @click="provider = 'openai'">Other</button>
          </div>
        </div>
        <p v-if="provider === 'gemini'" class="muted small">
          Free key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a>. The free tier is enough for normal runs.
        </p>
        <p v-else class="muted small">Any service that speaks the OpenAI API: OpenAI, OpenRouter, Groq, or a local model.</p>
        <div v-if="provider === 'openai'" class="form-grid wide">
          <label class="field">
            <span class="label">Address</span>
            <input v-model="baseUrl" type="url" spellcheck="false" placeholder="https://api.openai.com/v1" />
          </label>
          <label class="field">
            <span class="label">Model</span>
            <input v-model="model" type="text" spellcheck="false" placeholder="gpt-4o-mini" />
          </label>
        </div>
        <label class="field">
          <span class="label">{{ provider === 'gemini' ? 'Gemini API key' : 'API key' }}</span>
          <input v-model="llmKey" type="password" autocomplete="off" spellcheck="false" :placeholder="savedLlmKey !== null ? 'Saved' : 'Paste the key'" />
          <span class="hint">{{ savedText(savedLlmKey) }}</span>
        </label>
        <div v-if="checks" class="notice" :class="checks.llm.ok ? 'ok' : 'error'" role="status">{{ checks.llm.message }}</div>
      </section>

      <div v-if="formError" class="notice error" role="alert">{{ formError }}</div>
      <div class="row">
        <button class="btn primary" type="submit" :disabled="!!busy">
          {{ busy === 'save' ? 'Saving' : busy === 'check' ? 'Checking keys' : 'Save and check' }}
        </button>
        <RouterLink v-if="ready" to="/" class="btn">Start a prediction</RouterLink>
      </div>
    </form>

    <section v-if="saved" class="panel stack" aria-labelledby="test-head">
      <div class="panel-head">
        <h2 id="test-head">Test mode</h2>
        <p>Try every screen without keys. Every number it shows is made up.</p>
      </div>
      <div class="row">
        <span class="pill" :class="saved.test_mode ? 'warn' : ''">{{ saved.test_mode ? 'On' : 'Off' }}</span>
        <button class="btn small" type="button" :disabled="!!busy" @click="setTestMode(!saved.test_mode)">
          {{ saved.test_mode ? 'Turn off test mode' : 'Turn on test mode' }}
        </button>
      </div>
    </section>

    <section v-if="saved" class="panel stack" aria-labelledby="stop-head">
      <div class="panel-head">
        <h2 id="stop-head">Stop JevFish</h2>
        <p>Shuts JevFish down on this computer. Open JevFish.app to start it again.</p>
      </div>
      <div class="row">
        <button class="btn small danger" type="button" @click="stop">Stop JevFish</button>
      </div>
      <p class="caveat break">Keys are saved in {{ saved.env_file }}</p>
    </section>
  </div>
</template>

<style scoped>
.setup { max-width: 760px; }
.intro h1 { font-size: 32px; letter-spacing: -0.02em; margin-bottom: 8px; }
.intro p { font-size: 16px; }
@media (max-width: 600px) { .intro h1 { font-size: 26px; } }
.form-grid.wide { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
</style>
