import { useState } from 'react'
import { api } from '../api'
import { ErrorBox, Spinner } from '../components/ui'
import { fmtP } from '../util'

function Result({ ok, children }) {
  return <div className={`result ${ok ? 'ok' : 'gross'}`} role="status">{children}</div>
}

function GrimTool() {
  const [f, setF] = useState({ mean: '5.19', n: '28', items: '1', sd: '' })
  const [res, setRes] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function go(e) {
    e.preventDefault(); setErr(null); setRes(null); setBusy(true)
    try {
      const body = { mean: f.mean.trim(), n: Number(f.n), items: Number(f.items) }
      if (f.sd.trim()) body.sd = f.sd.trim()
      setRes(await api.grim(body))
    } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }

  return (
    <section className="card">
      <h2>GRIM / GRIMMER calculator</h2>
      <p className="fine">Can a mean (and SD) of integer data of this size exist? Type the numbers <b>exactly as printed</b>, keeping trailing zeros (e.g. 3.50).</p>
      <form onSubmit={go} className="form-row">
        <label className="field"><span>Mean</span><input value={f.mean} onChange={set('mean')} inputMode="decimal" required /></label>
        <label className="field"><span>n</span><input value={f.n} onChange={set('n')} type="number" min="1" required /></label>
        <label className="field"><span>Items / scale</span><input value={f.items} onChange={set('items')} type="number" min="1" /></label>
        <label className="field"><span>SD (optional)</span><input value={f.sd} onChange={set('sd')} inputMode="decimal" /></label>
        <button className="btn primary" disabled={busy}>Test</button>
      </form>
      <ErrorBox error={err} />
      {busy && <Spinner />}
      {res && (
        <>
          {!res.informative && <Result ok>n is large relative to the precision of the mean, so every mean is reachable: the test cannot fail.</Result>}
          {res.informative && (
            <Result ok={res.grim_consistent}>
              GRIM: mean {res.mean} {res.grim_consistent ? 'is' : 'is NOT'} possible with n = {res.n}{res.items > 1 ? ` and ${res.items} items` : ''}.
              {!res.grim_consistent && <> Nearest reachable means: <b>{res.nearest_possible_means.join(', ')}</b>.</>}
            </Result>
          )}
          {'grimmer_consistent' in res && (
            <Result ok={res.grimmer_consistent}>
              GRIMMER: SD {res.sd} {res.grimmer_consistent ? 'is' : 'is NOT'} possible together with mean {res.mean} (n = {res.n}).
            </Result>
          )}
        </>
      )}
    </section>
  )
}

function PTool() {
  const [f, setF] = useState({ kind: 't', stat: '2.20', df1: '28', df2: '', p_rel: '=', p: '.036' })
  const [res, setRes] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function go(e) {
    e.preventDefault(); setErr(null); setRes(null); setBusy(true)
    try {
      const body = { kind: f.kind, stat: f.stat.trim(), p_rel: f.p_rel, p: f.p.trim(),
        df1: f.kind === 'z' || f.df1 === '' ? null : Number(f.df1), df2: f.kind === 'F' && f.df2 !== '' ? Number(f.df2) : null }
      setRes(await api.pvalue(body))
    } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }

  return (
    <section className="card">
      <h2>p-value recomputation</h2>
      <p className="fine">Recomputes p from the statistic and degrees of freedom, allowing for the rounding of the printed statistic.</p>
      <form onSubmit={go} className="form-row">
        <label className="field"><span>Test</span>
          <select value={f.kind} onChange={set('kind')}>
            <option value="t">t</option><option value="F">F</option><option value="chi2">χ²</option><option value="r">r</option><option value="z">z</option>
          </select></label>
        <label className="field"><span>Statistic</span><input value={f.stat} onChange={set('stat')} inputMode="decimal" required /></label>
        {f.kind !== 'z' && <label className="field"><span>df{f.kind === 'F' ? '₁' : ''}</span><input value={f.df1} onChange={set('df1')} inputMode="decimal" required /></label>}
        {f.kind === 'F' && <label className="field"><span>df₂</span><input value={f.df2} onChange={set('df2')} inputMode="decimal" required /></label>}
        <label className="field"><span>Reported p</span>
          <div className="pair">
            <select value={f.p_rel} onChange={set('p_rel')} aria-label="relation"><option>=</option><option>&lt;</option><option>&gt;</option></select>
            <input value={f.p} onChange={set('p')} inputMode="decimal" required />
          </div></label>
        <button className="btn primary" disabled={busy}>Recompute</button>
      </form>
      <ErrorBox error={err} />
      {busy && <Spinner />}
      {res && (
        <Result ok={res.consistent}>
          Recomputed p = <b>{fmtP(res.computed_p)}</b> (range {res.computed_p_range[0].toPrecision(3)} – {res.computed_p_range[1].toPrecision(3)}).
          {res.consistent ? ' Consistent with the reported p.' : ' NOT consistent with the reported p.'}
          {res.one_tailed_p != null && !res.consistent && <> A one-tailed test would give p = {fmtP(res.one_tailed_p)}.</>}
        </Result>
      )}
    </section>
  )
}

export default function Tools() {
  return (
    <div className="page">
      <section className="hero small"><h1>Quick checks</h1><p>Test a single number without pasting a manuscript.</p></section>
      <div className="grid-2"><GrimTool /><PTool /></div>
    </div>
  )
}
