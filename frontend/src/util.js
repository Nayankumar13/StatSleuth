export const STATUS = {
  gross: { label: 'Serious', cls: 'gross', rank: 0, help: 'Impossible or significance-changing inconsistency' },
  minor: { label: 'Minor', cls: 'minor', rank: 1, help: 'Inconsistent, but significance unchanged' },
  caveat: { label: 'Needs context', cls: 'caveat', rank: 2, help: 'Consistent only under an assumption (one-tailed, correction, adjustment)' },
  unverifiable: { label: 'Unverifiable', cls: 'muted', rank: 3, help: 'Not enough information to check' },
  ok: { label: 'Consistent', cls: 'ok', rank: 4, help: 'Numbers agree (given rounding)' },
  na: { label: 'Not applicable', cls: 'muted', rank: 5, help: 'Check does not apply here' },
}

export const KINDS = {
  pvalue: 'p-value',
  grim: 'GRIM (means)',
  grimmer: 'GRIMMER (SDs)',
  percent: 'Percentages',
  ci: 'Confidence interval',
  df_n: 'df vs. sample size',
}

export function worst(findings) {
  return findings.reduce((a, f) => (STATUS[f.status].rank < STATUS[a.status].rank ? f : a), findings[0])
}

export function fmtP(x) {
  if (x == null) return '–'
  if (x < 0.001) return '< .001'
  return x >= 1 ? '1.000' : x.toFixed(3).replace(/^0/, '')
}

export function pct(x, d = 1) {
  return x == null ? '–' : `${(x * 100).toFixed(d)}%`
}

/** Split text into plain / highlighted segments from (possibly overlapping) findings. */
export function buildSegments(text, findings) {
  const groups = new Map()
  for (const f of findings) {
    const key = `${f.start}-${f.end}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(f)
  }
  const spans = [...groups.values()].sort((a, b) => a[0].start - b[0].start)
  const segs = []
  let pos = 0
  for (const g of spans) {
    const { start, end } = g[0]
    if (start < pos) continue // partially overlapping span: skip, still listed on the right
    if (start > pos) segs.push({ text: text.slice(pos, start) })
    segs.push({ text: text.slice(start, end), findings: g, top: worst(g) })
    pos = end
  }
  if (pos < text.length) segs.push({ text: text.slice(pos) })
  return segs
}
