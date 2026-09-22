"""
language_detector.py
=====================
Best-effort programming-language detection.

Why we need this:
    The LLM prompt and the static-analysis step both need to know which
    language they are dealing with. The frontend usually tells us (because
    Monaco Editor already knows), but we still want a safe fallback for:
      - API calls made directly (curl, Postman, another app) without a
        language hint.
      - Defensive programming: never trust client input blindly.

How it works:
    1. If a filename with a recognisable extension is provided, trust it.
    2. Otherwise, run a small set of cheap keyword/regex heuristics over the
       source text. This is intentionally simple (no heavy ML dependency)
       so the whole project stays lightweight and free to run anywhere.
"""

import re
from pathlib import Path
from typing import Optional

# Map of file extensions -> canonical language name used throughout the app.
_EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rs": "rust",
    ".kt": "kotlin",
    ".swift": "swift",
}

# Ordered list of (regex, language) heuristics. Order matters: more specific
# / less ambiguous patterns should come first.
_HEURISTICS = [
    (re.compile(r"^\s*def\s+\w+\(.*\):", re.MULTILINE), "python"),
    (re.compile(r"^\s*import\s+\w+|from\s+\w+\s+import", re.MULTILINE), "python"),
    (re.compile(r"\bfunction\s+\w+\s*\(|=>\s*{"), "javascript"),
    (re.compile(r"\binterface\s+\w+\s*{|:\s*(string|number|boolean)\b"), "typescript"),
    (re.compile(r"\bpublic\s+static\s+void\s+main\s*\("), "java"),
    (re.compile(r"^\s*package\s+main|func\s+\w+\("), "go"),
    (re.compile(r"#include\s*<.*>"), "c"),
    (re.compile(r"\bnamespace\s+\w+|using\s+System;"), "csharp"),
    (re.compile(r"\bfn\s+\w+\(.*\)\s*(->\s*\w+)?\s*{"), "rust"),
]


def detect_language(code: str, filename: Optional[str] = None, hint: Optional[str] = None) -> str:
    """
    Determine the most likely programming language for a code snippet.

    Priority order:
        1. Explicit `hint` supplied by the caller (e.g. Monaco editor's
           active language mode) — trusted first because it's the most
           reliable signal.
        2. File extension from `filename`, if provided.
        3. Regex/keyword heuristics run against `code`.
        4. Fallback to "plaintext" if nothing matches.

    Args:
        code: The raw source code.
        filename: Optional filename (used only for its extension).
        hint: Optional language name already known by the caller.

    Returns:
        A lowercase, canonical language name (e.g. "python", "javascript").
    """
    if hint:
        return hint.strip().lower()

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _EXTENSION_MAP:
            return _EXTENSION_MAP[ext]

    for pattern, language in _HEURISTICS:
        if pattern.search(code):
            return language

    return "plaintext"
