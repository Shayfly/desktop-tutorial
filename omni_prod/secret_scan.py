from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

@dataclass(frozen=True)
class SecretFinding:
    kind: str
    path: str
    line: int
    preview: str

_PLACEHOLDER_WORDS = {
    "change_me", "changeme", "example", "example_key", "example_secret",
    "your_key", "your_secret", "test", "dummy", "placeholder"
}

_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer_token", re.compile(r"Authorization\s*:\s*Bearer\s+([A-Za-z0-9._~+/=-]{16,})", re.I)),
    ("url_password", re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^:\s/]+:([^@\s/]{8,})@", re.I)),
]

_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"]?([A-Za-z0-9._~+/=-]{16,})"
)

def _looks_placeholder(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if normalized in _PLACEHOLDER_WORDS:
        return True
    if normalized.startswith("change_me") or normalized.startswith("your_"):
        return True
    return False

def _looks_runtime_generated_expression(line: str, match: re.Match[str]) -> bool:
    """Return True when an assignment match is a runtime-generated callable.

    The assignment scanner intentionally accepts unquoted tokens so hard-coded
    credential assignments are detected. A dotted callable followed immediately
    by parentheses is code that generates a value at runtime, not a credential
    literal embedded in the source file.
    """
    value = match.group(2)
    remainder = line[match.end(2):].lstrip()
    return bool(
        remainder.startswith("(")
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", value)
    )

_WORKFLOW_PATH = re.compile(r"(?:^|/)\.github/workflows/[^/]+\.ya?ml$")
# A YAML env/service mapping entry whose whole value is a loopback database URL
# carrying an explicit CI-fixture password ("ci-..."). Not a run script, not a
# remote host, not any other secret kind.
_CI_SERVICE_URL = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_]*:\s*['\"]?"
    r"(?:postgres(?:ql)?|mysql|mongodb)://[^:\s/@]+:ci-[A-Za-z0-9_.-]+@(?:127\.0\.0\.1|localhost)(?::\d+)?/[^\s'\"]*['\"]?\s*$",
    re.I,
)

def _is_ci_service_credential(kind: str, path: str, line: str) -> bool:
    return (
        kind == "url_password"
        and bool(_WORKFLOW_PATH.search(path.replace("\\", "/")))
        and bool(_CI_SERVICE_URL.match(line))
    )

def scan_text(text: str, *, path: str = "<memory>") -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        for kind, pattern in _PATTERNS:
            m = pattern.search(line)
            if m:
                value = m.group(1) if m.groups() else m.group(0)
                if not _looks_placeholder(value) and not _is_ci_service_credential(kind, path, line):
                    findings.append(SecretFinding(kind, path, idx, line[:160]))
        m = _ASSIGNMENT.search(line)
        if m and not _looks_runtime_generated_expression(line, m) and not _looks_placeholder(m.group(2)):
            findings.append(SecretFinding("credential_assignment", path, idx, line[:160]))
    # de-duplicate same line/kind
    unique = {}
    for f in findings:
        unique[(f.kind, f.path, f.line)] = f
    return list(unique.values())

def scan_tree(
    root: str | Path,
    *,
    include_suffixes: tuple[str, ...] = (".py", ".yml", ".yaml", ".json", ".toml", ".ini", ".env"),
    excluded_parts: tuple[str, ...] = ("tests", "__pycache__", ".git"),
) -> list[SecretFinding]:
    base = Path(root)
    out: list[SecretFinding] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded_parts for part in path.parts):
            continue
        if path.name == ".env.example":
            # Example config is permitted only because placeholders are expected there.
            pass
        elif path.suffix.lower() not in include_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        out.extend(scan_text(text, path=str(path.relative_to(base))))
    return out
