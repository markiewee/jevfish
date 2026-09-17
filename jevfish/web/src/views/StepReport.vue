<script setup>
import { computed, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { api } from '../lib/api.js'
import { int, pct, when } from '../lib/format.js'
import { seriesVar } from '../lib/palette.js'
import { FINISHED, useWorkspace } from '../lib/workspace.js'
import GroupedBars from '../components/GroupedBars.vue'
import TaskStatus from '../components/TaskStatus.vue'

const ws = useWorkspace()
const pid = ws.pid
const run = computed(() => ws.selectedRun.value)
const finished = computed(() => !!run.value && FINISHED.has(run.value.status))

const detail = ref(null)
const report = ref(null)
const error = ref('')
const reportFor = ref({}) // task id -> run id

async function load() {
  error.value = ''
  detail.value = null
  report.value = null
  if (!finished.value) return
  const rid = run.value.id
  try {
    const d = await ws.loadRun(rid, true)
    if (run.value?.id !== rid) return
    detail.value = d
    if (d.report_ready) report.value = await api.report(pid.value, rid)
  } catch (e) {
    error.value = e.message
  }
}
watch(() => run.value?.id + ':' + run.value?.status, load, { immediate: true })

const task = computed(() => {
  const t = ws.tasks.report
  if (!t) return null
  const owner = reportFor.value[t.id]
  if (owner && owner !== run.value?.id) return null
  if (!owner && !['queued', 'running'].includes(t.status)) return null
  return t
})
const busy = computed(() => !!ws.tasks.report && ['queued', 'running'].includes(ws.tasks.report.status))
const genError = ref('')
async function generate() {
  genError.value = ''
  const rid = run.value.id
  try {
    const t = await api.startReport(pid.value, rid)
    reportFor.value = { ...reportFor.value, [t.id]: rid }
    const final = await ws.track(t)
    if (final.status === 'done' && run.value?.id === rid) {
      report.value = await api.report(pid.value, rid)
      detail.value = await ws.loadRun(rid, true)
    }
  } catch (e) {
    genError.value = e.message
  }
}

const html = computed(() => {
  if (!report.value?.markdown) return ''
  return DOMPurify.sanitize(marked.parse(report.value.markdown, { gfm: true, breaks: false }), { USE_PROFILES: { html: true } })
})

// Data panels
const summary = computed(() => detail.value?.summary || null)
const variants = computed(() => (summary.value?.variants || []).map((v, index) => ({ ...v, index })))
const multi = computed(() => variants.value.length > 1)

const stance = computed(() => {
  if (!summary.value) return null
  return {
    categories: summary.value.stance_levels,
    series: variants.value
      .filter((v) => v.final)
      .map((v) => {
        const hist = v.final.stance_hist || []
        const total = hist.reduce((a, b) => a + b, 0) || 1
        return { id: v.id, label: v.label, index: v.index, values: hist.map((c) => c / total), counts: hist }
      }),
  }
})

const dims = computed(() => {
  const keys = new Set()
  for (const v of variants.value) for (const k of Object.keys(v.segments || {})) keys.add(k)
  const order = ['kind', 'group']
  return [...order.filter((k) => keys.has(k)), ...[...keys].filter((k) => !order.includes(k)).sort()]
})
const dim = ref('group')
watch(dims, (d) => { if (d.length && !d.includes(dim.value)) dim.value = d[0] }, { immediate: true })
const DIM_LABEL = { kind: 'Kind', group: 'Group' }
const segRows = computed(() => {
  const rows = new Map()
  for (const v of variants.value) {
    for (const r of v.segments?.[dim.value] || []) {
      if (!rows.has(r.value)) rows.set(r.value, { value: r.value, n: r.n, by: {} })
      rows.get(r.value).by[v.id] = r.mean_outcome
    }
  }
  const first = variants.value[0]?.id
  return [...rows.values()].sort((a, b) => (b.by[first] ?? 0) - (a.by[first] ?? 0))
})
function kindLabel(v) {
  return dim.value === 'kind' ? ({ stakeholder: 'Stakeholders', public: 'Public' }[v] || v) : v
}

const pointRows = computed(() => {
  const rows = new Map()
  for (const v of variants.value) {
    for (const p of v.points || []) {
      if (!rows.has(p.id)) rows.set(p.id, { id: p.id, text: p.text, side: p.side, by: {} })
      rows.get(p.id).by[v.id] = p
    }
  }
  const first = variants.value[0]?.id
  return [...rows.values()].sort((a, b) => (b.by[first]?.total ?? 0) - (a.by[first]?.total ?? 0))
})
const SIDE = { pro: 'For', con: 'Against', neutral: 'Neutral' }

const focusVariant = ref('')
watch(variants, (vs) => { if (vs.length && !vs.some((v) => v.id === focusVariant.value)) focusVariant.value = vs[0].id }, { immediate: true })
const focus = computed(() => variants.value.find((v) => v.id === focusVariant.value) || null)
</script>

<template>
  <div class="stack-lg">
    <div v-if="!finished" class="panel empty">
      <h3>Pick a finished run</h3>
      <p>The selected run has not finished. Choose another one in the run menu above.</p>
    </div>

    <template v-else>
      <div v-if="error" class="notice error" role="alert">{{ error }}</div>
      <div class="report-grid">
        <section class="panel stack" aria-labelledby="rep-head">
          <div class="panel-head">
            <h2 id="rep-head">Report</h2>
            <p v-if="report">Written {{ when(report.created_at) }}</p>
            <span class="spacer"></span>
            <button class="btn" :class="{ primary: !report }" type="button" :disabled="busy" @click="generate">
              {{ report ? 'Write again' : 'Generate report' }}
            </button>
          </div>
          <div v-if="genError" class="notice error" role="alert">{{ genError }}</div>
          <TaskStatus :task="task" :label="busy ? 'Writing the report' : ''" hide-done />
          <!-- The only v-html in the app: markdown from the server, sanitised by DOMPurify -->
          <article v-if="html" class="prose" v-html="html"></article>
          <div v-else-if="!busy" class="empty">
            <h3>No report yet</h3>
            <p>The language model writes it from the run's numbers and sample posts. It can only cite those numbers.</p>
          </div>
          <p class="caveat">Ranges cover chance only, not model error. The crowd is synthetic.</p>
        </section>

        <div v-if="summary" class="stack-lg data-col">
          <section class="panel stack" aria-labelledby="stance-head">
            <h3 id="stance-head">How people feel at the final poll</h3>
            <p class="muted small">Share of the crowd at each stance level{{ multi ? ', by variant' : '' }}.</p>
            <GroupedBars v-if="stance?.series.length" :categories="stance.categories" :series="stance.series" describe="Share of people at each stance level at the final poll" />
          </section>

          <section class="panel stack" aria-labelledby="seg-head">
            <div class="row">
              <h3 id="seg-head">Chance of yes by segment</h3>
              <span class="spacer"></span>
              <select v-model="dim" class="auto" aria-label="Segment by">
                <option v-for="d in dims" :key="d" :value="d">{{ DIM_LABEL[d] || d }}</option>
              </select>
            </div>
            <div class="table-scroll">
              <table class="data">
                <thead>
                  <tr>
                    <th>{{ DIM_LABEL[dim] || dim }}</th>
                    <th class="num">People</th>
                    <th v-for="v in variants" :key="v.id" class="num wrap-th">
                      <span class="th-key"><span v-if="multi" class="swatch" :style="{ background: seriesVar(v.index) }"></span>{{ multi ? v.label : 'Mean chance of yes' }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in segRows" :key="r.value">
                    <td class="seg-name">{{ kindLabel(r.value) }}</td>
                    <td class="num">{{ r.n }}</td>
                    <td v-for="v in variants" :key="v.id" class="num">{{ pct(r.by[v.id]) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="multi" class="muted small">Columns are the mean chance of yes under each variant.</p>
          </section>

        </div>
      </div>

      <section v-if="summary" class="panel stack" aria-labelledby="pts-head">
        <h3 id="pts-head">Which talking points spread</h3>
        <div class="table-scroll">
          <table class="data">
            <thead>
              <tr>
                <th>Point</th><th>Side</th>
                <th v-for="v in variants" :key="v.id" class="num wrap-th">{{ multi ? v.label : 'Uses' }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in pointRows" :key="p.id">
                <td class="pt-text"><span class="break">{{ p.text }}</span> <span class="muted small">{{ p.id }}</span></td>
                <td>{{ SIDE[p.side] || p.side }}</td>
                <td v-for="v in variants" :key="v.id" class="num" :title="p.by[v.id] ? `${p.by[v.id].posts} posts, ${p.by[v.id].comments} comments, ${p.by[v.id].quotes} quotes` : ''">
                  {{ p.by[v.id]?.total ?? 0 }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted small">Uses count posts, comments and quotes that make the point.</p>
      </section>
      <section v-if="focus" class="panel stack-lg" aria-labelledby="posts-head">
        <div class="row">
          <h2 id="posts-head">Top posts and people</h2>
          <span class="spacer"></span>
          <select v-if="multi" v-model="focusVariant" class="auto" aria-label="Variant">
            <option v-for="v in variants" :key="v.id" :value="v.id">{{ v.label }}</option>
          </select>
        </div>
        <div class="grid-side posts-grid">
          <div class="stack">
            <h3>Most engaging posts</h3>
            <p v-if="!focus.top_posts.length" class="muted">No posts in this variant.</p>
            <article v-for="p in focus.top_posts" :key="p.post_id" class="post">
              <p class="small"><strong>{{ p.author }}</strong></p>
              <p class="break content">{{ p.content }}</p>
              <p class="small muted tnum">{{ p.likes }} likes, {{ p.dislikes }} dislikes, {{ p.shares }} reshares, {{ p.comments.length }} comments</p>
              <ul v-if="p.comments.length" class="comments">
                <li v-for="(c, i) in p.comments" :key="i">
                  <p class="small"><strong>{{ c.author }}</strong> <span class="muted">{{ c.likes }} likes</span></p>
                  <p class="small break">{{ c.content }}</p>
                </li>
              </ul>
            </article>
          </div>
          <div class="stack">
            <h3>Most engaged people</h3>
            <div class="table-scroll">
              <table class="data">
                <thead><tr><th>Person</th><th class="num">Posts</th><th class="num">Engagement</th></tr></thead>
                <tbody>
                  <tr v-for="m in focus.most_engaged" :key="m.agent_id">
                    <td class="break">{{ m.name }}</td>
                    <td class="num">{{ int(m.posts) }}</td>
                    <td class="num">{{ int(m.engagement) }}</td>
                  </tr>
                  <tr v-if="!focus.most_engaged.length"><td colspan="3" class="muted">Nobody engaged.</td></tr>
                </tbody>
              </table>
            </div>
            <p class="muted small">Engagement counts the likes, reshares and comments a person's posts received.</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.report-grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 20px; align-items: start; }
@media (max-width: 1080px) { .report-grid { grid-template-columns: minmax(0, 1fr); } }
.data-col { min-width: 0; }
.auto { width: auto; max-width: 220px; }
.th-key { display: inline-flex; gap: 6px; align-items: center; }
.pt-text { min-width: 260px; }
.seg-name { min-width: 120px; overflow-wrap: break-word; }
.wrap-th { white-space: normal !important; min-width: 90px; max-width: 180px; }
.prose { max-width: 70ch; font-size: 15px; line-height: 1.65; overflow-wrap: anywhere; }
.prose :deep(h1), .prose :deep(h2), .prose :deep(h3) { margin: 1.4em 0 0.4em; }
.prose :deep(h1) { font-size: 22px; }
.prose :deep(h2) { font-size: 19px; }
.prose :deep(h3) { font-size: 16px; }
.prose :deep(> :first-child) { margin-top: 0; }
.prose :deep(p), .prose :deep(ul), .prose :deep(ol), .prose :deep(blockquote) { margin: 0 0 0.9em; }
.prose :deep(ul), .prose :deep(ol) { padding-left: 1.3em; }
.prose :deep(blockquote) { border-left: 3px solid var(--line-strong); padding-left: 12px; color: var(--ink-2); }
.prose :deep(code) { font-size: 0.9em; background: var(--panel-2); padding: 1px 4px; border-radius: 4px; }
.prose :deep(pre) { overflow-x: auto; background: var(--panel-2); padding: 10px; border-radius: 6px; }
.prose :deep(table) { border-collapse: collapse; display: block; overflow-x: auto; max-width: 100%; margin: 0 0 1em; font-size: 14px; }
.prose :deep(th), .prose :deep(td) { border-bottom: 1px solid var(--line); padding: 6px 10px; text-align: left; }
.prose :deep(img) { max-width: 100%; }
.posts-grid { grid-template-columns: minmax(0, 1fr) 360px; }
@media (max-width: 900px) { .posts-grid { grid-template-columns: minmax(0, 1fr); } }
.post { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px 14px; display: grid; gap: 6px; }
.post .content { white-space: pre-wrap; }
.comments { list-style: none; margin: 4px 0 0; padding: 0 0 0 14px; border-left: 2px solid var(--line); display: grid; gap: 8px; }
</style>
