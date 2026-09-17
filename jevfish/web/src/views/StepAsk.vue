<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { api } from '../lib/api.js'
import { num, pct, when } from '../lib/format.js'
import { FINISHED, useWorkspace } from '../lib/workspace.js'
import SwarmDots from '../components/SwarmDots.vue'

const ws = useWorkspace()
const pid = ws.pid
const run = computed(() => ws.selectedRun.value)
const finished = computed(() => !!run.value && FINISHED.has(run.value.status))
const loadError = ref('')
Promise.all([ws.loadFrame(), ws.loadCrowd()]).catch((e) => (loadError.value = e.message))

const agents = computed(() => ws.crowd.value?.agents || [])
const variants = computed(() => {
  const labels = Object.fromEntries((ws.frame.value?.variants || []).map((v) => [v.id, v.label]))
  const ids = run.value?.variants?.length ? run.value.variants : (ws.frame.value?.variants || []).map((v) => v.id)
  return ids.map((id, index) => ({ id, label: labels[id] || id, index }))
})

// Chat with one person
const who = ref('')
const pickedId = ref(null)
const chatVariant = ref('')
const history = ref([])
const message = ref('')
const sending = ref(false)
const chatError = ref('')
const thread = ref(null)

watch(variants, (vs) => {
  if (vs.length && !vs.some((v) => v.id === chatVariant.value)) chatVariant.value = vs[0].id
}, { immediate: true })

const matches = computed(() => {
  const term = who.value.trim().toLowerCase()
  const list = term
    ? agents.value.filter((a) => `${a.name} ${a.username} ${a.segment} ${a.kind}`.toLowerCase().includes(term))
    : agents.value
  return list.slice(0, 60)
})
const picked = computed(() => agents.value.find((a) => a.agent_id === pickedId.value) || null)

async function loadHistory() {
  chatError.value = ''
  history.value = []
  if (pickedId.value == null || !finished.value) return
  const key = `${run.value.id}:${pickedId.value}:${chatVariant.value}`
  try {
    const h = await api.chatHistory(pid.value, run.value.id, pickedId.value, chatVariant.value)
    if (key === `${run.value?.id}:${pickedId.value}:${chatVariant.value}`) {
      history.value = h
      scrollDown()
    }
  } catch (e) {
    chatError.value = e.message
  }
}
watch(() => [pickedId.value, chatVariant.value, run.value?.id], loadHistory)

async function scrollDown() {
  await nextTick()
  if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
}

async function send() {
  const text = message.value.trim()
  if (!text || pickedId.value == null) return
  sending.value = true
  chatError.value = ''
  const pending = [...history.value, { role: 'user', content: text, at: new Date().toISOString(), pending: true }]
  history.value = pending
  message.value = ''
  scrollDown()
  try {
    const res = await api.chat(pid.value, run.value.id, { agent_id: pickedId.value, message: text, variant: chatVariant.value })
    history.value = res.history
    scrollDown()
  } catch (e) {
    chatError.value = e.message
    history.value = pending.filter((m) => !m.pending)
    message.value = text
  } finally {
    sending.value = false
  }
}
function onKey(ev) {
  if (ev.key === 'Enter' && !ev.shiftKey) {
    ev.preventDefault()
    send()
  }
}

// Ask the crowd
const question = ref('')
const askVariant = ref('')
const asking = ref(false)
const askError = ref('')
const asks = ref([])
const shownAsk = ref(null)
watch(variants, (vs) => {
  if (vs.length && !vs.some((v) => v.id === askVariant.value)) askVariant.value = vs[0].id
}, { immediate: true })

async function loadAsks() {
  asks.value = []
  shownAsk.value = null
  if (!finished.value) return
  try {
    const list = await api.asked(pid.value, run.value.id)
    asks.value = [...list].reverse()
    shownAsk.value = asks.value[0] || null
  } catch (e) {
    askError.value = e.message
  }
}
watch(() => run.value?.id + ':' + finished.value, loadAsks, { immediate: true })

async function ask() {
  const q = question.value.trim()
  if (!q) return
  asking.value = true
  askError.value = ''
  try {
    const res = await api.ask(pid.value, run.value.id, { question: q, variant: askVariant.value || undefined })
    asks.value = [res, ...asks.value]
    shownAsk.value = res
    question.value = ''
  } catch (e) {
    askError.value = e.message
  } finally {
    asking.value = false
  }
}

const vIndex = computed(() => Object.fromEntries(variants.value.map((v) => [v.id, v.index])))
const vLabel = computed(() => Object.fromEntries(variants.value.map((v) => [v.id, v.label])))
const topSegments = computed(() => {
  const segs = shownAsk.value?.segments || {}
  const rows = segs.group || segs[Object.keys(segs)[0]] || []
  return [...rows].sort((a, b) => b.mean_outcome - a.mean_outcome)
})
</script>

<template>
  <div class="stack-lg">
    <div v-if="!finished" class="panel empty">
      <h3>Pick a finished run</h3>
      <p>People remember what happened in a run, so choose a finished one in the run menu above.</p>
    </div>
    <template v-else>
      <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>
      <div class="ask-grid">
        <section class="panel stack chat-panel" aria-labelledby="chat-head">
          <div class="panel-head">
            <h2 id="chat-head">Talk to one person</h2>
            <p>They answer in character, from their persona and what they saw in the run.</p>
          </div>

          <div class="picker-row">
            <label class="field grow">
              <span class="label">Find a person</span>
              <input v-model="who" type="search" placeholder="Name or group" autocomplete="off" />
            </label>
            <label v-if="variants.length > 1" class="field">
              <span class="label">Variant</span>
              <select v-model="chatVariant">
                <option v-for="v in variants" :key="v.id" :value="v.id">{{ v.label }}</option>
              </select>
            </label>
          </div>
          <ul class="people" role="listbox" aria-label="People">
            <li v-for="a in matches" :key="a.agent_id">
              <button
                type="button"
                role="option"
                :aria-selected="a.agent_id === pickedId"
                :class="{ on: a.agent_id === pickedId }"
                @click="pickedId = a.agent_id"
              >
                <span class="p-name break">{{ a.name }}</span>
                <span class="muted small">{{ a.kind === 'stakeholder' ? 'Stakeholder' : a.segment }}</span>
              </button>
            </li>
            <li v-if="!matches.length" class="muted small pad">Nobody matches.</li>
          </ul>

          <div v-if="picked" class="convo stack">
            <div class="persona">
              <p><strong class="break">{{ picked.name }}</strong> <span class="muted small">{{ picked.segment }}</span></p>
              <p class="small muted break">{{ picked.bio }}</p>
            </div>
            <div ref="thread" class="thread" aria-live="polite">
              <p v-if="!history.length" class="muted small">No messages yet. Ask what they think and why.</p>
              <div v-for="(m, i) in history" :key="i" class="msg" :class="[m.role, { pending: m.pending }]">
                <p class="break">{{ m.content }}</p>
              </div>
              <div v-if="sending" class="msg assistant typing"><p class="muted">Writing a reply</p></div>
            </div>
            <form class="composer" @submit.prevent="send">
              <label class="sr-only" for="chat-input">Message</label>
              <textarea id="chat-input" v-model="message" rows="2" placeholder="Would you pay more for weekly cleaning?" @keydown="onKey"></textarea>
              <button class="btn primary" type="submit" :disabled="sending || !message.trim()">Send</button>
            </form>
            <div v-if="chatError" class="notice error" role="alert">{{ chatError }}</div>
          </div>
          <p v-else class="muted small">Pick someone from the list to start.</p>
        </section>

        <section class="panel stack" aria-labelledby="ask-head">
          <div class="panel-head">
            <h2 id="ask-head">Ask the whole crowd</h2>
            <p>Jev polls every person with a new yes or no question. It takes a few seconds.</p>
          </div>
          <form class="stack" @submit.prevent="ask">
            <label class="field">
              <span class="label">Question</span>
              <textarea v-model="question" rows="2" placeholder="Would you recommend Lazybee to a friend?"></textarea>
            </label>
            <div class="row">
              <label v-if="variants.length > 1" class="field">
                <span class="label">Variant</span>
                <select v-model="askVariant">
                  <option v-for="v in variants" :key="v.id" :value="v.id">{{ v.label }}</option>
                </select>
              </label>
              <span class="spacer"></span>
              <button class="btn primary ask-btn" type="submit" :disabled="asking || !question.trim()">
                {{ asking ? `Polling ${agents.length} people` : 'Ask the crowd' }}
              </button>
            </div>
          </form>
          <div v-if="askError" class="notice error" role="alert">{{ askError }}</div>

          <article v-if="shownAsk" class="result stack" aria-live="polite">
            <p class="r-q break">{{ shownAsk.question }}</p>
            <p class="muted small">{{ vLabel[shownAsk.variant] || shownAsk.variant }}, asked {{ when(shownAsk.at) }}</p>
            <p class="big">
              <span class="figure">{{ num(shownAsk.summary.expected_yes) }}</span>
              <span>of {{ shownAsk.summary.n }} expected to say yes</span>
            </p>
            <dl class="facts">
              <div><dt>90% range</dt><dd class="tnum">{{ num(shownAsk.summary.low) }} to {{ num(shownAsk.summary.high) }}</dd></div>
              <div><dt>Mean chance of yes</dt><dd class="tnum">{{ pct(shownAsk.summary.mean_outcome, 1) }}</dd></div>
            </dl>
            <SwarmDots
              :n="shownAsk.summary.n"
              :expected="shownAsk.summary.expected_yes"
              :low="shownAsk.summary.low"
              :high="shownAsk.summary.high"
              :index="vIndex[shownAsk.variant] ?? 0"
              :label="shownAsk.question"
            />
            <p class="caveat">Ranges cover chance only, not model error. The crowd is synthetic.</p>

            <div v-if="topSegments.length" class="stack">
              <h3>By group</h3>
              <div class="table-scroll">
                <table class="data">
                  <thead><tr><th>Group</th><th class="num">People</th><th class="num">Chance of yes</th><th class="num">Expected yes</th></tr></thead>
                  <tbody>
                    <tr v-for="s in topSegments" :key="s.value">
                      <td class="break">{{ s.value }}</td>
                      <td class="num">{{ s.n }}</td>
                      <td class="num">{{ pct(s.mean_outcome) }}</td>
                      <td class="num">{{ num(s.expected_yes) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="grid-2 names">
              <div>
                <h3>Most likely yes</h3>
                <ol><li v-for="p in shownAsk.most_yes" :key="p.name"><span class="break">{{ p.name }}</span> <span class="muted tnum">{{ pct(p.p) }}</span></li></ol>
              </div>
              <div>
                <h3>Most likely no</h3>
                <ol><li v-for="p in shownAsk.most_no" :key="p.name"><span class="break">{{ p.name }}</span> <span class="muted tnum">{{ pct(p.p) }}</span></li></ol>
              </div>
            </div>
            <p class="muted small tnum">{{ shownAsk.requests }} Jev requests, {{ shownAsk.cache_hits }} from cache</p>
          </article>

          <div v-if="asks.length" class="stack">
            <h3>Earlier questions</h3>
            <ul class="asks">
              <li v-for="(a, i) in asks" :key="i">
                <button type="button" :class="{ on: a === shownAsk }" @click="shownAsk = a">
                  <span class="break">{{ a.question }}</span>
                  <span class="muted small tnum nowrap">{{ num(a.summary.expected_yes) }} of {{ a.summary.n }}, {{ pct(a.summary.mean_outcome) }}</span>
                </button>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ask-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; align-items: start; }
@media (max-width: 1000px) { .ask-grid { grid-template-columns: minmax(0, 1fr); } }
.picker-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
.picker-row .grow { flex: 1 1 200px; }
.label { font-size: 13px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 6px; }
.people { list-style: none; margin: 0; padding: 4px; max-height: 200px; overflow-y: auto; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.people button { width: 100%; font: inherit; text-align: left; background: none; border: 0; border-radius: 4px; padding: 6px 8px; cursor: pointer; display: flex; gap: 8px; align-items: baseline; justify-content: space-between; color: var(--ink); }
.people button:hover { background: var(--panel-2); }
.people button.on { background: var(--accent-soft); }
.p-name { font-weight: 600; font-size: 14px; }
.pad { padding: 8px; }
.persona { background: var(--panel-2); border-radius: var(--radius-sm); padding: 10px 12px; }
.thread { display: flex; flex-direction: column; gap: 8px; max-height: 420px; min-height: 120px; overflow-y: auto; padding: 4px 2px; }
.msg { max-width: 85%; padding: 8px 12px; border-radius: 14px; font-size: 14px; white-space: pre-wrap; }
.msg.user { align-self: flex-end; background: var(--accent); color: var(--accent-ink); border-bottom-right-radius: 4px; }
.msg.assistant { align-self: flex-start; background: var(--panel-2); border: 1px solid var(--line); border-bottom-left-radius: 4px; }
.msg.pending { opacity: 0.7; }
.composer { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: end; }
.r-q { font-size: 17px; font-weight: 600; }
.result { border-top: 1px solid var(--line); padding-top: 16px; }
.big { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; color: var(--ink-2); }
.figure { font-size: 40px; font-weight: 650; letter-spacing: -0.02em; line-height: 1; color: var(--ink); }
.facts { margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 16px; }
.facts dt { font-size: 13px; color: var(--muted); }
.facts dd { margin: 0; font-weight: 600; }
.names ol { margin: 6px 0 0; padding-left: 20px; font-size: 14px; }
.asks { list-style: none; margin: 0; padding: 0; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.asks li + li { border-top: 1px solid var(--line); }
.asks button { width: 100%; font: inherit; font-size: 14px; text-align: left; background: none; border: 0; padding: 8px 12px; cursor: pointer; display: flex; gap: 12px; justify-content: space-between; align-items: baseline; color: var(--ink); flex-wrap: wrap; }
.asks button:hover { background: var(--panel-2); }
.asks button.on { background: var(--accent-soft); }
</style>
