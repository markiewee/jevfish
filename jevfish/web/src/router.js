import { createRouter, createWebHistory } from 'vue-router'
import ProjectsView from './views/ProjectsView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import StepGraph from './views/StepGraph.vue'
import StepCrowd from './views/StepCrowd.vue'
import StepSimulate from './views/StepSimulate.vue'
import StepReport from './views/StepReport.vue'
import StepAsk from './views/StepAsk.vue'
import SetupView from './views/SetupView.vue'
import { refreshHealth } from './lib/health.js'

export const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    { path: '/', name: 'projects', component: ProjectsView },
    {
      path: '/p/:pid',
      component: WorkspaceView,
      props: true,
      children: [
        { path: '', redirect: (to) => ({ name: 'graph', params: to.params, query: to.query }) },
        { path: 'graph', name: 'graph', component: StepGraph },
        { path: 'crowd', name: 'crowd', component: StepCrowd },
        { path: 'simulate', name: 'simulate', component: StepSimulate },
        { path: 'report', name: 'report', component: StepReport },
        { path: 'ask', name: 'ask', component: StepAsk },
      ],
    },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/:rest(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

// First load only: send people without keys to Setup.
let firstLoad = true
router.beforeEach(async (to) => {
  if (!firstLoad) return true
  firstLoad = false
  const h = await refreshHealth()
  if (h && h.setup_needed && to.name !== 'setup') return { name: 'setup' }
  return true
})
