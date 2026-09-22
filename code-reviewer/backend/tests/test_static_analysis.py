"""
test_static_analysis.py
========================
Unit tests for the static-analysis integration. These tests require the
real `bandit`, `pylint`, and `radon` binaries to be installed (they are,
per requirements.txt) — no mocking needed since these tools are fast,
deterministic, and free.
"""

from app.services.static_analysis import run_static_analysis


def test_bandit_flags_hardcoded_password():
    code = 'password = "hardcoded123"\nprint(password)\n'
    findings, summaries = run_static_analysis(code, "python")
    tool_names = {s.tool for s in summaries}
    assert "bandit" in tool_names
    # Bandit should flag hardcoded credentials as a security finding.
    assert any(f.category.value == "security" for f in findings)


def test_non_python_language_returns_empty():
    findings, summaries = run_static_analysis("console.log('hi')", "javascript")
    assert findings == []
    assert summaries == []


def test_clean_code_has_few_or_no_bandit_findings():
    code = "def add(a: int, b: int) -> int:\n    \"\"\"Add two numbers.\"\"\"\n    return a + b\n"
    findings, _ = run_static_analysis(code, "python")
    security_findings = [f for f in findings if f.category.value == "security"]
    assert security_findings == []
