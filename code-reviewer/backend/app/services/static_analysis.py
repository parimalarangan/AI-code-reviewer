"""
static_analysis.py
===================
Runs real, deterministic, open-source static-analysis tools against
submitted code and converts their output into the app's `Finding` schema.

Why combine static analysis WITH an LLM instead of using only one:
    - Static tools (Bandit, Pylint, Radon) are 100% deterministic and catch
      well-known issues (SQL injection patterns, unused imports, cyclomatic
      complexity) with zero hallucination risk.
    - LLMs are better at explaining *why* something is a problem in plain
      English and at spotting logic bugs that no linter rule covers.
    Combining both gives a review that is more trustworthy than either
    alone — this is the same "defense in depth" approach used by real
    production code-review platforms (e.g. GitHub's CodeQL + Copilot).

Supported languages today:
    Python is fully supported (Bandit for security, Pylint for general
    quality, Radon for complexity) because these are free, open-source,
    pip-installable tools with no external service dependency.
    Other languages currently rely on the LLM stage only; the architecture
    (see `run_static_analysis`) makes it straightforward to plug in
    ESLint for JavaScript/TypeScript later without touching any other file.

Safety notes:
    - All analysis runs against a temporary file on disk, never `eval`/`exec`.
    - Every subprocess call has a timeout so a pathological input can't hang
      the server.
    - Temporary files are always cleaned up (try/finally).
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import List

from app.models.schemas import Category, Finding, Severity, StaticAnalysisSummary

_SUBPROCESS_TIMEOUT_SECONDS = 20


def _run_bandit(file_path: Path) -> tuple[list[Finding], StaticAnalysisSummary]:
    """
    Run Bandit (https://github.com/PyCQA/bandit) — an open-source security
    linter for Python — and translate its JSON output into `Finding`s.
    """
    findings: List[Finding] = []
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", str(file_path)],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )
        # Bandit exits with status 1 when it finds issues — that's expected,
        # not an error, so we only guard against completely missing output.
        payload = json.loads(result.stdout or "{}")
        for issue in payload.get("results", []):
            severity_map = {"LOW": Severity.LOW, "MEDIUM": Severity.MEDIUM, "HIGH": Severity.CRITICAL}
            findings.append(
                Finding(
                    line=issue.get("line_number"),
                    category=Category.SECURITY,
                    severity=severity_map.get(issue.get("issue_severity", "LOW"), Severity.LOW),
                    title=issue.get("test_name", "Security issue"),
                    explanation=issue.get("issue_text", "Potential security issue detected."),
                    suggestion=f"See Bandit rule {issue.get('test_id')} for remediation guidance.",
                    source="bandit",
                )
            )
        summary = StaticAnalysisSummary(
            tool="bandit", findings_count=len(findings), raw_output=result.stdout[:2000] if result.stdout else None
        )
    except FileNotFoundError:
        summary = StaticAnalysisSummary(tool="bandit", findings_count=0, raw_output="bandit not installed")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        summary = StaticAnalysisSummary(tool="bandit", findings_count=0, raw_output=f"bandit failed: {exc}")
    return findings, summary


def _run_pylint(file_path: Path) -> tuple[list[Finding], StaticAnalysisSummary]:
    """
    Run Pylint (https://pylint.pycqa.org/) for general Python code-quality
    checks (unused variables, bad naming, missing docstrings, etc.).
    """
    findings: List[Finding] = []
    try:
        result = subprocess.run(
            ["pylint", "--output-format=json", "--disable=C0114,C0116", str(file_path)],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )
        payload = json.loads(result.stdout or "[]")
        type_map = {
            "error": Severity.HIGH,
            "warning": Severity.MEDIUM,
            "convention": Severity.LOW,
            "refactor": Severity.LOW,
        }
        for issue in payload:
            findings.append(
                Finding(
                    line=issue.get("line"),
                    category=Category.BEST_PRACTICE,
                    severity=type_map.get(issue.get("type"), Severity.LOW),
                    title=issue.get("symbol", "Pylint finding"),
                    explanation=issue.get("message", ""),
                    source="pylint",
                )
            )
        summary = StaticAnalysisSummary(
            tool="pylint", findings_count=len(findings), raw_output=result.stdout[:2000] if result.stdout else None
        )
    except FileNotFoundError:
        summary = StaticAnalysisSummary(tool="pylint", findings_count=0, raw_output="pylint not installed")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        summary = StaticAnalysisSummary(tool="pylint", findings_count=0, raw_output=f"pylint failed: {exc}")
    return findings, summary


def _run_radon(file_path: Path) -> tuple[list[Finding], StaticAnalysisSummary]:
    """
    Run Radon (https://radon.readthedocs.io/) to measure cyclomatic
    complexity. Functions/classes with high complexity are flagged as
    maintainability concerns.
    """
    findings: List[Finding] = []
    try:
        result = subprocess.run(
            ["radon", "cc", "-j", str(file_path)],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )
        payload = json.loads(result.stdout or "{}")
        for _, blocks in payload.items():
            for block in blocks:
                rank = block.get("rank", "A")
                if rank in ("D", "E", "F"):  # Radon ranks A (simple) -> F (very complex)
                    findings.append(
                        Finding(
                            line=block.get("lineno"),
                            category=Category.MAINTAINABILITY,
                            severity=Severity.HIGH if rank in ("E", "F") else Severity.MEDIUM,
                            title=f"High cyclomatic complexity in '{block.get('name')}'",
                            explanation=(
                                f"Radon complexity rank '{rank}' (score {block.get('complexity')}). "
                                "Consider breaking this function into smaller pieces."
                            ),
                            source="radon",
                        )
                    )
        summary = StaticAnalysisSummary(
            tool="radon", findings_count=len(findings), raw_output=result.stdout[:2000] if result.stdout else None
        )
    except FileNotFoundError:
        summary = StaticAnalysisSummary(tool="radon", findings_count=0, raw_output="radon not installed")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        summary = StaticAnalysisSummary(tool="radon", findings_count=0, raw_output=f"radon failed: {exc}")
    return findings, summary


def run_static_analysis(code: str, language: str) -> tuple[list[Finding], list[StaticAnalysisSummary]]:
    """
    Entry point used by the orchestrator (`code_analyzer.py`).

    Writes the submitted code to a temporary file and runs every applicable
    static-analysis tool for the detected language, then returns the
    combined findings and per-tool summaries.

    Args:
        code: Raw source code submitted by the user.
        language: Canonical language name from `language_detector.py`.

    Returns:
        A tuple of (all findings from all tools, per-tool summaries).
        Returns empty lists for languages with no configured tools yet
        (the LLM review still runs regardless).
    """
    if language != "python":
        # Static tooling for other languages (e.g. ESLint for JS/TS) can be
        # added here later using the exact same pattern as the functions
        # above, without changing any other part of the app.
        return [], []

    all_findings: List[Finding] = []
    all_summaries: List[StaticAnalysisSummary] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "submission.py"
        file_path.write_text(code, encoding="utf-8")

        for runner in (_run_bandit, _run_pylint, _run_radon):
            findings, summary = runner(file_path)
            all_findings.extend(findings)
            all_summaries.append(summary)

    return all_findings, all_summaries
