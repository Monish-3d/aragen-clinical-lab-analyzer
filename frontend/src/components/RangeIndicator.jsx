// Shows where a value sits against its reference range, so "how far outside"
// is visible at a glance instead of only in the sentence underneath.
//
// The scale runs one whole range width past each limit, which is the same
// measure the classifier uses for its first critical rule. So a value sitting
// right at the edge of the bar is exactly one range width out - the point where
// a warning becomes critical.
function RangeIndicator({ value, min, max, status }) {
  const width = max - min

  // A zero-width range would divide by zero and there would be nothing
  // meaningful to draw anyway.
  if (!Number.isFinite(width) || width <= 0) {
    return null
  }

  const scaleMin = min - width
  const scaleMax = max + width
  const position = ((value - scaleMin) / (scaleMax - scaleMin)) * 100

  // Values further out than the scale sit on the edge rather than disappearing.
  const offScale = position < 0 || position > 100
  const left = Math.max(0, Math.min(100, position))

  return (
    <div className="range-indicator">
      <div className="range-track">
        {/* The normal zone is always the middle third, because the padding on
            each side is exactly one range width. */}
        <div className="range-normal" />
        <div
          className={`range-marker range-marker-${status.toLowerCase()}${
            offScale ? ' range-marker-offscale' : ''
          }`}
          style={{ left: `${left}%` }}
        />
      </div>

      <div className="range-scale">
        <span className="range-limit range-limit-min">{min}</span>
        <span className="range-limit range-limit-max">{max}</span>
      </div>
    </div>
  )
}

export default RangeIndicator
