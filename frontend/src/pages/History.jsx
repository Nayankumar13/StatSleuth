import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ErrorBox, Spinner } from '../components/ui'

export default function History() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  const load = () => api.reports().then(setRows).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  async function del(id) {
    if (!window.confirm('Delete this report and its stored text?')) return
    try { await api.remove(id); load() } catch (e) { setError(e.message) }
  }

  return (
    <div className="page">
      <section className="hero small"><h1>Saved reports</h1><p>Stored in the server's SQLite database. Delete any report at any time.</p></section>
      <ErrorBox error={error} onClose={() => setError(null)} />
      {!rows && !error && <Spinner />}
      {rows && rows.length === 0 && <div className="card empty">No saved reports yet. <Link to="/">Run your first analysis</Link>.</div>}
      {rows && rows.length > 0 && (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>Title</th><th>Date</th><th>Checked</th><th>Serious</th><th>Minor</th><th /></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td><Link to={`/report/${r.id}`}>{r.title}</Link></td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                  <td>{r.summary.checked}</td>
                  <td className={r.summary.gross ? 'num gross' : 'num'}>{r.summary.gross}</td>
                  <td className={r.summary.by_status.minor ? 'num minor' : 'num'}>{r.summary.by_status.minor || 0}</td>
                  <td><button className="link danger" onClick={() => del(r.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
