// Thin fetch wrapper. Every call throws an Error with a human-readable message.
async function request(path, opts = {}) {
  let res
  try {
    res = await fetch(`/api${path}`, opts)
  } catch {
    throw new Error('Cannot reach the StatSleuth server. Is the backend running on port 8000?')
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') msg = body.detail
      else if (Array.isArray(body.detail)) msg = body.detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
    } catch { /* non-JSON error body */ }
    throw new Error(msg)
  }
  return res
}

const json = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  samples: async () => (await request('/samples')).json(),
  sample: async (id) => (await request(`/samples/${id}`)).json(),
  analyze: async (payload) => (await request('/analyze', json(payload))).json(),
  analyzeFile: async (file, o) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('alpha', o.alpha)
    fd.append('items_per_scale', o.items_per_scale)
    fd.append('integer_data', o.integer_data)
    fd.append('persist', o.persist)
    return (await request('/analyze/file', { method: 'POST', body: fd })).json()
  },
  reports: async () => (await request('/reports')).json(),
  report: async (id) => (await request(`/reports/${id}`)).json(),
  remove: async (id) => (await request(`/reports/${id}`, { method: 'DELETE' })).json(),
  grim: async (p) => (await request('/tools/grim', json(p))).json(),
  pvalue: async (p) => (await request('/tools/pvalue', json(p))).json(),
  exportUrl: (id, format) => `/api/reports/${id}/export?format=${format}`,
}
