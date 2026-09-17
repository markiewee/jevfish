<script setup>
import { computed, onBeforeUnmount, provide, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, waitForTask } from '../lib/api.js'
import { STAGE_LABEL } from '../lib/format.js'
import { ACTIVE_RUN, FINISHED, WS_KEY, runLabel } from '../lib/workspace.js'

const props = defineProps({ pid: { type: String, required: true } })
const route = useRoute()
const router = useRouter()

const overview = ref(null)
const loadError = ref('')
const tasks = reactive({})
const tracking = new Set()
const frame = shallowRef(null)
const crowd = shallowRef(null)
const runDetails = reactive({})
let alive = true
onBeforeUnmount(() => (alive = false))

const stageIndex = computed(() => ['new', 'seeded', 'graph', 'prepared'].indexOf(overview.value?.stage ?? 'new'))
const runs = computed(() => [...(overview.value?.runs || [])].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)))
const finishedRuns = computed(() => runs.value.filter((r) => FINISHED.has(r.status)))

const selectedRunId = computed({
  get() {
    const q = route.query.run
    if (q && runs.value.some((r) => r.id === q)) return q
    return runs.value[0]?.id || ''
  },
  set(v) {
    router.replace({ query: { ...route.query, run: v || undefined } })
  },
})
const selectedRun = computed(() => runs.value.find((r) => r.id === selectedRunId.value) || null)

async function refresh() {
  try {
    const ov = await api.project(props.pid)
    if (!alive) return
    overview.value = ov
    loadError.value = ''
    resumeTasks(ov.tasks || [])
  } catch (e) {
    loadError.value = e.message
  }
}

function resumeTasks(list) {
  const seen = new Set()
  for (const t of [...list].sort((a, b) => (a.created_at < b.created_at ? 1 : -1))) {
    if (seen.has(t.kind)) continue
    seen.add(t.kind)
    if (!tasks[t.kind] || tasks[t.kind].id === t.id || new Date(t.created_at) > new Date(tasks[t.kind].created_at)) {
      if (!tracking.has(t.id)) tasks[t.kind] = t
    }
    if ((t.status === 'queued' || t.status === 'running') && !tracking.has(t.id)) track(t)
  }
}

async function track(task) {
  tracking.add(task.id)
  tasks[task.kind] = task
  try {
    const final = await waitForTask(task, (t) => {
      if (alive && (!tasks[t.kind] || tasks[t.kind].id === t.id)) tasks[t.kind] = t
    })
    if (task.kind === 'prepare' && final.status === 'done') {
      frame.value = null
      crowd.value = null
    }
    if (final.kind === 'run' || final.kind === 'report') {
      const rid = final.result?.run_id || selectedRunId.value
      if (rid) delete runDetails[rid]
    }
    if (alive) await refresh()
    return final
  } catch (e) {
    const failed = { ...tasks[task.kind], status: 'failed', error: e.message }
    tasks[task.kind] = failed
    return failed
  } finally {
    tracking.delete(task.id)
  }
}

async function loadFrame(force = false) {
  if (!frame.value || force) frame.value = await api.frame(props.pid)
  return frame.value
}
async function loadCrowd(force = false) {
  if (!crowd.value || force) crowd.value = await api.crowd(props.pid)
  return crowd.value
}
async function loadRun(rid, force = false) {
  if (!rid) return null
  if (!runDetails[rid] || force) runDetails[rid] = await api.run(props.pid, rid)
  return runDetails[rid]
}

const steps = computed(() => {
  const ov = overview.value
  const si = stageIndex.value
  const hasFinished = finishedRuns.value.length > 0
  return [
    { name: 'graph', n: 1, title: 'Graph', open: true, done: !!ov?.graph_stats, why: '' },
    { name: 'crowd', n: 2, title: 'Crowd', open: si >= 2, done: !!ov?.crowd_stats, why: 'Build the graph first' },
    { name: 'simulate', n: 3, title: 'Simulate', open: si >= 3, done: hasFinished, why: 'Prepare the crowd first' },
    { name: 'report', n: 4, title: 'Report', open: hasFinished, done: !!selectedRun.value?.report_ready, why: 'Finish a run first' },
    { name: 'ask', n: 5, title: 'Ask', open: hasFinished, done: false, why: 'Finish a run first' },
  ]
})
const current = computed(() => steps.value.find((s) => s.name === route.name) || steps.value[0])

// Project name and question editing
const editing = ref(false)
const editName = ref('')
const editQuestion = ref('')
const editError = ref('')
function startEdit() {
  editName.value = overview.value?.name || ''
  editQuestion.value = overview.value?.requirement || ''
  editError.value = ''
  editing.value = true
}
async function saveEdit() {
  try {
    await api.patchProject(props.pid, { name: editName.value, requirement: editQuestion.value })
    editing.value = false
    await refresh()
  } catch (e) {
    editError.value = e.message
  }
}

// Keep run status fresh while a run is active
let runTimer = null
watch(
  () => runs.value.some((r) => ACTIVE_RUN.has(r.status)),
  (active) => {
    clearInterval(runTimer)
    if (active) runTimer = setInterval(refresh, 2000)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearInterval(runTimer))

watch(() => props.pid, () => {
  overview.value = null
  frame.value = null
  crowd.value = null
  refresh()
}, { immediate: true })

provide(WS_KEY, {
  pid: computed(() => props.pid),
  overview,
  refresh,
  tasks,
  track,
  runs,
  finishedRuns,
  selectedRunId,
  selectedRun,
  loadFrame,
  loadCrowd,
  loadRun,
  runDetails,
  frame,
  crowd,
  steps,
})
</script>

<template>
  <div class="stack-lg">
    <RouterLink to="/" class="back small">All projects</RouterLink>
    <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>

    <template v-if="overview">
      <header class="ws-head">
        <template v-if="!editing">
          <div class="row title-row">
            <h1 class="break">{{ overview.name || 'Untitled' }}</h1>
            <span class="pill" :class="{ good: overview.stage === 'prepared' }">{{ STAGE_LABEL[overview.stage] || overview.stage }}</span>
            <button class="btn small ghost" type="button" @click="startEdit">Edit</button>
          </div>
          <p class="question break">{{ overview.requirement }}</p>
        </template>
        <form v-else class="edit-form" @submit.prevent="saveEdit">
          <label class="field"><span class="label">Project name</span><input v-model="editName" type="text" /></label>
          <label class="field"><span class="label">Prediction question</span><textarea v-model="editQuestion" rows="2"></textarea></label>
          <div v-if="editError" class="notice error">{{ editError }}</div>
          <div class="row">
            <button class="btn primary small" type="submit">Save</button>
            <button class="btn small" type="button" @click="editing = false">Cancel</button>
          </div>
        </form>
      </header>

      <nav class="stepbar" aria-label="Prediction steps">
        <ol class="steps">
          <li v-for="s in steps" :key="s.name">
            <RouterLink
              v-if="s.open"
              :to="{ name: s.name, params: { pid }, query: route.query.run ? { run: route.query.run } : {} }"
              class="step"
              :class="{ current: current.name === s.name, done: s.done }"
              :aria-current="current.name === s.name ? 'step' : undefined"
            >
              <span class="step-n" aria-hidden="true">
                <svg v-if="s.done && current.name !== s.name" width="12" height="12" viewBox="0 0 12 12"><path d="M2.5 6.2l2.3 2.3 4.7-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
                <template v-else>{{ s.n }}</template>
              </span>
              <span>{{ s.title }}</span>
            </RouterLink>
            <span v-else class="step locked" :title="s.why" aria-disabled="true">
              <span class="step-n" aria-hidden="true">{{ s.n }}</span>
              <span>{{ s.title }}</span>
              <span class="sr-only">(locked: {{ s.why }})</span>
            </span>
          </li>
        </ol>
        <label v-if="runs.length" class="run-pick">
          <span class="small muted">Run</span>
          <select v-model="selectedRunId">
            <option v-for="r in runs" :key="r.id" :value="r.id">{{ runLabel(r) }}</option>
          </select>
        </label>
      </nav>

      <div v-if="!current.open" class="panel empty">
        <h3>{{ current.title }} is not ready yet</h3>
        <p>{{ current.why }}.</p>
      </div>
      <RouterView v-else :key="pid" />
    </template>
    <p v-else-if="!loadError" class="muted">Loading project</p>
  </div>
</template>

<style scoped>
.back { color: var(--muted); text-decoration: none; display: inline-block; }
.back::before { content: '\2039'; margin-right: 6px; }
.back:hover { color: var(--ink); }
.stack-lg > .back + * { margin-top: 12px; }
.ws-head { max-width: 900px; }
.title-row { gap: 12px; }
.title-row h1 { font-size: 24px; }
.question { font-size: 20px; line-height: 1.4; margin-top: 8px; color: var(--ink-2); letter-spacing: -0.01em; }
@media (max-width: 600px) { .question { font-size: 17px; } }
.edit-form { display: grid; gap: 12px; }
.stepbar { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding-bottom: 12px; }
.steps { list-style: none; margin: 0; padding: 0; display: flex; gap: 4px; flex-wrap: wrap; flex: 1 1 auto; counter-reset: none; }
.step { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px 6px 6px; border-radius: 999px; text-decoration: none; color: var(--ink-2); font-weight: 600; font-size: 14px; }
a.step:hover { background: var(--panel); }
.step-n { width: 24px; height: 24px; border-radius: 50%; display: inline-grid; place-items: center; font-size: 12px; border: 1px solid var(--line-strong); color: var(--muted); background: var(--panel); font-variant-numeric: tabular-nums; }
.step.done .step-n { border-color: transparent; background: var(--accent-soft); color: var(--accent-text); }
.step.current { background: var(--panel); color: var(--ink); box-shadow: inset 0 0 0 1px var(--line); }
.step.current .step-n { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.step.locked { color: var(--muted); opacity: 0.6; cursor: not-allowed; }
.run-pick { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 0 1 340px; }
.run-pick select { min-width: 0; }
@media (max-width: 600px) {
  .step { padding-right: 8px; font-size: 13px; }
  .run-pick { flex: 1 1 100%; }
}
</style>
