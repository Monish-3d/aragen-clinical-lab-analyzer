import SeverityBadge from './SeverityBadge'

// Some tests (pH, urine strips) have "-" as their unit in the dataset, which
// would show up as "1+ -" if it were printed.
function displayUnit(unit) {
  return !unit || unit === '-' ? '' : unit
}

function ResultsDisplay({ analysis }) {
  const { results, summary } = analysis

  return (
    <section className="results">
      <div className="summary">
        <span className="summary-item summary-critical">🚨 Critical: {summary.critical}</span>
        <span className="summary-item summary-warning">⚠️ Warning: {summary.warning}</span>
        <span className="summary-item summary-normal">✓ Normal: {summary.normal}</span>
        {summary.unknown > 0 && (
          <span className="summary-item summary-unknown">? Not classified: {summary.unknown}</span>
        )}
      </div>

      {/* The backend already sorted these critical first, so they are rendered
          in the order they arrive. */}
      {results.map((result, index) => (
        <article className={`card result result-${result.status.toLowerCase()}`} key={index}>
          <div className="result-head">
            <div>
              <h3>{result.test_name}</h3>
              <p className="measured">
                {result.value} {displayUnit(result.unit)}
              </p>
            </div>
            <SeverityBadge status={result.status} />
          </div>

          {result.reference_range && (
            <p className="reference">
              Reference range: {result.reference_range} {displayUnit(result.unit)}
            </p>
          )}

          <dl className="explanation">
            <dt>Why this was flagged</dt>
            <dd>{result.reason}</dd>

            <dt>What it can mean</dt>
            <dd>{result.explanation}</dd>

            <dt>Suggested next step</dt>
            <dd>{result.next_step}</dd>
          </dl>
        </article>
      ))}

      <p className="disclaimer">
        This tool provides AI-assisted interpretation based on supplied laboratory
        reference ranges. It is not a medical diagnosis. Clinical decisions should be
        made by a qualified healthcare professional.
      </p>
    </section>
  )
}

export default ResultsDisplay
