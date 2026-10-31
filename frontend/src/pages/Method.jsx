export default function Method() {
  return (
    <div className="page prose">
      <section className="hero small"><h1>How it works</h1><p>Every check is deterministic mathematics. There is no model that "guesses".</p></section>

      <section className="card">
        <h2>Rounding-aware checks</h2>
        <p>A printed <code>2.20</code> means "somewhere in [2.195, 2.205]". StatSleuth recomputes p over that whole interval and only complains if the reported p lies <em>outside</em> the resulting range. Checkers that compare a single recomputed value to the printed p raise many false alarms from rounding alone.</p>
        <table>
          <thead><tr><th>Check</th><th>What is verified</th><th>Reference</th></tr></thead>
          <tbody>
            <tr><td>p-value</td><td>t, F, χ², r, z with df → p, for ranges, inequalities (p &lt; .05), and significance flips at α</td><td>Nuijten et al., 2016 (statcheck study)</td></tr>
            <tr><td>Corrections</td><td>A mismatching F is accepted as "needs context" only if a sphericity-corrected df (ε between 1/df₁ and 1) can produce the reported p <em>and</em> the text mentions a correction. Adjusted p-values may only be <em>larger</em> than raw p. One-tailed matches are called out.</td><td>Schmidt, 2017 (arXiv:1610.01010)</td></tr>
            <tr><td>GRIM</td><td>Is the mean reachable as an integer sum divided by n (× items)?</td><td>Brown &amp; Heathers, 2017</td></tr>
            <tr><td>GRIMMER</td><td>Given the mean, is the SD reachable (parity and minimum sum-of-squares of integer data)?</td><td>Anaya, 2016</td></tr>
            <tr><td>Percentages</td><td>k/n × 100 rounds to the printed percentage</td><td>arithmetic</td></tr>
            <tr><td>CI vs p</td><td>Estimate inside its CI; a 95% CI that includes the null cannot go with p &lt; .05 (and vice versa); p implied by the CI close to the reported p</td><td>Altman &amp; Bland, BMJ 2011</td></tr>
            <tr><td>df vs N</td><td>A test's df cannot require more participants than the largest N stated in the text</td><td>arithmetic</td></tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Limitations (please read)</h2>
        <ul>
          <li>Extraction is pattern based. It recognises APA-style reports such as <code>t(28) = 2.20, p = .036</code>, not statistics hidden in tables, figures or prose. Text extracted from PDFs can lose symbols (for example χ²) and layout; scanned PDFs need OCR first.</li>
          <li>GRIM/GRIMMER are only valid for integer-valued data. Averaged multi-item scales need the "items per scale" setting; continuous measures should be excluded. GRIMMER here tests <em>necessary</em> conditions, so it never raises false alarms but misses some impossible SDs.</li>
          <li>Corrections are recognised from keywords in the text. If a correction is applied but not mentioned, the result is flagged (and the explanation asks the author to say so).</li>
          <li>The df-vs-N check uses the largest <code>N =</code> in the text; in multi-study papers with unreported Ns it can over-flag, so it is only "minor".</li>
          <li>A flag is a numerical contradiction that needs an explanation: a typo, a different test, an undescribed correction. It is <strong>not</strong> evidence of misconduct and should never be used as such on its own.</li>
        </ul>
      </section>

      <section className="card">
        <h2>Privacy</h2>
        <p>Text you analyse is processed on this server only; no third-party service is called. With "Save report to history" switched off nothing is written to the database. Saved reports (including the full text) can be deleted from the History page.</p>
      </section>
    </div>
  )
}
