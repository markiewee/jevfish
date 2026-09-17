<script setup>
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { api } from '../lib/api.js'

const props = defineProps({
  pid: { type: String, required: true },
  runId: { type: String, required: true },
  active: { type: Boolean, default: false },
  variants: { type: Array, default: () => [] }, // [{id, label}]
  points: { type: Object, default: () => ({}) }, // id -> text
})

const items = shallowRef([])
const error = ref('')
const variant = ref('all')
const showIdle = ref(false)
const shown = ref(120)
let since = 0
let timer = null
let pulling = false
let gen = 0

async function pull() {
  if (pulling) return
  pulling = true
  const my = gen
  try {
    for (;;) {
      const batch = await api.actions(props.pid, props.runId, since, 500)
      if (my !== gen) return
      if (batch.length) {
        since += batch.length
        items.value = items.value.concat(batch)
      }
      if (batch.length < 500) break
    }
    error.value = ''
  } catch (e) {
    if (my === gen) error.value = e.message
  } finally {
    if (my === gen) pulling = false
  }
}

function reset() {
  gen++
  pulling = false
  since = 0
  items.value = []
  shown.value = 120
  pull()
}

watch(() => props.runId, reset, { immediate: true })
watch(
  () => props.active,
  (on, was) => {
    clearInterval(timer)
    if (on) timer = setInterval(pull, 1500)
    else if (was) setTimeout(pull, 300)
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  clearInterval(timer)
  gen++
})

const key = (v, author, text) => `${v}${author}${String(text || '').slice(0, 200)}`

// Tally reactions onto the posts they point at
const tallies = computed(() => {
  const t = {}
  for (const a of items.value) {
    if (!a.ok) continue
    if (a.action === 'create_post' || a.action === 'quote_post') {
      t[key(a.variant, a.agent_name, a.content)] ||= { likes: 0, dislikes: 0, reshares: 0, comments: 0 }
    }
  }
  for (const a of items.value) {
    if (!a.ok || !a.target_author) continue
    const k = key(a.variant, a.target_author, a.target_excerpt)
    const row = t[k]
    if (!row) continue
    if (a.action === 'like_post') row.likes++
    else if (a.action === 'dislike_post') row.dislikes++
    else if (a.action === 'repost' || a.action === 'quote_post') row.reshares++
    else if (a.action === 'create_comment') row.comments++
  }
  return t
})

const counts = computed(() => {
  const c = { posts: 0, comments: 0, reactions: 0, idle: 0 }
  for (const a of items.value) {
    if (variant.value !== 'all' && a.variant !== variant.value) continue
    if (a.action === 'create_post' || a.action === 'quote_post') c.posts++
    else if (a.action === 'create_comment') c.comments++
    else if (a.action === 'do_nothing') c.idle++
    else c.reactions++
  }
  return c
})

const visible = computed(() => {
  const out = []
  for (let i = items.value.length - 1; i >= 0; i--) {
    const a = items.value[i]
    if (variant.value !== 'all' && a.variant !== variant.value) continue
    if (!showIdle.value && a.action === 'do_nothing') continue
    out.push({ a, i })
  }
  return out
})

const multi = computed(() => props.variants.length > 1)
const vLabel = computed(() => Object.fromEntries(props.variants.map((v) => [v.id, v.label])))
function kind(a) {
  if (a.action === 'create_post' || a.action === 'quote_post') return 'post'
  if (a.action === 'create_comment') return 'comment'
  return 'reaction'
}
function name(n) {
  return String(n || '').replace(/\s+\([^)]*\)$/, '')
}
function group(n) {
  const m = String(n || '').match(/\(([^)]*)\)$/)
  return m ? m[1] : ''
}
function excerpt(s, n = 90) {
  s = String(s || '').replace(/\s+/g, ' ').trim()
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}
function reactionText(a) {
  const target = a.target_author ? name(a.target_author) : 'someone'
  switch (a.action) {
    case 'like_post': return `liked a post by ${target}`
    case 'dislike_post': return `disliked a post by ${target}`
    case 'repost': return `reshared a post by ${target}`
    case 'like_comment': return `liked a comment by ${target}`
    case 'follow': return `followed ${target}`
    case 'do_nothing': return 'read the feed and moved on'
    default: return a.action.replace(/_/g, ' ')
  }
}
function when(a) {
  return a.round === 0 ? 'Opening' : `Round ${a.round}`
}
</script>

<template>
  <div class="feed">
    <div class="feed-bar">
      <p class="small muted tnum">
        {{ counts.posts }} posts, {{ counts.comments }} comments, {{ counts.reactions }} reactions<template v-if="counts.idle">, {{ counts.idle }} idle turns</template>
      </p>
      <span class="spacer"></span>
      <select v-if="multi" v-model="variant" class="vsel" aria-label="Variant shown in the feed">
        <option value="all">All variants</option>
        <option v-for="v in variants" :key="v.id" :value="v.id">{{ v.label }}</option>
      </select>
      <label class="check small"><input v-model="showIdle" type="checkbox" /> Show idle turns</label>
      <span v-if="active" class="live small"><span class="pulse" aria-hidden="true"></span>Live</span>
    </div>
    <div v-if="error" class="notice error">{{ error }}</div>
    <p v-if="!visible.length" class="muted small empty-feed">{{ active ? 'Waiting for the first actions.' : 'No actions recorded.' }}</p>
    <ol class="items" aria-live="off">
      <li v-for="{ a, i } in visible.slice(0, shown)" :key="i" :class="['item', kind(a), { failed: !a.ok }]">
        <template v-if="kind(a) !== 'reaction'">
          <div class="meta">
            <strong class="break">{{ name(a.agent_name) }}</strong>
            <span v-if="group(a.agent_name)" class="muted small">{{ group(a.agent_name) }}</span>
            <span v-if="a.opening" class="pill accent">Opening post</span>
            <span v-if="a.injection" class="pill warn">News</span>
            <span v-if="a.action === 'quote_post'" class="pill">Quote</span>
            <span class="spacer"></span>
            <span v-if="multi" class="muted small">{{ vLabel[a.variant] || a.variant }}</span>
            <span class="muted small nowrap">{{ when(a) }}</span>
          </div>
          <p v-if="kind(a) === 'comment'" class="reply small muted break">
            Replying to {{ name(a.target_author) }}: {{ excerpt(a.target_excerpt) }}
          </p>
          <p class="content break">{{ a.content }}</p>
          <div class="foot small">
            <span v-if="a.point" class="pill" :title="points[a.point] || ''">{{ a.point }}<template v-if="points[a.point]">: {{ excerpt(points[a.point], 40) }}</template></span>
            <template v-if="kind(a) === 'post' && tallies[key(a.variant, a.agent_name, a.content)]">
              <span class="muted tnum">{{ tallies[key(a.variant, a.agent_name, a.content)].likes }} likes</span>
              <span v-if="tallies[key(a.variant, a.agent_name, a.content)].dislikes" class="muted tnum">{{ tallies[key(a.variant, a.agent_name, a.content)].dislikes }} dislikes</span>
              <span class="muted tnum">{{ tallies[key(a.variant, a.agent_name, a.content)].reshares }} reshares</span>
              <span class="muted tnum">{{ tallies[key(a.variant, a.agent_name, a.content)].comments }} comments</span>
            </template>
            <span v-if="!a.ok" class="pill bad">Failed: {{ excerpt(a.error, 60) }}</span>
          </div>
        </template>
        <template v-else>
          <p class="line small break">
            <span class="who">{{ name(a.agent_name) }}</span> {{ reactionText(a) }}<template v-if="a.target_excerpt && a.action !== 'follow'"><span class="muted">: {{ excerpt(a.target_excerpt, 70) }}</span></template>
            <span v-if="!a.ok" class="pill bad">Failed</span>
            <span class="muted when nowrap">{{ multi ? (vLabel[a.variant] || a.variant) + ', ' : '' }}{{ when(a) }}</span>
          </p>
        </template>
      </li>
    </ol>
    <div v-if="visible.length > shown" class="row"><button class="btn small" type="button" @click="shown += 200">Show older actions</button></div>
  </div>
</template>

<style scoped>
.feed { display: grid; gap: 10px; }
.feed-bar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.vsel { width: auto; max-width: 220px; }
.live { display: inline-flex; gap: 6px; align-items: center; font-weight: 600; color: var(--good); }
.pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--good); animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.3; } }
.items { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; max-height: 640px; overflow-y: auto; overscroll-behavior: contain; padding-right: 4px; }
.item.post, .item.comment { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 10px 12px; background: var(--panel); display: grid; gap: 6px; }
.item.comment { margin-left: 24px; background: var(--panel-2); }
@media (max-width: 500px) { .item.comment { margin-left: 10px; } }
.item.failed { border-style: dashed; }
.meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.content { white-space: pre-wrap; }
.reply { border-left: 2px solid var(--line-strong); padding-left: 8px; }
.foot { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.foot .pill { max-width: 100%; white-space: normal; line-height: 1.3; }
.item.reaction { padding: 2px 12px; }
.line { color: var(--ink-2); }
.line .who { font-weight: 600; color: var(--ink); }
.line .when { margin-left: 8px; }
.empty-feed { padding: 16px 0; }
</style>
