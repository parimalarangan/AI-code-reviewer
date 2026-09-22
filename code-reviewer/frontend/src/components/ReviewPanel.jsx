// ReviewPanel.jsx
// ---------------
// Renders the structured review returned by the backend: overall score,
// plain-English summary, and a categorized list of findings (each with
// severity, explanation, and suggested fix).

import SeverityBadge from "./SeverityBadge.jsx";

const CATEGORY_LABELS = {
  bug: "🐛 Bug",
  security: "🔒 Security",
  performance: "⚡ Performance",
  best_practice: "✅ Best Practice",
  style: "🎨 Style",
  maintainability: "🧩 Maintainability",
};

/** Pick a score color: green (good) -> amber (ok) -> red (poor). */
function scoreColor(score) {
  if (score >= 80) return "#22c55e";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

/**
 * @param {Object} props
 * @param {Object|null} props.review - The CodeReviewResponse from the backend, or null if none yet.
 * @param {boolean} props.loading - Whether a review request is in flight.
 * @param {string|null} props.error - Error message to display, if any.
 */
export default function ReviewPanel({ review, loading, error }) {
  if (loading) {
    return (
      <div className="review-panel review-panel--empty">
        <p>Analyzing your code… this can take a few seconds on a local model.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="review-panel review-panel--error">
        <h3>Review failed</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="review-panel review-panel--empty">
        <p>Paste or write some code, then click "Review Code" to get AI-powered feedback.</p>
      </div>
    );
  }

  return (
    <div className="review-panel">
      <div className="review-header">
        <div className="review-score" style={{ borderColor: scoreColor(review.overall_score) }}>
          <span className="review-score__number" style={{ color: scoreColor(review.overall_score) }}>
            {review.overall_score}
          </span>
          <span className="review-score__label">/ 100</span>
        </div>
        <div>
          <p className="review-summary">{review.summary}</p>
          <p className="review-meta">
            Language: <strong>{review.language_detected}</strong> · Model:{" "}
            <strong>{review.model_used}</strong>
          </p>
        </div>
      </div>

      {review.static_analysis?.length > 0 && (
        <div className="static-analysis-strip">
          {review.static_analysis.map((tool) => (
            <span key={tool.tool} className="static-tool-chip">
              {tool.tool}: {tool.findings_count} finding{tool.findings_count === 1 ? "" : "s"}
            </span>
          ))}
        </div>
      )}

      <h3 className="findings-heading">Findings ({review.findings.length})</h3>
      {review.findings.length === 0 && <p>No issues found. Nice work!</p>}

      <ul className="findings-list">
        {review.findings.map((finding, index) => (
          <li key={index} className="finding-card">
            <div className="finding-card__header">
              <span className="finding-category">{CATEGORY_LABELS[finding.category] || finding.category}</span>
              <SeverityBadge severity={finding.severity} />
              {finding.line != null && <span className="finding-line">Line {finding.line}</span>}
              <span className="finding-source">via {finding.source}</span>
            </div>
            <h4 className="finding-title">{finding.title}</h4>
            <p className="finding-explanation">{finding.explanation}</p>
            {finding.suggestion && (
              <pre className="finding-suggestion">
                <code>{finding.suggestion}</code>
              </pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
