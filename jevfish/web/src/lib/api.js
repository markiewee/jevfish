// Thin fetch wrapper. Every error becomes an Error whose message is the API's `error` string.
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(method, path, body, isForm = false) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    if (isForm) opts.body = body
    else {
      opts.headers['Content-Type'] = 'application/json'
      opts.body = JSON.stringify(body)
    }
  }
  let res
  try {
    res = await fetch('/api' + path, opts)
  } catch (e) {
    throw new ApiError('Cannot reach the JevFish server. Check that it is running.', 0)
  }
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch (e) {
    data = null
  }
  if (!res.ok) {
    const msg = (data && data.error) || `Request failed with status ${res.status}`
    throw new ApiError(msg, res.status)
  }
  return data
}

const enc = encodeURIComponent

export const api = {
  health: () => request('GET', '/health'),
  settings: () => request('GET', '/settings'),
  saveSettings: (body) => request('PUT', '/settings', body),
  checkKeys: (body) => request('POST', '/settings/check', body),
  example: () => request('GET', '/example'),
  shutdown: () => request('POST', '/shutdown'),
  task: (tid) => request('GET', `/tasks/${enc(tid)}`),
  cancelTask: (tid) => request('POST', `/tasks/${enc(tid)}/cancel`),

  projects: () => request('GET', '/projects'),
  createProject: (body) => request('POST', '/projects', body),
  project: (pid) => request('GET', `/projects/${enc(pid)}`),
  patchProject: (pid, body) => request('PATCH', `/projects/${enc(pid)}`, body),
  deleteProject: (pid) => request('DELETE', `/projects/${enc(pid)}`),
  seed: (pid) => request('GET', `/projects/${enc(pid)}/seed`),
  addSeed: (pid, text, source) => request('POST', `/projects/${enc(pid)}/seed`, { text, source }),
  uploadFiles: (pid, files) => {
    const form = new FormData()
    for (const f of files) form.append('file', f, f.name)
    return request('POST', `/projects/${enc(pid)}/files`, form, true)
  },

  buildGraph: (pid) => request('POST', `/projects/${enc(pid)}/graph`),
  graph: (pid) => request('GET', `/projects/${enc(pid)}/graph`),
  searchGraph: (pid, q, limit = 10) => request('GET', `/projects/${enc(pid)}/graph/search?q=${enc(q)}&limit=${limit}`),

  prepare: (pid, body) => request('POST', `/projects/${enc(pid)}/prepare`, body),
  frame: (pid) => request('GET', `/projects/${enc(pid)}/frame`),
  saveFrame: (pid, frame) => request('PUT', `/projects/${enc(pid)}/frame`, frame),
  crowd: (pid) => request('GET', `/projects/${enc(pid)}/crowd`),

  estimate: (pid, cfg) => request('POST', `/projects/${enc(pid)}/estimate`, cfg),
  runs: (pid) => request('GET', `/projects/${enc(pid)}/runs`),
  startRun: (pid, cfg) => request('POST', `/projects/${enc(pid)}/runs`, cfg),
  run: (pid, rid) => request('GET', `/projects/${enc(pid)}/runs/${enc(rid)}`),
  cancelRun: (pid, rid) => request('POST', `/projects/${enc(pid)}/runs/${enc(rid)}/cancel`),
  actions: (pid, rid, since = 0, limit = 500) =>
    request('GET', `/projects/${enc(pid)}/runs/${enc(rid)}/actions?since=${since}&limit=${limit}`),
  polls: (pid, rid) => request('GET', `/projects/${enc(pid)}/runs/${enc(rid)}/polls`),

  startReport: (pid, rid) => request('POST', `/projects/${enc(pid)}/runs/${enc(rid)}/report`),
  report: (pid, rid) => request('GET', `/projects/${enc(pid)}/runs/${enc(rid)}/report`),

  chat: (pid, rid, body) => request('POST', `/projects/${enc(pid)}/runs/${enc(rid)}/chat`, body),
  chatHistory: (pid, rid, agentId, variant) =>
    request('GET', `/projects/${enc(pid)}/runs/${enc(rid)}/chat/${enc(agentId)}${variant ? `?variant=${enc(variant)}` : ''}`),
  ask: (pid, rid, body) => request('POST', `/projects/${enc(pid)}/runs/${enc(rid)}/ask`, body),
  asked: (pid, rid) => request('GET', `/projects/${enc(pid)}/runs/${enc(rid)}/ask`),
}

export const TERMINAL = new Set(['done', 'failed', 'cancelled'])

// Poll a task about once a second until it ends. onUpdate gets every snapshot.
export async function waitForTask(task, onUpdate, signal) {
  let t = task
  onUpdate && onUpdate(t)
  while (!TERMINAL.has(t.status)) {
    await new Promise((r) => setTimeout(r, 1000))
    if (signal && signal.aborted) return t
    try {
      t = await api.task(t.id)
    } catch (e) {
      if (e.status === 404) throw new ApiError('The server lost track of this task (it may have restarted).', 404)
      continue
    }
    onUpdate && onUpdate(t)
  }
  return t
}
