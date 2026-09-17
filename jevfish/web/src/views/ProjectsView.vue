<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api.js'
import { STAGE_LABEL, when } from '../lib/format.js'

const router = useRouter()
const projects = ref([])
const loading = ref(true)
const loadError = ref('')

const name = ref('')
const question = ref('')
const seedText = ref('')
const files = ref([])
const fileInput = ref(null)
const creating = ref(false)
const createError = ref('')
const showForm = ref(false)

const ACCEPT = '.txt,.md,.markdown,.pdf'

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    projects.value = await api.projects()
    if (!projects.value.length) showForm.value = true
  } catch (e) {
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

function onFiles(ev) {
  const picked = Array.from(ev.target.files || [])
  const bad = picked.filter((f) => !/\.(txt|md|markdown|pdf)$/i.test(f.name))
  createError.value = bad.length ? `Only .txt, .md and .pdf files work. Skipped: ${bad.map((f) => f.name).join(', ')}` : ''
  files.value = picked.filter((f) => /\.(txt|md|markdown|pdf)$/i.test(f.name) && f.size <= 25 * 1024 * 1024)
  if (picked.some((f) => f.size > 25 * 1024 * 1024)) createError.value = 'Files must be 25 MB or smaller.'
}

function removeFile(i) {
  files.value = files.value.filter((_, j) => j !== i)
  if (!files.value.length && fileInput.value) fileInput.value.value = ''
}

async function create() {
  createError.value = ''
  if (!question.value.trim()) {
    createError.value = 'Write the prediction question first.'
    return
  }
  creating.value = true
  let project = null
  try {
    project = await api.createProject({
      name: name.value.trim() || question.value.trim().slice(0, 60),
      requirement: question.value.trim(),
      seed_text: seedText.value,
    })
    if (files.value.length) await api.uploadFiles(project.id, files.value)
    router.push({ name: 'graph', params: { pid: project.id } })
  } catch (e) {
    if (project) {
      router.push({ name: 'graph', params: { pid: project.id }, query: { uploadError: e.message } })
    } else createError.value = e.message
  } finally {
    creating.value = false
  }
}

async function remove(p) {
  if (!window.confirm(`Delete "${p.name}" and all its runs? This cannot be undone.`)) return
  try {
    await api.deleteProject(p.id)
    projects.value = projects.value.filter((x) => x.id !== p.id)
  } catch (e) {
    loadError.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div class="stack-lg">
    <section class="intro">
      <h1>What should the crowd predict?</h1>
      <p class="muted">
        Give JevFish a yes or no question and the documents behind it. It maps the people and facts, builds a synthetic crowd,
        lets them argue on a simulated social feed, and polls every person with Jev.
      </p>
    </section>

    <section class="panel" aria-labelledby="new-head">
      <div class="panel-head">
        <h2 id="new-head">New prediction</h2>
        <span class="spacer"></span>
        <button v-if="projects.length" class="btn small ghost" type="button" :aria-expanded="showForm" @click="showForm = !showForm">
          {{ showForm ? 'Hide form' : 'Show form' }}
        </button>
      </div>
      <form v-if="showForm" class="new-form" @submit.prevent="create">
        <label class="field">
          <span class="label">Prediction question</span>
          <input v-model="question" type="text" placeholder="Would a weekly cleaning upgrade make more renters book a viewing?" required />
          <span class="hint">Phrase it so each simulated person can answer yes or no.</span>
        </label>
        <label class="field">
          <span class="label">Project name <span class="muted">(optional)</span></span>
          <input v-model="name" type="text" placeholder="Cleaning upgrade" />
        </label>
        <label class="field">
          <span class="label">Seed text</span>
          <textarea v-model="seedText" rows="7" placeholder="Paste the brief, survey notes, articles or anything the crowd should know about."></textarea>
        </label>
        <div class="field">
          <span class="label">Or add files</span>
          <div class="row">
            <label class="btn small file-btn">
              Choose files
              <input ref="fileInput" class="sr-only" type="file" multiple :accept="ACCEPT" @change="onFiles" />
            </label>
            <span class="hint">.txt, .md or .pdf, up to 25 MB each</span>
          </div>
          <ul v-if="files.length" class="file-list">
            <li v-for="(f, i) in files" :key="f.name + i">
              <span class="break">{{ f.name }}</span>
              <span class="muted small">{{ Math.max(1, Math.round(f.size / 1024)) }} KB</span>
              <button class="btn small ghost" type="button" @click="removeFile(i)">Remove</button>
            </li>
          </ul>
        </div>
        <div v-if="createError" class="notice error" role="alert">{{ createError }}</div>
        <div class="row">
          <button class="btn primary" type="submit" :disabled="creating || !question.trim()">
            {{ creating ? 'Creating project' : 'Create project' }}
          </button>
          <span class="muted small">You can add more sources on the next screen.</span>
        </div>
      </form>
    </section>

    <section aria-labelledby="list-head" class="stack">
      <div class="row">
        <h2 id="list-head">Projects</h2>
        <span class="muted small" v-if="projects.length">{{ projects.length }} total, newest first</span>
      </div>
      <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>
      <p v-if="loading" class="muted">Loading projects</p>
      <div v-else-if="!projects.length && !loadError" class="panel empty">
        <h3>No projects yet</h3>
        <p>Start with a question and some seed text above.</p>
      </div>
      <ul v-else class="project-list">
        <li v-for="p in projects" :key="p.id" class="project">
          <RouterLink :to="{ name: 'graph', params: { pid: p.id } }" class="project-link">
            <span class="project-name break">{{ p.name || 'Untitled' }}</span>
            <span class="project-q break">{{ p.requirement }}</span>
          </RouterLink>
          <div class="project-meta">
            <span class="pill" :class="{ good: p.stage === 'prepared', accent: p.stage === 'graph' }">{{ STAGE_LABEL[p.stage] || p.stage }}</span>
            <span class="muted small nowrap">{{ p.sources.length }} {{ p.sources.length === 1 ? 'source' : 'sources' }}</span>
            <span class="muted small nowrap">Updated {{ when(p.updated_at) }}</span>
            <button class="btn small ghost danger" type="button" @click="remove(p)" :aria-label="`Delete ${p.name}`">Delete</button>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.intro { max-width: 720px; }
.intro h1 { font-size: 32px; letter-spacing: -0.02em; margin-bottom: 8px; }
.intro p { font-size: 16px; }
@media (max-width: 600px) { .intro h1 { font-size: 26px; } }
.new-form { display: grid; gap: 16px; max-width: 760px; }
.file-btn { position: relative; }
.file-list { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 4px; }
.file-list li { display: flex; gap: 12px; align-items: center; font-size: 14px; }
.project-list { list-style: none; margin: 0; padding: 0; background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); }
.project { display: flex; gap: 16px; align-items: center; padding: 14px 20px; flex-wrap: wrap; }
.project + .project { border-top: 1px solid var(--line); }
.project-link { flex: 1 1 360px; min-width: 0; text-decoration: none; color: inherit; display: grid; gap: 2px; }
.project-link:hover .project-name { text-decoration: underline; }
.project-name { font-weight: 600; font-size: 16px; }
.project-q { color: var(--muted); font-size: 14px; }
.project-meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
</style>
