<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  frame: { type: Object, required: true },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
  savedAt: { type: Number, default: 0 },
})
const emit = defineEmits(['save'])

let uid = 0
const draft = ref(null)
const localError = ref('')

function load(f) {
  draft.value = {
    points: f.talking_points.map((p) => ({ key: ++uid, id: p.id, text: p.text, side: p.side })),
    variants: f.variants.map((v) => ({
      key: ++uid,
      id: v.id,
      label: v.label,
      rows: Object.entries(v.subject || {}).map(([k, val]) => ({ key: ++uid, k, v: String(val) })),
    })),
  }
  localError.value = ''
}
watch(() => props.frame, load, { immediate: true })

const snapshot = computed(() => JSON.stringify(toFrame()))
const baseline = ref('')
watch(() => props.frame, () => (baseline.value = snapshot.value), { immediate: true, flush: 'post' })
const dirty = computed(() => baseline.value && snapshot.value !== baseline.value)

function toFrame() {
  if (!draft.value) return props.frame
  return {
    ...props.frame,
    talking_points: draft.value.points.map((p) => ({ id: p.id || '', text: p.text, side: p.side })),
    variants: draft.value.variants.map((v) => ({
      id: v.id,
      label: v.label,
      subject: Object.fromEntries(v.rows.filter((r) => r.k.trim()).map((r) => [r.k.trim(), r.v])),
    })),
  }
}

function addPoint() {
  draft.value.points.push({ key: ++uid, id: '', text: '', side: 'neutral' })
}
function removePoint(i) {
  draft.value.points.splice(i, 1)
}
function addVariant() {
  const ids = new Set(draft.value.variants.map((v) => v.id))
  let n = draft.value.variants.length + 1
  while (ids.has(`V${n}`)) n++
  const firstKey = Object.keys(props.frame.subject || {})[0] || ''
  draft.value.variants.push({ key: ++uid, id: `V${n}`, label: '', rows: [{ key: ++uid, k: firstKey, v: '' }] })
}
function removeVariant(i) {
  draft.value.variants.splice(i, 1)
}
function addRow(v) {
  v.rows.push({ key: ++uid, k: '', v: '' })
}

function validate() {
  const pts = draft.value.points.filter((p) => p.text.trim())
  if (!pts.length) return 'Keep at least one talking point with text.'
  if (!draft.value.variants.length) return 'Keep at least one variant.'
  const seen = new Set()
  for (const v of draft.value.variants) {
    const id = v.id.replace(/[^A-Za-z0-9_-]/g, '')
    if (!id) return 'Every variant needs a short id made of letters, numbers, _ or -.'
    if (id.length > 12) return `Variant id "${v.id}" is longer than 12 characters.`
    if (id !== v.id) return `Variant id "${v.id}" can only use letters, numbers, _ or -.`
    if (seen.has(id)) return `Two variants share the id "${id}".`
    seen.add(id)
    if (!v.label.trim()) return `Give variant ${id} a label.`
  }
  return ''
}

function save() {
  localError.value = validate()
  if (localError.value) return
  emit('save', toFrame())
}
function discard() {
  load(props.frame)
}

const subjectKeys = computed(() => Object.keys(props.frame.subject || {}))
const SIDES = [
  { v: 'pro', t: 'For' },
  { v: 'con', t: 'Against' },
  { v: 'neutral', t: 'Neutral' },
]
const recentlySaved = computed(() => props.savedAt && Date.now() - props.savedAt < 6000 && !dirty.value)
</script>

<template>
  <div v-if="draft" class="fe stack-lg">
    <div class="read grid-2">
      <div class="stack">
        <h3>Question</h3>
        <p class="break">{{ frame.question }}</p>
        <h3>Outcome question</h3>
        <p class="break">{{ frame.outcome.instructions }}</p>
        <dl v-if="frame.outcome.criteria" class="kv small">
          <dt>Counts as yes</dt><dd class="break">{{ frame.outcome.criteria.true }}</dd>
          <dt>Counts as no</dt><dd class="break">{{ frame.outcome.criteria.false }}</dd>
        </dl>
      </div>
      <div class="stack">
        <h3>Subject facts</h3>
        <dl v-if="subjectKeys.length" class="kv small">
          <template v-for="k in subjectKeys" :key="k"><dt class="break">{{ k }}</dt><dd class="break">{{ frame.subject[k] }}</dd></template>
        </dl>
        <p v-else class="muted small">None</p>
        <h3>Stance levels</h3>
        <ol class="levels small">
          <li v-for="(l, i) in frame.stance.levels" :key="i">{{ l }}</li>
        </ol>
      </div>
    </div>

    <div class="stack">
      <h3>Opening posts</h3>
      <ul v-if="frame.opening_posts.length" class="openings">
        <li v-for="(o, i) in frame.opening_posts" :key="i">
          <p class="small"><strong>{{ o.author || 'Unnamed' }}</strong> <span v-if="o.talking_point" class="pill">{{ o.talking_point }}</span></p>
          <p class="break">{{ o.text }}</p>
        </li>
      </ul>
      <p v-else class="muted small">None. The feed starts empty.</p>
    </div>

    <form class="stack-lg" @submit.prevent="save">
      <fieldset class="stack">
        <legend><h3>Talking points</h3></legend>
        <p class="muted small">The arguments people can pick up. Posts and comments are tagged with the point they make.</p>
        <div class="table-scroll">
          <table class="data points">
            <thead><tr><th>Id</th><th>Point</th><th>Side</th><th><span class="sr-only">Remove</span></th></tr></thead>
            <tbody>
              <tr v-for="(p, i) in draft.points" :key="p.key">
                <td class="nowrap"><span class="pill pid" :title="p.id">{{ p.id || 'new' }}</span></td>
                <td class="grow"><input v-model="p.text" type="text" :aria-label="`Talking point ${i + 1}`" /></td>
                <td>
                  <select v-model="p.side" :aria-label="`Side of point ${i + 1}`">
                    <option v-for="s in SIDES" :key="s.v" :value="s.v">{{ s.t }}</option>
                  </select>
                </td>
                <td><button class="btn small ghost" type="button" @click="removePoint(i)" :aria-label="`Remove point ${i + 1}`">Remove</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div><button class="btn small" type="button" @click="addPoint">Add talking point</button></div>
      </fieldset>

      <fieldset class="stack">
        <legend><h3>Variants</h3></legend>
        <p class="muted small">Each variant runs against the same crowd with some subject facts changed. Compare an offer against the current one.</p>
        <datalist id="subject-keys"><option v-for="k in subjectKeys" :key="k" :value="k" /></datalist>
        <div class="variants">
          <div v-for="(v, i) in draft.variants" :key="v.key" class="variant">
            <div class="v-head">
              <label class="field v-id"><span class="label">Id</span><input v-model="v.id" type="text" maxlength="12" /></label>
              <label class="field v-label"><span class="label">Label</span><input v-model="v.label" type="text" placeholder="Weekly cleaning at S$100 more" /></label>
              <button class="btn small ghost danger" type="button" :disabled="draft.variants.length < 2" @click="removeVariant(i)">Remove variant</button>
            </div>
            <div class="stack">
              <span class="label small">Subject overrides</span>
              <p v-if="!v.rows.length" class="muted small">No overrides. This variant uses the subject facts as written.</p>
              <div v-for="(r, j) in v.rows" :key="r.key" class="kv-row">
                <input v-model="r.k" type="text" list="subject-keys" placeholder="Fact name" :aria-label="`Fact name ${j + 1}`" />
                <input v-model="r.v" type="text" placeholder="Value for this variant" :aria-label="`Fact value ${j + 1}`" />
                <button class="btn small ghost" type="button" @click="v.rows.splice(j, 1)" :aria-label="`Remove override ${j + 1}`">Remove</button>
              </div>
              <div><button class="btn small" type="button" @click="addRow(v)">Add override</button></div>
            </div>
          </div>
        </div>
        <div><button class="btn small" type="button" :disabled="draft.variants.length >= 8" @click="addVariant">Add variant</button></div>
      </fieldset>

      <div v-if="localError || error" class="notice error" role="alert">{{ localError || error }}</div>
      <div class="row savebar">
        <button class="btn primary" type="submit" :disabled="saving || !dirty">{{ saving ? 'Saving' : 'Save frame' }}</button>
        <button class="btn" type="button" :disabled="saving || !dirty" @click="discard">Discard changes</button>
        <span v-if="dirty" class="muted small">Unsaved changes</span>
        <span v-else-if="recentlySaved" class="pill good" role="status">Saved</span>
      </div>
    </form>
  </div>
</template>

<style scoped>
.kv { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 4px 12px; margin: 0; }
.kv dt { color: var(--muted); }
.kv dd { margin: 0; }
.levels { margin: 0; padding-left: 20px; }
.openings { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.openings li { background: var(--panel-2); border-radius: var(--radius-sm); padding: 10px 12px; }
.points td { vertical-align: middle; }
.pid { max-width: 120px; overflow: hidden; text-overflow: ellipsis; display: inline-block; line-height: 1.2; }
.points td.grow { width: 100%; min-width: 260px; }
.points select { width: auto; }
.variants { display: grid; gap: 12px; }
.variant { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 14px; display: grid; gap: 12px; }
.v-head { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.v-id { width: 110px; }
.v-label { flex: 1 1 220px; }
.kv-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto; gap: 8px; align-items: center; }
@media (max-width: 520px) { .kv-row { grid-template-columns: minmax(0, 1fr) auto; } .kv-row input:nth-child(2) { grid-column: 1; grid-row: 2; } }
.label { font-weight: 600; color: var(--ink-2); }
.savebar { position: sticky; bottom: 0; background: var(--panel); padding: 12px 0; border-top: 1px solid var(--line); }
</style>
