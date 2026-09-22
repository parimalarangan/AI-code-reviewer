// reviewApi.js
// ------------
// Thin wrapper around the backend's /api/review endpoint. Keeping all
// network calls in one small module (instead of scattering axios/fetch
// calls across components) makes it trivial to change the base URL,
// add auth headers, or swap HTTP libraries later without touching any UI
// component.

import axios from "axios";

// In development, Vite's dev-server proxy (see vite.config.js) forwards
// "/api/*" to the FastAPI backend, so a relative URL works everywhere:
// locally, in Docker Compose (via the nginx reverse proxy - see
// nginx.conf), and in production behind a single domain.
const apiClient = axios.create({
  baseURL: "/api",
  timeout: 90_000, // LLM calls can be slow, especially on local CPU-only Ollama.
});

/**
 * Send code to the backend for AI-powered review.
 *
 * @param {Object} params
 * @param {string} params.code - The raw source code to review.
 * @param {string} [params.language] - Optional language hint (e.g. "python").
 * @param {string} [params.filename] - Optional filename for better language detection.
 * @returns {Promise<Object>} The parsed CodeReviewResponse from the backend.
 * @throws {Error} A human-readable error message extracted from the backend's
 *   error response, or a generic network-error message.
 */
export async function reviewCode({ code, language, filename }) {
  try {
    const response = await apiClient.post("/review", { code, language, filename });
    return response.data;
  } catch (error) {
    // FastAPI returns errors as { detail: "..." }. Surface that message to
    // the UI instead of a generic axios error, so users know exactly what
    // went wrong (e.g. "Ollama is not running").
    const backendMessage = error?.response?.data?.detail;
    throw new Error(backendMessage || "Could not reach the review service. Is the backend running?");
  }
}

/** Check backend health, used to show a connection status indicator. */
export async function checkHealth() {
  const response = await apiClient.get("/health");
  return response.data;
}
