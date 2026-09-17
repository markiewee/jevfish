<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { api } from '../lib/api.js'
import { debounce, int, usd } from '../lib/format.js'
import { ACTIVE_RUN, FINISHED, runLabel, useWorkspace } from '../lib/workspace.js'
import ActionFeed from '../components/ActionFeed.vue'
import RunResults from '../components/RunResults.vue'
import TaskStatus from '../components/TaskStatus.vue'

const ws = useWorkspace()
const pid = ws.pid

const frame = computed(() => ws.frame.value)
const loadError = ref('')
Promise.all([ws.loadFrame(), ws.loadCrowd()]).catch((e) => (loadError.value = e.message))

// Settings
const form = reactive({
  platform: 'reddit',
  rounds: 12,
  min: 8,
  max: 20,
  variants: [],
  injections: [],
  pollRounds: '',
  maxRequests: '',
})
// New variants start checked; ones the user unchecked stay unchecked.
watch(
  () => (frame.value ? frame.value.variants.map((v) => v.id).join('') : null),
  (ids, old) => {
    if (ids == null) return
    const all = ids.split('')
    const before = old ? old.split('') : []
    form.variants = all.filter((id) => !before.includes(id) || form.variants.includes(id))
  },
  { immediate: true },
)
let injKey = 0
function addInjection() {
  form.injections.push({ key: ++injKey, round: Math.max(1, Math.floor(Number(form.rounds) / 2) || 1), text: '', author: '' })
}

const clientError = computed(() => {
  const r = Number(form.rounds)
  if (!Number.isInteger(r) || r < 1 || r > 500) return 'Rounds must be a whole number from 1 to 500.'
  const mn = Number(form.min)
  const mx = Number(form.max)
  if (!Number.isInteger(mn) || !Number.isInteger(mx) || mn < 1 || mn > mx) return 'People per round: the minimum must be at least 1 and no more than the maximum.'
  if (frame.value && !form.variants.length) return 'Pick at least one variant.'
  for (const [i, inj] of form.injections.entries()) {
    if (!inj.text.trim()) return `News item ${i + 1} needs text.`
    const ir = Number(inj.round)
    if (!Number.isInteger(ir) || ir < 1 || ir > r) return `News item ${i + 1} needs a round from 1 to ${r}.`
  }
  if (form.pollRounds.trim()) {
    const parts = form.pollRounds.split(/[\s,]+/).filter(Boolean)
    if (parts.some((p) => !/^\d+$/.test(p) || Number(p) > r)) return `Poll rounds must be whole numbers from 0 to ${r}, separated by commas.`
  }
  if (String(form.maxRequests).trim() && (!/^\d+$/.test(String(form.maxRequests).trim()) || Number(form.maxRequests) < 1))
    return 'Request cap must be a positive whole number, or blank for the server default.'
  return ''
})

const config = computed(() => {
  const all = frame.value?.variants.map((v) => v.id) || []
  const cfg = {
    platform: form.platform,
    rounds: Number(form.rounds),
    agents_per_round_min: Number(form.min),
    agents_per_round_max: Number(form.max),
    variants: form.variants.length === all.length ? [] : all.filter((id) => form.variants.includes(id)),
    injections: form.injections.map((i) => ({ round: Number(i.round), text: i.text.trim(), ...(i.author.trim() ? { author: i.author.trim() } : {}) })),
    poll_rounds: form.pollRounds.trim() ? form.pollRounds.split(/[\s,]+/).filter(Boolean).map(Number) : null,
    max_requests: String(form.maxRequests).trim() ? Number(form.maxRequests) : null,
  }
  return cfg
})

// Live estimate
const estimate = ref(null)
const estError = ref('')
const estimating = ref(false)
let estSeq = 0
const runEstimate = debounce(async () => {
  if (clientError.value) {
    estimate.value = null
    return
  }
  const seq = ++estSeq
  estimating.value = true
  try {
    const e = await api.estimate(pid.value, config.value)
    if (seq === estSeq) {
      estimate.value = e
      estError.value = ''
    }
  } catch (e) {
    if (seq === estSeq) {
      estError.value = e.message
      estimate.value = null
    }
  } finally {
    if (seq === estSeq) estimating.value = false
  }
}, 400)
watch(() => JSON.stringify(config.value) + clientError.value, runEstimate, { immediate: true })
const overCap = computed(() => estimate.value && estimate.value.planned_requests > estimate.value.cap)

// Start
const runTask = computed(() => ws.tasks.run)
const anyActive = computed(() => ws.runs.value.some((r) => ACTIVE_RUN.has(r.status)) || (runTask.value && ['queued', 'running'].includes(runTask.value.status)))
const starting = ref(false)
const startError = ref('')
async function start() {
  startError.value = ''
  if (clientError.value) return (startError.value = clientError.value)
  starting.value = true
  try {
    const { run, task } = await api.startRun(pid.value, config.value)
    await ws.refresh()
    ws.selectedRunId.value = run.id
    ws.track(task)
  } catch (e) {
    startError.value = e.message
  } finally {
    starting.value = false
  }
}

// Selected run
const run = computed(() => ws.selectedRun.value)
const active = computed(() => !!run.value && ACTIVE_RUN.has(run.value.status))
const liveTask = computed(() => (run.value && runTask.value && runTask.value.id === run.value.task_id ? runTask.value : null))
const detail = ref(null)
const detailError = ref('')
async function loadDetail(force) {
  detailError.value = ''
  if (!run.value) return (detail.value = null)
  try {
    detail.value = await ws.loadRun(run.value.id, force)
  } catch (e) {
    detailError.value = e.message
  }
}
watch(() => run.value && `${run.value.id}:${run.value.status}`, () => loadDetail(true), { immediate: true })

const cancelling = ref(false)
async function cancel() {
  if (!run.value) return
  cancelling.value = true
  try {
    await api.cancelRun(pid.value, run.value.id)
    await ws.refresh()
  } catch (e) {
    detailError.value = e.message
  } finally {
    cancelling.value = false
  }
}

const variantList = computed(() => {
  const ids = run.value?.variants?.length ? run.value.variants : frame.value?.variants.map((v) => v.id) || []
  const labels = Object.fromEntries((frame.value?.variants || []).map((v) => [v.id, v.label]))
  for (const v of detail.value?.summary?.variants || []) labels[v.id] = v.label
  return ids.map((id) => ({ id, label: labels[id] || id }))
})
const points = computed(() => Object.fromEntries((frame.value?.talking_points || []).map((p) => [p.id, p.text])))
const runPct = computed(() => Math.round((liveTask.value?.progress ?? run.value?.progress ?? 0) * 100))
const STATUS = { queued: 'Queued', running: 'Running', done: 'Finished', partial: 'Partly finished', failed: 'Failed', cancelled: 'Cancelled' }
const showForm = ref(true)
watch(() => ws.runs.value.length, (n) => (showForm.value = n === 0 || showForm.value), { immediate: true })
onBeforeUnmount(() => estSeq++)
</script>

<template>
  <div class="stack-lg">
    <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>

    <section class="panel" aria-labelledby="set-head">
      <div class="panel-head">
        <h2 id="set-head">New run</h2>
        <p>Each round, some people read their feed and Jev picks what each one does.</p>
      </div>
      <form class="run-grid" @submit.prevent="start">
        <div class="stack-lg">
          <div class="form-grid">
            <label class="field">
              <span class="label">Platform</span>
              <select v-model="form.platform">
                <option value="reddit">Reddit style</option>
                <option value="lite">Lite (fast, in memory)</option>
                <option value="twitter">Twitter style</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Rounds</span>
              <input v-model.number="form.rounds" type="number" min="1" max="500" step="1" />
            </label>
            <label class="field">
              <span class="label">People per round, min</span>
              <input v-model.number="form.min" type="number" min="1" step="1" />
            </label>
            <label class="field">
              <span class="label">People per round, max</span>
              <input v-model.number="form.max" type="number" min="1" step="1" />
            </label>
          </div>
          <p v-if="form.platform === 'twitter'" class="notice info small">
            The Twitter style platform downloads a recommendation model of about 500 MB the first time it runs.
          </p>

          <fieldset v-if="frame" class="stack">
            <legend class="label">Variants to run</legend>
            <div class="checks">
              <label v-for="v in frame.variants" :key="v.id" class="check">
                <input v-model="form.variants" type="checkbox" :value="v.id" />
                <span class="break">{{ v.label }} <span class="muted small">{{ v.id }}</span></span>
              </label>
            </div>
          </fieldset>

          <fieldset class="stack">
            <legend class="label">News during the run</legend>
            <p v-if="!form.injections.length" class="muted small">None. Add a news post to see how the crowd reacts to it.</p>
            <div v-for="(inj, i) in form.injections" :key="inj.key" class="inj">
              <label class="field inj-round"><span class="label small">Round</span><input v-model.number="inj.round" type="number" min="1" :max="form.rounds" step="1" /></label>
              <label class="field inj-text"><span class="label small">Text</span><input v-model="inj.text" type="text" placeholder="Coliving Co cuts its rent by 10%" /></label>
              <label class="field inj-author"><span class="label small">Posted by</span><input v-model="inj.author" type="text" placeholder="News desk" /></label>
              <button class="btn small ghost" type="button" @click="form.injections.splice(i, 1)" :aria-label="`Remove news item ${i + 1}`">Remove</button>
            </div>
            <div><button class="btn small" type="button" @click="addInjection">Add news</button></div>
          </fieldset>

          <div class="form-grid">
            <label class="field">
              <span class="label">Poll after rounds</span>
              <input v-model="form.pollRounds" type="text" :placeholder="`0, ${Math.floor((Number(form.rounds) || 0) / 2)}, ${form.rounds}`" />
              <span class="hint">0 means before round 1. Blank uses the start, middle and end.</span>
            </label>
            <label class="field">
              <span class="label">Request cap</span>
              <input v-model="form.maxRequests" type="text" inputmode="numeric" placeholder="Server default" />
              <span class="hint">The run refuses to start above this.</span>
            </label>
          </div>
        </div>

        <aside class="estimate" aria-live="polite">
          <h3>Estimate</h3>
          <template v-if="estimate">
            <p class="est-big tnum" :class="{ stale: estimating }">{{ int(estimate.planned_requests) }}</p>
            <p class="muted small">Jev requests at most, cap {{ int(estimate.cap) }}</p>
            <dl class="est">
              <div><dt>Estimated cost</dt><dd class="tnum">{{ usd(estimate.est_cost_usd) }}</dd></div>
              <div><dt>Input tokens</dt><dd class="tnum">{{ int(estimate.est_input_tokens) }}</dd></div>
              <div><dt>Polls after rounds</dt><dd class="tnum">{{ estimate.polls.join(', ') }}</dd></div>
            </dl>
            <p v-if="overCap" class="notice warn small">This is over the cap. Lower the rounds or people per round, or raise the cap.</p>
          </template>
          <p v-else-if="estimating" class="muted small">Working it out</p>
          <p v-if="clientError" class="notice error small">{{ clientError }}</p>
          <p v-else-if="estError" class="notice error small">{{ estError }}</p>
          <button class="btn primary start" type="submit" :disabled="starting || anyActive || !!clientError || overCap">
            {{ starting ? 'Starting' : 'Start run' }}
          </button>
          <p v-if="anyActive" class="muted small">A run is already going. Wait for it or cancel it.</p>
          <p v-if="startError" class="notice error small" role="alert">{{ startError }}</p>
        </aside>
      </form>
    </section>

    <section v-if="run" class="panel stack-lg" aria-labelledby="run-head">
      <div class="panel-head run-head">
        <h2 id="run-head">Run</h2>
        <span class="pill" :class="{ good: run.status === 'done', warn: run.status === 'partial' || run.status === 'cancelled', bad: run.status === 'failed', accent: active }">
          {{ STATUS[run.status] || run.status }}
        </span>
        <p class="break">{{ runLabel(run) }}</p>
      </div>

      <div v-if="active" class="live stack">
        <div class="row">
          <strong>{{ run.status === 'queued' ? 'Waiting to start' : 'Simulating' }}</strong>
          <span class="muted small tnum">{{ runPct }}%</span>
          <span class="muted small tnum" v-if="run.requests != null">{{ int(run.requests) }} of {{ int(run.planned_requests) }} requests</span>
          <span class="spacer"></span>
          <button class="btn small danger" type="button" :disabled="cancelling" @click="cancel">{{ cancelling ? 'Cancelling' : 'Cancel run' }}</button>
        </div>
        <div class="progress" role="progressbar" :aria-valuenow="runPct" aria-valuemin="0" aria-valuemax="100"><div :style="{ width: runPct + '%' }"></div></div>
        <p class="small muted break">{{ liveTask?.message || run.message }}</p>
      </div>
      <TaskStatus v-else-if="liveTask && liveTask.status !== 'done'" :task="liveTask" />
      <p v-if="run.status === 'failed' && run.error" class="notice error break">{{ run.error }}</p>
      <p v-if="run.status === 'cancelled'" class="notice warn">This run was cancelled before it finished.</p>
      <p v-if="detailError" class="notice error">{{ detailError }}</p>

      <RunResults v-if="detail?.summary && FINISHED.has(run.status)" :summary="detail.summary" :run="detail" />

      <div class="stack">
        <h3>Activity</h3>
        <ActionFeed :pid="pid" :run-id="run.id" :active="active" :variants="variantList" :points="points" />
      </div>

      <div v-if="FINISHED.has(run.status)" class="row end">
        <RouterLink class="btn" :to="{ name: 'ask', params: { pid }, query: { run: run.id } }">Ask the crowd</RouterLink>
        <RouterLink class="btn primary" :to="{ name: 'report', params: { pid }, query: { run: run.id } }">Go to the report</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.run-grid { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 24px; align-items: start; }
@media (max-width: 900px) { .run-grid { grid-template-columns: minmax(0, 1fr); } }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
legend.label, .label { font-size: 13px; font-weight: 600; color: var(--ink-2); padding: 0; }
.checks { display: flex; flex-wrap: wrap; gap: 8px 20px; }
.inj { display: grid; grid-template-columns: 80px minmax(0, 1fr) 160px auto; gap: 8px; align-items: end; }
@media (max-width: 640px) {
  .inj { grid-template-columns: 80px minmax(0, 1fr); }
  .inj-text { grid-column: 1 / -1; grid-row: 2; }
}
.estimate { position: sticky; top: 16px; background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; display: grid; gap: 8px; }
.est-big { font-size: 36px; font-weight: 650; line-height: 1.1; letter-spacing: -0.02em; }
.est-big.stale { opacity: 0.5; }
.est { margin: 4px 0; display: grid; gap: 6px; }
.est div { display: flex; justify-content: space-between; gap: 12px; font-size: 14px; }
.est dt { color: var(--muted); }
.est dd { margin: 0; font-weight: 600; text-align: right; }
.start { width: 100%; margin-top: 4px; }
.run-head { margin-bottom: 0; }
.run-head p { flex-basis: 100%; }
.live { padding: 14px; border-radius: var(--radius-sm); background: var(--accent-soft); }
</style>
