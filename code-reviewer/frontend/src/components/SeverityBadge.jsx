// SeverityBadge.jsx
// -----------------
// Small colored pill showing a finding's severity. Colors are chosen for
// quick visual triage: red = urgent, down to grey = informational.

const SEVERITY_STYLES = {
  critical: { background: "#7f1d1d", color: "#fecaca", label: "Critical" },
  high: { background: "#7c2d12", color: "#fed7aa", label: "High" },
  medium: { background: "#78350f", color: "#fde68a", label: "Medium" },
  low: { background: "#1e3a8a", color: "#bfdbfe", label: "Low" },
  info: { background: "#374151", color: "#e5e7eb", label: "Info" },
};

/** @param {Object} props @param {string} props.severity - One of critical|high|medium|low|info. */
export default function SeverityBadge({ severity }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;
  return (
    <span
      className="severity-badge"
      style={{ backgroundColor: style.background, color: style.color }}
    >
      {style.label}
    </span>
  );
}
