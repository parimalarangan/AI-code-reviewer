// App.jsx
// -------
// Top-level component: holds the editor state, talks to the backend via
// reviewApi.js, and lays out the two-pane UI (editor on the left, results
// on the right).

import { useEffect, useState } from "react";
import { checkHealth, reviewCode } from "./api/reviewApi.js";
import CodeEditor from "./components/CodeEditor.jsx";
import LanguageSelector from "./components/LanguageSelector.jsx";
import ReviewPanel from "./components/ReviewPanel.jsx";

const DEFAULT_CODE = `def calculate_average(numbers):
    total = 0
    for n in numbers:
        total = total + n
    return total / len(numbers)
`;

export default function App() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [language, setLanguage] = useState("python");
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState("checking");

  // Ping the backend once on mount so we can show a clear "backend
  // unreachable" indicator instead of a confusing failure only when the
  // user tries to submit code.
  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  async function handleReview() {
    setLoading(true);
    setError(null);
    try {
      const result = await reviewCode({ code, language });
      setReview(result);
    } catch (err) {
      setError(err.message);
      setReview(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>AI Code Reviewer</h1>
        <p className="app-subtitle">
          Open-source, self-hostable AI code review — bugs, security, performance &amp; best practices.
        </p>
        <span className={`backend-status backend-status--${backendStatus}`}>
          Backend: {backendStatus}
        </span>
      </header>

      <main className="app-main">
        <section className="editor-section">
          <div className="editor-toolbar">
            <LanguageSelector value={language} onChange={setLanguage} />
            <button className="review-button" onClick={handleReview} disabled={loading || !code.trim()}>
              {loading ? "Reviewing…" : "Review Code"}
            </button>
          </div>
          <CodeEditor code={code} onChange={setCode} language={language} />
        </section>

        <section className="results-section">
          <ReviewPanel review={review} loading={loading} error={error} />
        </section>
      </main>
    </div>
  );
}
