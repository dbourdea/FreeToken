"""Keep deployment identities out of public AMD documentation."""

from pathlib import Path
import re


def test_public_amd_documents_use_anonymous_deployment_examples():
    root = Path(__file__).resolve().parents[2]
    patterns = [
        re.compile(r"\bLAN-\d+\b", re.I),
        re.compile(r"\b192\.168\.\d+\.\d+\b"),
        re.compile(r"/home/(?!operator(?:/|\b)|user(?:/|\b)|username(?:/|\b))[^/\s`]+"),
    ]
    violations = []
    for path in (root / "docs").glob("*.md"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                violations.append(f"{path.name}:{number}")
    assert not violations, "Deployment identity in public docs: " + ", ".join(violations)
