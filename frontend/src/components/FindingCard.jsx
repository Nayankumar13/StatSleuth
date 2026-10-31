import { Badge, RangeBar } from './ui'
import { KINDS, fmtP } from '../util'

export default function FindingCard({ f, selected, onSelect }) {
  const d = f.details || {}
  return (
    <article className={`finding ${f.status} ${selected ? 'sel' : ''}`} id={`finding-${f.id}`}>
      <button className="finding-head" onClick={() => onSelect(f.id)} aria-expanded={selected}>
        <Badge status={f.status} />
        <span className="finding-kind">{KINDS[f.kind]}</span>
        <code className="finding-title">{f.title}</code>
      </button>
      {selected && (
        <div className="finding-body">
          <p>{f.explanation}</p>
          {f.kind === 'pvalue' && d.computed_p_range && (
            <>
              <RangeBar computed={d.computed_p_range} reported={d.reported_p_range} />
              <dl className="kv">
                <dt>Reported</dt><dd>p {d.reported_p}</dd>
                <dt>Recomputed</dt><dd>p = {fmtP(d.computed_p)}</dd>
                {d.one_tailed_p != null && (<><dt>One-tailed</dt><dd>p = {fmtP(d.one_tailed_p)}</dd></>)}
                {d.epsilon_estimate != null && (<><dt>Fitted ε</dt><dd>{d.epsilon_estimate.toFixed(2)}</dd></>)}
              </dl>
            </>
          )}
          {f.kind === 'ci' && d.p_implied_range && (
            <dl className="kv"><dt>p implied by CI</dt><dd>{fmtP(d.p_implied_range[0])} – {fmtP(d.p_implied_range[1])}</dd></dl>
          )}
          {f.suggestion && <p className="suggest"><strong>What to check:</strong> {f.suggestion}</p>}
        </div>
      )}
    </article>
  )
}
