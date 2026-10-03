// Thin wrapper around the ANVAYA REST API. In Docker, nginx proxies /api to
// the backend; in `npm run dev`, Vite does the same (see vite.config.js).
const BASE = import.meta.env.VITE_API_URL || ''

async function request(path, { method = 'GET', body, form } = {}) {
  const options = { method, headers: {} }
  if (form) options.body = form
  else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}/api${path}`, options)
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : detail || `Request failed (${res.status})`
    throw new Error(message)
  }
  return data
}

export const api = {
  health: () => request('/health'),
  meta: () => request('/meta'),
  conversations: () => request('/conversations'),
  conversation: (id) => request(`/conversations/${id}`),
  createConversation: (name, members) => request('/conversations', { method: 'POST', body: { name, members } }),
  importChat: (file, name) => {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    return request('/conversations/import', { method: 'POST', form })
  },
  deleteConversation: (id) => request(`/conversations/${id}`, { method: 'DELETE' }),
  addMember: (id, name) => request(`/conversations/${id}/members`, { method: 'POST', body: { name } }),
  sendMessage: (id, sender, text, time) =>
    request(`/conversations/${id}/messages`, { method: 'POST', body: { sender, text, time } }),
  analyze: (id) => request(`/conversations/${id}/analyze`, { method: 'POST' }),
}
