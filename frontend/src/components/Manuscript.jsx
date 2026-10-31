import { useMemo } from 'react'
import { buildSegments, STATUS } from '../util'

/** The submitted text with every parsed statistic highlighted by verdict. Rendered as text nodes only (no HTML injection). */
export default function Manuscript({ text, findings, selectedId, onSelect }) {
  const segs = useMemo(() => buildSegments(text, findings), [text, findings])
  return (
    <div className="manuscript" tabIndex={0} aria-label="Analysed text with highlighted statistics">
      {segs.map((s, i) =>
        s.findings ? (
          <mark
            key={i}
            id={`mark-${s.top.id}`}
            className={`hl ${STATUS[s.top.status].cls} ${s.findings.some((f) => f.id === selectedId) ? 'sel' : ''}`}
            onClick={() => onSelect(s.top.id)}
            title={`${STATUS[s.top.status].label}: ${s.top.title}`}
          >
            {s.text}
          </mark>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )}
    </div>
  )
}
