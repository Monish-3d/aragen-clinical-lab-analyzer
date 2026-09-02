// Every badge carries an icon and a word as well as a colour, so the severity
// is still readable if the colours cannot be told apart.
const BADGES = {
  CRITICAL: { label: 'Critical', icon: '🚨' },
  WARNING: { label: 'Warning', icon: '⚠️' },
  NORMAL: { label: 'Normal', icon: '✓' },
  UNKNOWN: { label: 'Not classified', icon: '?' },
}

function SeverityBadge({ status }) {
  const badge = BADGES[status] || BADGES.UNKNOWN

  return (
    <span className={`badge badge-${status.toLowerCase()}`}>
      <span aria-hidden="true">{badge.icon}</span> {badge.label}
    </span>
  )
}

export default SeverityBadge
