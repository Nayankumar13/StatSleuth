import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { ErrorBox, Spinner } from '../components/ui'

const LIMIT = 300000

export default function Analyze() {
  const nav = useNavigate()
  const fileRef = useRef(null)
  const [samples, setSamples] = useState([])
  const [text, setText] = useState('')
  const [title, setTitle] = useState('Pasted text')
  const [file, setFile] = useState(null)
  const [opts, setOpts] = useState({ alpha: 0.05, items_per_scale: 1, integer_data: true, persist: true })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [drag, setDrag] = useState(false)

  useEffect(() => { api.samples().then(setSamples).catch((e) => setError(e.message)) }, [])

  const set = (k, v) => setOpts((o) => ({ ...o, [k]: v }))

  async function loadSample(id) {
    setError(null)
    try {
      const s = await api.sample(id)
      setText(s.text); setTitle(s.title); setFile(null)
    } catch (e) { setError(e.message) }
  }

  function pickFile(f) {
    if (!f) return
    if (!/\.(txt|md|pdf)$/i.test(f.name)) return setError('Only .txt, .md and .pdf files are supported.')
    if (f.size > 5 * 1024 * 1024) return setError('File is larger than 5 MB.')
    setError(null); setFile(f); setTitle(f.name); setText('')
  }

  async function run() {
    setError(null); setBusy(true)
    try {
      const report = file
        ? await api.analyzeFile(file, opts)
        : await api.analyze({ text, title: title || 'Pasted text', persist: opts.persist,
            options: { alpha: Number(opts.alpha), items_per_scale: Number(opts.items_per_scale), integer_data: opts.integer_data } })
      if (report.id) nav(`/report/${report.id}`)
      else { sessionStorage.setItem('statsleuth:local', JSON.stringify(report)); nav('/report/local') }
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const canRun = (file || text.trim().length > 0) && text.length <= LIMIT && !busy

  return (
    <div className="page">
      <section className="hero">
        <h1>Find the numbers that don't add up.</h1>
        <p>
          Paste a results section or upload a manuscript. StatSleuth re-computes every p-value, tests means and SDs for
          mathematical possibility (GRIM / GRIMMER), and cross-checks percentages and confidence intervals, all
          allowing for rounding and for legitimate corrections.
        </p>
      </section>

      <ErrorBox error={error} onClose={() => setError(null)} />

      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <h2>1 · Add text</h2>
            <div className="chips" aria-label="Load a demo manuscript">
              <span className="chips-label">Try a demo:</span>
              {samples.map((s) => (
                <button key={s.id} className="chip" onClick={() => loadSample(s.id)} title={s.description}>{s.title.split(' – ')[0]}</button>
              ))}
            </div>
          </div>

          <label className="field">
            <span>Title</span>
            <input value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
          </label>

          {file ? (
            <div className="filebox">
              <strong>{file.name}</strong> <span className="muted-t">({(file.size / 1024).toFixed(0)} KB)</span>
              <button className="link" onClick={() => { setFile(null); setTitle('Pasted text') }}>Remove</button>
            </div>
          ) : (
            <>
              <textarea
                className="editor" rows={13} value={text} spellCheck={false}
                placeholder={'Paste text here, e.g.\n\nThe groups differed, t(58) = 1.40, p = .012. The mean was M = 3.48 (SD = 0.90, n = 30).'}
                onChange={(e) => setText(e.target.value)} aria-label="Manuscript text"
              />
              <div className={`counter ${text.length > LIMIT ? 'bad' : ''}`}>{text.length.toLocaleString()} / {LIMIT.toLocaleString()} characters</div>
            </>
          )}

          <div
            className={`drop ${drag ? 'over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pickFile(e.dataTransfer.files[0]) }}
            onClick={() => fileRef.current?.click()}
            role="button" tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && fileRef.current?.click()}
          >
            Or drop a <b>.pdf / .txt / .md</b> file here (max 5 MB, text-based PDFs only)
            <input ref={fileRef} type="file" accept=".pdf,.txt,.md" hidden onChange={(e) => pickFile(e.target.files[0])} />
          </div>
        </section>

        <section className="card">
          <h2>2 · Settings</h2>
          <label className="field">
            <span>Significance level α</span>
            <input type="number" step="0.01" min="0.001" max="0.5" value={opts.alpha} onChange={(e) => set('alpha', e.target.value)} />
            <small>Used to decide whether an inconsistency changes the conclusion.</small>
          </label>
          <label className="check">
            <input type="checkbox" checked={opts.integer_data} onChange={(e) => set('integer_data', e.target.checked)} />
            <span><b>Assume integer-valued data for GRIM/GRIMMER</b><small>Single Likert items, counts, ages in years. Turn off for continuous measures.</small></span>
          </label>
          <label className="field">
            <span>Items averaged per scale score</span>
            <input type="number" min="1" max="200" step="1" value={opts.items_per_scale} disabled={!opts.integer_data}
              onChange={(e) => set('items_per_scale', e.target.value)} />
            <small>1 = single item. For a 3-item scale mean set 3 (GRIMMER then needs 1).</small>
          </label>
          <label className="check">
            <input type="checkbox" checked={opts.persist} onChange={(e) => set('persist', e.target.checked)} />
            <span><b>Save report to history</b><small>Off = nothing is stored on the server; the report lives only in this browser tab.</small></span>
          </label>

          <button className="btn primary big" disabled={!canRun} onClick={run}>
            {busy ? 'Analysing…' : 'Check statistics'}
          </button>
          {busy && <Spinner label="Recomputing every statistic…" />}
          <p className="fine">
            Automated checks flag numerical contradictions, not misconduct. Typos, corrections that were not described, and
            non-integer data can all trigger flags. Always verify against the original analysis.
          </p>
        </section>
      </div>
    </div>
  )
}
