import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { Donut, ErrorBox, Spinner } from '../components/ui'
import FindingCard from '../components/FindingCard'
import Manuscript from '../components/Manuscript'
import { KINDS, STATUS, pct } from '../util'

const FILTERS = [
  ['attention', 'Needs attention', (f) => ['gross', 'minor', 'caveat'].includes(f.status)],
  ['all', 'All', () => true],
  ['ok', 'Consistent', (f) => f.status === 'ok'],
  ['other', 'Not checked', (f) => ['na', 'unverifiable'].includes(f.status)],
]

export default function Report() {
  const { id } = useParams()
  const [rep, setRep] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('attention')
  const [kind, setKind] = useState('all')
  const [sel, setSel] = useState(null)

  useEffect(() => {
    setRep(null); setError(null)
    if (id === 'local') {
      const raw = sessionStorage.getItem('statsleuth:local')
      raw ? setRep(JSON.parse(raw)) : setError('This unsaved report is no longer in the browser tab. Run the analysis again.')
    } else api.report(id).then(setRep).catch((e) => setError(e.message))
  }, [id])

  const list = useMemo(() => {
    if (!rep) return []
    const fn = FILTERS.find((f) => f[0] === filter)[2]
    return rep.findings
      .filter(fn)
      .filter((f) => kind === 'all' || f.kind === kind)
      .sort((a, b) => STATUS[a.status].rank - STATUS[b.status].rank || a.start - b.start)
  }, [rep, filter, kind])

  function select(fid) {
    setSel((cur) => (cur === fid ? null : fid))
    const f = rep.findings.find((x) => x.id === fid)
    requestAnimationFrame(() => {
      document.getElementById(`mark-${fid}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      if (f) document.getElementById(`finding-${fid}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    })
  }

  if (error) return <div className="page"><ErrorBox error={error} /><Link to="/" className="btn">New analysis</Link></div>
  if (!rep) return <div className="page"><Spinner label="Loading report…" /></div>

  const s = rep.summary
  const bs = s.by_status
  const kinds = Object.keys(s.by_kind)

  return (
    <div className="page wide">
      <header className="report-head">
        <div>
          <p className="eyebrow">Report {rep.id ? `· ${rep.id}` : '· not saved'}</p>
          <h1>{rep.title}</h1>
        </div>
        <div className="actions">
          <Link className="btn" to="/">New analysis</Link>
          {rep.id && ['json', 'csv', 'md'].map((f) => (
            <a key={f} className="btn" href={api.exportUrl(rep.id, f)} download>{f.toUpperCase()}</a>
          ))}
          <button className="btn" onClick={() => window.print()}>Print</button>
        </div>
      </header>

      <div className={`verdict ${bs.gross ? 'gross' : bs.minor ? 'minor' : 'ok'}`} role="status">
        <strong>{s.verdict}</strong>
      </div>

      <section className="stats">
        <div className="stat"><b>{s.checked}</b><span>statistics checked</span></div>
        <div className="stat gross"><b>{bs.gross || 0}</b><span>serious</span></div>
        <div className="stat minor"><b>{bs.minor || 0}</b><span>minor</span></div>
        <div className="stat caveat"><b>{bs.caveat || 0}</b><span>need context</span></div>
        <div className="stat ok"><b>{bs.ok || 0}</b><span>consistent</span></div>
        <div className="stat"><b>{(bs.na || 0) + (bs.unverifiable || 0)}</b><span>not checkable</span></div>
      </section>

      <section className="card overview">
        <Donut counts={bs} />
        <ul className="legend">
          {['gross', 'minor', 'caveat', 'ok', 'unverifiable', 'na'].filter((k) => bs[k]).map((k) => (
            <li key={k}><i className={`sw ${STATUS[k].cls}`} />{STATUS[k].label}<b>{bs[k]}</b></li>
          ))}
        </ul>
        <div className="bykind">
          <h3>By check</h3>
          {kinds.map((k) => {
            const c = s.by_kind[k]
            const tot = Object.values(c).reduce((a, b) => a + b, 0)
            return (
              <div className="bk-row" key={k}>
                <span>{KINDS[k]}</span>
                <div className="bk-bar">
                  {['gross', 'minor', 'caveat', 'ok', 'unverifiable', 'na'].map((st) => c[st] ? (
                    <i key={st} className={`sw ${STATUS[st].cls}`} style={{ width: `${(c[st] / tot) * 100}%` }} title={`${STATUS[st].label}: ${c[st]}`} />
                  ) : null)}
                </div>
                <em>{tot}</em>
              </div>
            )
          })}
          {s.flag_rate != null && (
            <p className="fine">Flag rate {pct(s.flag_rate)} (95% Wilson interval {pct(s.flag_rate_ci95[0])}–{pct(s.flag_rate_ci95[1])}). With few statistics the interval is wide.</p>
          )}
        </div>
      </section>

      <div className="split">
        <section className="card">
          <div className="card-head">
            <h2>Findings</h2>
            <div className="seg" role="tablist">
              {FILTERS.map(([k, label]) => (
                <button key={k} role="tab" aria-selected={filter === k} className={filter === k ? 'on' : ''} onClick={() => setFilter(k)}>{label}</button>
              ))}
            </div>
          </div>
          <label className="field inline">
            <span>Check type</span>
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="all">All</option>
              {kinds.map((k) => <option key={k} value={k}>{KINDS[k]}</option>)}
            </select>
          </label>
          <div className="finding-list">
            {list.length === 0 && <p className="empty">Nothing in this view. {filter === 'attention' && s.checked > 0 ? 'No statistics need attention.' : ''}</p>}
            {list.map((f) => <FindingCard key={f.id} f={f} selected={sel === f.id} onSelect={select} />)}
          </div>
        </section>

        <section className="card">
          <div className="card-head"><h2>Text</h2><span className="fine">Click a highlight to open its finding</span></div>
          <Manuscript text={rep.text} findings={rep.findings} selectedId={sel} onSelect={(fid) => { setSel(fid); setFilter('all'); setKind('all'); requestAnimationFrame(() => document.getElementById(`finding-${fid}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })) }} />
        </section>
      </div>
    </div>
  )
}
