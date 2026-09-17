<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: { type: Object, default: null },
  label: { type: String, default: '' },
  cancellable: { type: Boolean, default: false },
})
defineEmits(['cancel'])

const STATUS = { queued: 'Waiting to start', running: 'Working', done: 'Finished', failed: 'Failed', cancelled: 'Cancelled' }
const active = computed(() => props.task && (props.task.status === 'queued' || props.task.status === 'running'))
const pctDone = computed(() => Math.round(Math.max(0, Math.min(1, props.task?.progress || 0)) * 100))
</script>

<template>
  <div v-if="task" class="task" :class="task.status" role="status" aria-live="polite">
    <div class="task-top">
      <strong>{{ label || STATUS[task.status] }}</strong>
      <span class="muted small tnum" v-if="active">{{ pctDone }}%</span>
      <span v-else class="pill" :class="{ good: task.status === 'done', bad: task.status === 'failed', warn: task.status === 'cancelled' }">
        {{ STATUS[task.status] || task.status }}
      </span>
      <span class="spacer"></span>
      <button v-if="cancellable && active" class="btn small danger" type="button" @click="$emit('cancel')">Cancel</button>
    </div>
    <div v-if="active" class="progress" role="progressbar" :aria-valuenow="pctDone" aria-valuemin="0" aria-valuemax="100">
      <div :style="{ width: pctDone + '%' }"></div>
    </div>
    <p v-if="task.message" class="small muted break">{{ task.message }}</p>
    <p v-if="task.error" class="notice error break">{{ task.error }}</p>
  </div>
</template>

<style scoped>
.task { display: grid; gap: 8px; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--panel-2); }
.task-top { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
</style>
