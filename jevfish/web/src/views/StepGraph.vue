<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api.js'
import { debounce, int, when } from '../lib/format.js'
import { seriesVar } from '../lib/palette.js'
import { useWorkspace } from '../lib/workspace.js'
import ForceGraph from '../components/ForceGraph.vue'
import TaskStatus from '../components/TaskStatus.vue'

const ws = useWorkspace()
const route = useRoute()
const router = useRouter()
const pid = ws.pid

const ov = computed(() => ws.overview.value)
const task = computed(() => ws.tasks.graph)
const busy = computed(() => task.value && (task.value.status === 'queued' || task.value.status === 'running'))

// Sources
const pasteText = ref('')
const pasteName = ref('')
const addError = ref(route.query.uploadError ? `The project was created but a file failed: ${route.query.uploadError}` : '')
const adding = ref(false)
const fileInput = ref(null)
if (route.query.uploadError) router.replace({ query: { ...route.query, uploadError: undefined } })

async function addText() {
  addError.value = ''
  adding.value = true
  try {
    await api.addSeed(pid.value, pasteText.value, pasteName.value.trim() || undefined)
    pasteText.value = ''
    pasteName.value = ''
    await ws.refresh()
  } catch (e) {
    addError.value = e.message
  } finally {
    adding.value = false
  }
}
async function addFiles(ev) {
  const files = Array.from(ev.target.files || [])
  if (!files.length) return
  addError.value = ''
  const bad = files.filter((f) => !/\.(txt|md|markdown|pdf)$/i.test(f.name))
  if (bad.length) {
    addError.value = `Only .txt, .md and .pdf files work. Skipped: ${bad.map((f) => f.name).join(', ')}`
  }
  const good = files.filter((f) => !bad.includes(f))
  if (good.length) {
    adding.value = true
    try {
      await api.uploadFiles(pid.value, good)
      await ws.refresh()
    } catch (e) {
      addError.value = e.message
    } finally {
      adding.value = false
    }
  }
  if (fileInput.value) fileInput.value.value = ''
}

// Build
const buildError = ref('')
async function build() {
  buildError.value = ''
  try {
    const t = await api.buildGraph(pid.value)
    const final = await ws.track(t)
    if (final.status === 'done') await loadGraph()
  } catch (e) {
    buildError.value = e.message
  }
}

// Graph data
const graph = ref(null)
const graphError = ref('')
async function loadGraph() {
  graphError.value = ''
  try {
    graph.value = await api.graph(pid.value)
  } catch (e) {
    if (e.status !== 400) graphError.value = e.message
    graph.value = null
  }
}
watch(() => ov.value?.graph_stats && ov.value.updated_at, (v, old) => {
  if (ov.value?.graph_stats && (!graph.value || v !== old)) loadGraph()
}, { immediate: true })

const types = computed(() => {
  if (!graph.value) return []
  const fromOntology = (graph.value.ontology?.entity_types || []).map((t) => t.name)
  const seen = new Set(fromOntology)
  const extra = [...new Set(graph.value.nodes.map((n) => n.type))].filter((t) => !seen.has(t))
  const all = [...fromOntology, ...extra]
  const counts = graph.value.stats?.types || {}
  const used = all.filter((t) => counts[t] || graph.value.nodes.some((n) => n.type === t))
  return used
})
const legendTypes = computed(() => types.value.slice(0, 8))
const otherCount = computed(() => types.value.length - 8)

const byId = computed(() => Object.fromEntries((graph.value?.nodes || []).map((n) => [n.id, n])))
const selectedId = ref('')
const highlightEdge = ref('')
const selected = computed(() => byId.value[selectedId.value] || null)
const selectedEdges = computed(() => {
  if (!selected.value) return []
  return graph.value.edges.filter((e) => e.source === selectedId.value || e.target === selectedId.value)
})
function select(id) {
  selectedId.value = id
  if (!id) highlightEdge.value = ''
}

// Search
const q = ref('')
const results = ref([])
const searching = ref(false)
const searchError = ref('')
const runSearch = debounce(async (term) => {
  if (!term.trim()) {
    results.value = []
    return
  }
  searching.value = true
  searchError.value = ''
  try {
    results.value = await api.searchGraph(pid.value, term, 10)
  } catch (e) {
    searchError.value = e.message
  } finally {
    searching.value = false
  }
}, 300)
watch(q, (v) => runSearch(v))
function pick(r) {
  if (r.kind === 'node') {
    selectedId.value = r.item.id
    highlightEdge.value = ''
  } else {
    selectedId.value = r.item.source
    highlightEdge.value = r.item.id
  }
}
function edgeText(e) {
  const s = byId.value[e.source]?.name || e.source
  const t = byId.value[e.target]?.name || e.target
  return `${s} ${e.type.toLowerCase().replace(/_/g, ' ')} ${t}`
}

const view = ref('graph')
const tableSort = computed(() => [...(graph.value?.nodes || [])].sort((a, b) => b.degree - a.degree || a.name.localeCompare(b.name)))
function typeColor(t) {
  const i = types.value.indexOf(t)
  return i >= 0 && i < 8 ? seriesVar(i) : 'var(--s-other)'
}
</script>

<template>
  <div class="stack-lg">
    <div class="grid-2">
      <section class="panel" aria-labelledby="src-head">
        <div class="panel-head">
          <h2 id="src-head">Seed sources</h2>
          <p v-if="ov">{{ int(ov.seed_chars) }} characters in total</p>
        </div>
        <ul v-if="ov?.sources.length" class="sources">
          <li v-for="(s, i) in ov.sources" :key="i">
            <span class="break">{{ s.name }}</span>
            <span class="muted small tnum nowrap">{{ int(s.chars) }} chars</span>
            <span class="muted small nowrap">{{ when(s.added_at) }}</span>
          </li>
        </ul>
        <p v-else class="muted">No sources yet. Paste some text or add a file to start.</p>

        <details class="add" :open="!ov?.sources.length">
          <summary>Add more sources</summary>
          <form class="stack" @submit.prevent="addText">
            <label class="field">
              <span class="label">Paste text</span>
              <textarea v-model="pasteText" rows="5" placeholder="Articles, notes, survey answers"></textarea>
            </label>
            <label class="field">
              <span class="label">Source name <span class="muted">(optional)</span></span>
              <input v-model="pasteName" type="text" placeholder="Tenant chat notes" />
            </label>
            <div class="row">
              <button class="btn" type="submit" :disabled="adding || !pasteText.trim()">Add text</button>
              <label class="btn" :class="{ disabled: adding }">
                Add files
                <input ref="fileInput" class="sr-only" type="file" multiple accept=".txt,.md,.markdown,.pdf" :disabled="adding" @change="addFiles" />
              </label>
              <span class="muted small">.txt, .md or .pdf</span>
            </div>
          </form>
        </details>
        <div v-if="addError" class="notice error" role="alert">{{ addError }}</div>
      </section>

      <section class="panel stack" aria-labelledby="build-head">
        <div class="panel-head">
          <h2 id="build-head">Knowledge graph</h2>
          <p>The language model reads the sources and maps the people, groups and facts in them.</p>
        </div>
        <div class="row">
          <button class="btn primary" type="button" :disabled="busy || !ov?.seed_chars" @click="build">
            {{ ov?.graph_stats ? 'Rebuild graph' : 'Build graph' }}
          </button>
          <span v-if="ov?.graph_stats && ov?.stage === 'prepared'" class="muted small">Rebuilding means you should prepare the crowd again.</span>
          <span v-if="!ov?.seed_chars" class="muted small">Add a source first.</span>
        </div>
        <div v-if="buildError" class="notice error" role="alert">{{ buildError }}</div>
        <TaskStatus :task="task" :label="busy ? 'Building the graph' : ''" />

        <dl v-if="ov?.graph_stats" class="stats">
          <div><dt>Entities</dt><dd>{{ int(ov.graph_stats.nodes) }}</dd></div>
          <div><dt>Relations</dt><dd>{{ int(ov.graph_stats.edges) }}</dd></div>
          <div><dt>Chunks read</dt><dd>{{ int(ov.graph_stats.chunks) }}</dd></div>
          <div><dt>Chunks failed</dt><dd :class="{ bad: ov.graph_stats.failed_chunks }">{{ int(ov.graph_stats.failed_chunks) }}</dd></div>
        </dl>
        <div v-if="ov?.graph_stats" class="type-counts">
          <span v-for="(c, t) in ov.graph_stats.types" :key="t" class="pill">
            <span class="swatch" :style="{ background: typeColor(t) }"></span>{{ t }} <span class="tnum">{{ c }}</span>
          </span>
        </div>
        <div v-if="graph?.errors?.length" class="notice warn">
          <p><strong>{{ graph.errors.length }} extraction {{ graph.errors.length === 1 ? 'problem' : 'problems' }}</strong></p>
          <p v-for="(e, i) in graph.errors.slice(0, 5)" :key="i" class="small break">{{ e }}</p>
        </div>
      </section>
    </div>

    <div v-if="graphError" class="notice error" role="alert">{{ graphError }}</div>

    <section v-if="graph" class="panel" aria-labelledby="map-head">
      <div class="panel-head">
        <h2 id="map-head">Map</h2>
        <span class="spacer"></span>
        <div class="seg" role="group" aria-label="View">
          <button type="button" :aria-pressed="view === 'graph'" @click="view = 'graph'">Graph</button>
          <button type="button" :aria-pressed="view === 'table'" @click="view = 'table'">Table</button>
        </div>
      </div>

      <div class="legend graph-legend" aria-label="Entity types">
        <span v-for="(t, i) in legendTypes" :key="t"><span class="swatch" :style="{ background: seriesVar(i), borderRadius: '50%' }"></span>{{ t }}</span>
        <span v-if="otherCount > 0"><span class="swatch" style="background: var(--s-other); border-radius: 50%"></span>Other ({{ otherCount }} types)</span>
        <span class="muted">Dot size shows how connected an entity is.</span>
      </div>

      <div class="grid-side map-grid">
        <div class="map-main">
          <template v-if="!graph.nodes.length">
            <div class="empty"><h3>The graph is empty</h3><p>Add richer sources and rebuild.</p></div>
          </template>
          <ForceGraph
            v-else-if="view === 'graph'"
            :nodes="graph.nodes"
            :edges="graph.edges"
            :types="types"
            :selected-id="selectedId"
            :highlight-edge="highlightEdge"
            @select="select"
          />
          <div v-else class="table-scroll node-table">
            <table class="data">
              <thead><tr><th>Entity</th><th>Type</th><th class="num">Connections</th><th class="num">Mentions</th><th>Summary</th></tr></thead>
              <tbody>
                <tr v-for="n in tableSort" :key="n.id" :class="{ picked: n.id === selectedId }">
                  <td><button class="linkish" type="button" @click="select(n.id)">{{ n.name }}</button></td>
                  <td class="nowrap"><span class="swatch" :style="{ background: typeColor(n.type) }"></span> {{ n.type }}</td>
                  <td class="num">{{ n.degree }}</td>
                  <td class="num">{{ n.mentions }}</td>
                  <td class="summary">{{ n.summary }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <aside class="side stack">
          <div class="field">
            <label class="label" for="graph-search">Search the graph</label>
            <input id="graph-search" v-model="q" type="search" placeholder="cleaning, students, rent" autocomplete="off" />
          </div>
          <div v-if="searchError" class="notice error">{{ searchError }}</div>
          <ul v-if="q.trim() && results.length" class="results">
            <li v-for="(r, i) in results" :key="i">
              <button type="button" class="result" @click="pick(r)">
                <template v-if="r.kind === 'node'">
                  <span class="r-title"><span class="swatch" :style="{ background: typeColor(r.item.type) }"></span>{{ r.item.name }}</span>
                  <span class="muted small">{{ r.item.type }}</span>
                </template>
                <template v-else>
                  <span class="r-title">{{ edgeText(r.item) }}</span>
                  <span class="muted small break">{{ r.item.fact }}</span>
                </template>
              </button>
            </li>
          </ul>
          <p v-else-if="q.trim() && !searching" class="muted small">No matches for that search.</p>

          <div v-if="selected" class="detail">
            <div class="row">
              <span class="swatch" :style="{ background: typeColor(selected.type), borderRadius: '50%' }"></span>
              <h3 class="break">{{ selected.name }}</h3>
              <span class="spacer"></span>
              <button class="btn small ghost" type="button" @click="select('')" aria-label="Close details">Close</button>
            </div>
            <p class="muted small">{{ selected.type }}, {{ selected.degree }} connections, mentioned {{ selected.mentions }} {{ selected.mentions === 1 ? 'time' : 'times' }}</p>
            <p class="break">{{ selected.summary }}</p>
            <h4>Facts</h4>
            <ul v-if="selectedEdges.length" class="facts">
              <li v-for="e in selectedEdges" :key="e.id" :class="{ hit: e.id === highlightEdge }">
                <p class="small">
                  <button v-if="e.source !== selectedId" class="linkish" type="button" @click="select(e.source)">{{ byId[e.source]?.name }}</button>
                  <strong v-else>{{ selected.name }}</strong>
                  <span class="muted rel">{{ e.type.toLowerCase().replace(/_/g, ' ') }}</span>
                  <button v-if="e.target !== selectedId" class="linkish" type="button" @click="select(e.target)">{{ byId[e.target]?.name }}</button>
                  <strong v-else>{{ selected.name }}</strong>
                </p>
                <p class="small muted break">{{ e.fact }}</p>
              </li>
            </ul>
            <p v-else class="muted small">No relations recorded.</p>
          </div>
          <p v-else class="muted small">Click a dot or a search result to see its facts.</p>
        </aside>
      </div>
    </section>
  </div>
</template>

<style scoped>
.sources { list-style: none; margin: 0 0 16px; padding: 0; }
.sources li { display: flex; gap: 12px; align-items: baseline; padding: 6px 0; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.sources li > :first-child { flex: 1 1 160px; min-width: 0; }
.add summary { cursor: pointer; font-weight: 600; font-size: 14px; color: var(--accent-text); margin-bottom: 12px; }
.add[open] summary { margin-bottom: 12px; }
label.btn.disabled { opacity: 0.5; }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0; }
@media (max-width: 500px) { .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.stats div { background: var(--panel-2); border-radius: var(--radius-sm); padding: 10px 12px; }
.stats dt { font-size: 13px; color: var(--muted); }
.stats dd { margin: 0; font-size: 24px; font-weight: 600; }
.stats dd.bad { color: var(--bad); }
.type-counts { display: flex; gap: 6px; flex-wrap: wrap; }
.graph-legend { margin-bottom: 12px; }
.map-grid { grid-template-columns: minmax(0, 1fr) 320px; }
@media (max-width: 900px) { .map-grid { grid-template-columns: minmax(0, 1fr); } }
.map-main { min-width: 0; }
.node-table { max-height: 520px; overflow-y: auto; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.node-table .summary { min-width: 240px; color: var(--ink-2); }
tr.picked td { background: var(--accent-soft) !important; }
.linkish { font: inherit; background: none; border: 0; padding: 0; color: var(--accent-text); cursor: pointer; text-align: left; text-decoration: underline; text-underline-offset: 2px; }
.results { list-style: none; margin: 0; padding: 0; border: 1px solid var(--line); border-radius: var(--radius-sm); max-height: 260px; overflow-y: auto; }
.results li + li { border-top: 1px solid var(--line); }
.result { display: grid; gap: 2px; width: 100%; text-align: left; font: inherit; background: none; border: 0; padding: 8px 10px; cursor: pointer; color: var(--ink); }
.result:hover { background: var(--panel-2); }
.r-title { display: flex; gap: 6px; align-items: center; font-size: 14px; font-weight: 600; }
.detail { border-top: 1px solid var(--line); padding-top: 12px; display: grid; gap: 8px; }
.facts { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; max-height: 320px; overflow-y: auto; }
.facts li { padding: 8px 10px; border-radius: var(--radius-sm); background: var(--panel-2); }
.rel { margin: 0 0.35em; }
.facts li.hit { box-shadow: inset 0 0 0 2px var(--ink-2); }
</style>
