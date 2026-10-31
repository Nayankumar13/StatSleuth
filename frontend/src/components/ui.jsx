import { STATUS, fmtP } from '../util'

export function Badge({ status }) {
  const s = STATUS[status]
  return <span className={`badge ${s.cls}`} title={s.help}>{s.label}</span>
}

export function Spinner({ label = 'Working…' }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="dot" /> {label}
    </div>
  )
}

export function ErrorBox({ error, onClose }) {
  if (!error) return null
  return (
    <div className="errorbox" role="alert">
      <strong>Something went wrong.</strong> {error}
      {onClose && <button className="link" onClick={onClose}>Dismiss</button>}
    </div>
  )
}

/** Donut chart of findings by status (pure SVG). */
export function Donut({ counts }) {
  const order = ['gross', 'minor', 'caveat', 'ok', 'unverifiable', 'na']
  const total = order.reduce((a, k) => a + (counts[k] || 0), 0)
  const R = 54, C = 2 * Math.PI * R
  let off = 0
  return (
    <svg viewBox="0 0 140 140" className="donut" role="img" aria-label="Findings by status">
      <circle cx="70" cy="70" r={R} fill="none" stroke="var(--line)" strokeWidth="16" />
      {total > 0 && order.map((k) => {
        const v = counts[k] || 0
        if (!v) return null
        const len = (v / total) * C
        const el = (
          <circle key={k} cx="70" cy="70" r={R} fill="none" strokeWidth="16"
            stroke={`var(--${STATUS[k].cls === 'muted' ? 'muted-fill' : STATUS[k].cls})`}
            strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} transform="rotate(-90 70 70)" />
        )
        off += len
        return el
      })}
      <text x="70" y="68" textAnchor="middle" className="donut-n">{total}</text>
      <text x="70" y="86" textAnchor="middle" className="donut-l">statistics</text>
    </svg>
  )
}

/** Log-scale bar showing the recomputed p-range against the reported p-range. */
export function RangeBar({ computed, reported }) {
  const lo = -4.3, hi = 0
  const x = (p) => {
    const v = Math.log10(Math.max(p, 1e-5))
    return ((Math.min(Math.max(v, lo), hi) - lo) / (hi - lo)) * 100
  }
  const seg = ([a, b]) => ({ left: `${x(a)}%`, width: `${Math.max(x(b) - x(a), 1.2)}%` })
  return (
    <div className="rangebar" aria-label="Recomputed versus reported p-value range">
      <div className="rb-row"><span>Recomputed</span><div className="rb-track"><i className="rb-seg calc" style={seg(computed)} /></div></div>
      <div className="rb-row"><span>Reported</span><div className="rb-track"><i className="rb-seg rep" style={seg(reported)} /></div></div>
      <div className="rb-axis">
        {[0.0001, 0.001, 0.01, 0.05, 0.1, 1].map((p) => (
          <em key={p} style={{ left: `${x(p)}%` }}>{p === 0.05 ? '.05' : fmtP(p).replace('< ', '')}</em>
        ))}
      </div>
    </div>
  )
}
