<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../lib/api.js'
import { int, pct } from '../lib/format.js'
import { useWorkspace } from '../lib/workspace.js'
import FrameEditor from '../components/FrameEditor.vue'
import TaskStatus from '../components/TaskStatus.vue'

const ws = useWorkspace()
const pid = ws.pid
const ov = computed(() => ws.overview.value)
const task = computed(() => ws.tasks.prepare)
const busy = computed(() => task.value && (task.value.status === 'queued' || task.value.status === 'running'))

const publicSize = ref(60)
const maxStakeholders = ref(20)
const seed = ref(0)
const prepError = ref('')

async function prepare() {
  prepError.value = ''
  const ps = Number(publicSize.value)
  const ms = Number(maxStakeholders.value)
  if (!Number.isInteger(ps) || ps < 1 || ps > 2000) return (prepError.value = 'Public size must be a whole number from 1 to 2000.')
  if (!Number.isInteger(ms) || ms < 0 || ms > 200) return (prepError.value = 'Stakeholders must be a whole number from 0 to 200.')
  try {
    const t = await api.prepare(pid.value, { public_size: ps, max_stakeholders: ms, seed: Number(seed.value) || 0 })
    const final = await ws.track(t)
    if (final.status === 'done') await load(true)
  } catch (e) {
    prepError.value = e.message
  }
}

const frame = computed(() => ws.frame.value)
const crowd = computed(() => ws.crowd.value)
const loadError = ref('')
async function load(force = false) {
  loadError.value = ''
  try {
    await Promise.all([ws.loadFrame(force), ws.loadCrowd(force)])
  } catch (e) {
    if (e.status !== 400) loadError.value = e.message
  }
}
watch(() => ov.value?.has_frame && ov.value?.crowd_stats, (ready) => ready && load(), { immediate: true })

const saving = ref(false)
const saveError = ref('')
const savedAt = ref(0)
async function saveFrame(f) {
  saving.value = true
  saveError.value = ''
  try {
    ws.frame.value = await api.saveFrame(pid.value, f)
    savedAt.value = Date.now()
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

// Crowd table
const filter = ref('')
const kindFilter = ref('all')
const limit = ref(100)
const followers = computed(() => {
  const counts = {}
  for (const a of crowd.value?.agents || []) for (const f of a.follows || []) counts[f] = (counts[f] || 0) + 1
  return counts
})
const rows = computed(() => {
  const term = filter.value.trim().toLowerCase()
  return (crowd.value?.agents || []).filter((a) => {
    if (kindFilter.value !== 'all' && a.kind !== kindFilter.value) return false
    if (!term) return true
    const attrs = Object.entries(a.attributes || {}).map(([k, v]) => `${k} ${v}`).join(' ')
    return `${a.name} ${a.username} ${a.segment} ${a.kind} ${a.stance_hint} ${a.bio} ${attrs}`.toLowerCase().includes(term)
  })
})
watch([filter, kindFilter], () => (limit.value = 100))
const STANCE = { for: 'For', against: 'Against', neutral: 'Neutral', mixed: 'Mixed' }
const maxShare = computed(() => Math.max(0.0001, ...(crowd.value?.segments || []).map((s) => s.share)))
function attrText(attrs) {
  return Object.entries(attrs || {})
    .map(([k, dist]) => {
      if (dist && typeof dist === 'object') {
        return `${k}: ` + Object.entries(dist).map(([v, p]) => `${v} ${pct(p)}`).join(', ')
      }
      return `${k}: ${dist}`
    })
    .join('; ')
}
</script>

<template>
  <div class="stack-lg">
    <section class="panel" aria-labelledby="prep-head">
      <div class="panel-head">
        <h2 id="prep-head">Prepare the crowd</h2>
        <p>Writes the prediction frame, turns graph entities into stakeholders and samples members of the public.</p>
      </div>
      <form class="stack" @submit.prevent="prepare">
        <div class="form-grid">
          <label class="field">
            <span class="label">Members of the public</span>
            <input v-model.number="publicSize" type="number" min="1" max="2000" step="1" />
          </label>
          <label class="field">
            <span class="label">Stakeholders, at most</span>
            <input v-model.number="maxStakeholders" type="number" min="0" max="200" step="1" />
          </label>
          <label class="field">
            <span class="label">Random seed</span>
            <input v-model.number="seed" type="number" step="1" />
          </label>
        </div>
        <div class="row">
          <button class="btn primary" type="submit" :disabled="busy">{{ ov?.crowd_stats ? 'Prepare again' : 'Prepare' }}</button>
          <span v-if="ov?.crowd_stats" class="muted small">Preparing again replaces the frame and the crowd, including edits.</span>
        </div>
        <div v-if="prepError" class="notice error" role="alert">{{ prepError }}</div>
        <TaskStatus :task="task" :label="busy ? 'Preparing the crowd' : ''" />
      </form>
    </section>

    <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>

    <section v-if="frame" class="panel" aria-labelledby="frame-head">
      <div class="panel-head">
        <h2 id="frame-head">Frame</h2>
        <p>What every person is asked, and the arguments in play.</p>
      </div>
      <FrameEditor :frame="frame" :saving="saving" :error="saveError" :saved-at="savedAt" @save="saveFrame" />
    </section>

    <section v-if="crowd" class="panel" aria-labelledby="crowd-head">
      <div class="panel-head">
        <h2 id="crowd-head">Crowd</h2>
        <p>{{ int(crowd.agents.length) }} people: {{ int(crowd.stats.stakeholders) }} stakeholders and {{ int(crowd.stats.public) }} members of the public.</p>
      </div>

      <div v-if="crowd.segments.length" class="segments stack">
        <h3>Public segments</h3>
        <ul class="seg-list">
          <li v-for="s in crowd.segments" :key="s.name">
            <div class="seg-top">
              <strong class="break">{{ s.name }}</strong>
              <span class="tnum">{{ pct(s.share) }}</span>
            </div>
            <div class="bar-track" role="img" :aria-label="`${s.name}: ${pct(s.share)} of the public`">
              <div class="bar" :style="{ width: (s.share / maxShare) * 100 + '%' }"></div>
            </div>
            <p class="small muted break">{{ s.description }}</p>
            <p v-if="Object.keys(s.attributes || {}).length" class="small muted break">{{ attrText(s.attributes) }}</p>
          </li>
        </ul>
      </div>

      <div class="stack crowd-table">
        <div class="row">
          <h3>People</h3>
          <span class="spacer"></span>
          <select v-model="kindFilter" class="kind" aria-label="Filter by kind">
            <option value="all">Everyone</option>
            <option value="stakeholder">Stakeholders</option>
            <option value="public">Public</option>
          </select>
          <input v-model="filter" type="search" class="filter" placeholder="Filter by name, group or trait" aria-label="Filter people" />
        </div>
        <p class="muted small">Showing {{ Math.min(limit, rows.length) }} of {{ rows.length }}</p>
        <div class="table-scroll bordered">
          <table class="data">
            <thead>
              <tr>
                <th>Name</th><th>Kind</th><th>Group</th><th>Leaning</th>
                <th class="num">Influence</th><th class="num">Activity</th><th class="num">Followers</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in rows.slice(0, limit)" :key="a.agent_id">
                <td class="who">
                  <span class="name break">{{ a.name }}</span>
                  <span class="muted small bio">{{ a.bio }}</span>
                </td>
                <td>{{ a.kind === 'stakeholder' ? 'Stakeholder' : 'Public' }}</td>
                <td class="break">{{ a.segment }}</td>
                <td>{{ STANCE[a.stance_hint] || a.stance_hint }}</td>
                <td class="num">{{ a.influence.toFixed(2) }}</td>
                <td class="num">{{ a.activity.toFixed(2) }}</td>
                <td class="num">{{ followers[a.agent_id] || 0 }}</td>
              </tr>
              <tr v-if="!rows.length"><td colspan="7" class="muted">Nobody matches that filter.</td></tr>
            </tbody>
          </table>
        </div>
        <div v-if="rows.length > limit"><button class="btn small" type="button" @click="limit += 200">Show more people</button></div>
      </div>
    </section>

    <div v-if="crowd && frame" class="row end">
      <RouterLink class="btn primary" :to="{ name: 'simulate', params: { pid } }">Set up a run</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.seg-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.seg-top { display: flex; justify-content: space-between; gap: 8px; }
.bar-track { height: 10px; margin: 6px 0; }
.bar { height: 100%; background: var(--s1); border-radius: 0 4px 4px 0; min-width: 2px; }
.crowd-table { margin-top: 28px; }
.kind { width: auto; }
.filter { max-width: 280px; }
@media (max-width: 600px) { .filter { max-width: none; } }
.bordered { border: 1px solid var(--line); border-radius: var(--radius-sm); max-height: 560px; overflow-y: auto; }
.who { min-width: 220px; max-width: 380px; }
.who .name { display: block; font-weight: 600; }
.bio { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
