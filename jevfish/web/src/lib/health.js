// One shared copy of /api/health, so the banner and the Setup screen agree.
import { ref } from 'vue'
import { api } from './api.js'

export const health = ref(null)
export const healthError = ref('')

export async function refreshHealth() {
  try {
    health.value = await api.health()
    healthError.value = ''
  } catch (e) {
    healthError.value = e.message
  }
  return health.value
}
