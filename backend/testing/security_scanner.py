"""Alt 4: security scanning. Bandit covers Python with real AST-based
rules. For other languages, a small set of conservative regex patterns
catches the same handful of high-signal issues bandit looks for (eval,
shell injection, hardcoded secrets, string-built SQL). These are marked
confidence="LOW" (pattern-match, not AST-verified) so a report reader can
tell them apart from bandit's AST-backed findings — both run on source
text only, never executing target code, so this stays safe on any public repo.

python_backend_security_scan() adds a small set of framework-specific
AST rules bandit doesn't have: insecure default JWT/secret keys, unbounded
password length passed into bcrypt, mutating FastAPI routes with no visible
auth dependency, and SQLite engines missing WAL mode. These were added
after testing against a real FastAPI starter repo, where bandit's generic
rules reported zero findings despite a real empty-string SECRET_KEY default
(i.e. "security scan: OK" was a false negative, not a clean bill of health)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.repository.parser import iter_source_files
from backend.utils.file_utils import safe_read_text


@dataclass
class SecurityIssue:
    file: str
    line: int
    severity: str  # "HIGH" | "MEDIUM" | "LOW"
    confidence: str
    test_id: str
    description: str

    def key(self) -> tuple:
        return (self.file, self.line, self.test_id)


@dataclass
class SecurityReport:
    issues: list[SecurityIssue] = field(default_factory=list)
    high_severity_count: int = 0
    medium_severity_count: int = 0
    ran: bool = True  # False if bandit isn't installed — never block on that

    @property
    def passed(self) -> bool:
        return self.high_severity_count == 0

    def summary(self) -> str:
        if not self.ran:
            return "security scan: skipped (bandit not installed)"
        if not self.issues:
            return "security scan: OK (no issues found)"
        lines = [
            f"security scan: {self.high_severity_count} high, "
            f"{self.medium_severity_count} medium severity issue(s)"
        ]
        for issue in self.issues[:20]:
            lines.append(f"  {issue.file}:{issue.line} [{issue.severity}] {issue.description}")
        if len(self.issues) > 20:
            lines.append(f"  ... and {len(self.issues) - 20} more")
        return "\n".join(lines)


def run_bandit(root: Path) -> SecurityReport:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "--quiet"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return SecurityReport(ran=False)

    if not proc.stdout.strip():
        return SecurityReport(ran=False)

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return SecurityReport(ran=False)

    issues = []
    for result in data.get("results", []):
        issues.append(
            SecurityIssue(
                file=result.get("filename", "").lstrip("./"),
                line=result.get("line_number", 0),
                severity=result.get("issue_severity", "LOW"),
                confidence=result.get("issue_confidence", "LOW"),
                test_id=result.get("test_id", ""),
                description=result.get("issue_text", ""),
            )
        )

    high = sum(1 for i in issues if i.severity == "HIGH")
    medium = sum(1 for i in issues if i.severity == "MEDIUM")
    return SecurityReport(issues=issues, high_severity_count=high, medium_severity_count=medium)


# suffix -> language label, for the small set of applicable rules below
_GENERIC_LANGS = {
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".rb": "ruby", ".php": "php", ".java": "java",
}

# Conservative, high-signal-only patterns. Each: (test_id, severity, regex, description)
_GENERIC_RULES: list[tuple[str, str, "re.Pattern", str]] = [
    (
        "GEN-EVAL",
        "HIGH",
        re.compile(r"\beval\s*\("),
        "Use of eval() on dynamic input — arbitrary code execution risk (CWE-95).",
    ),
    (
        "GEN-SHELL",
        "HIGH",
        re.compile(
            r"\b(shell_exec|system|passthru|exec)\s*\(\s*[\"'].*\$|"
            r"child_process\.(exec|execSync)\s*\(\s*`|"
            r"exec\.Command\s*\(\s*\"sh\"\s*,\s*\"-c\""
        ),
        "Shell command built from interpolated/dynamic input — command injection risk (CWE-78).",
    ),
    (
        "GEN-SECRET",
        "MEDIUM",
        re.compile(
            r"(?i)\b(password|secret|api[_-]?key|token)\b\s*[:=]\s*[\"'][^\"'\s]{4,}[\"']"
        ),
        "Hardcoded credential-looking literal — should come from config/secrets store (CWE-798).",
    ),
    (
        "GEN-SQLI",
        "MEDIUM",
        re.compile(
            r"(?i)(select|insert|update|delete)\b[^\"'\n]{0,80}[\"'][^\"'\n]*"
            r"(\+|\$\{|#\{)"
        ),
        "SQL query built via string concatenation/interpolation — SQL injection risk (CWE-89).",
    ),
]


def generic_security_scan(root: Path) -> list[SecurityIssue]:
    """Pattern-based scan for the common non-Python languages (JS/TS, Go,
    Ruby, PHP, Java). Intentionally small and conservative."""
    issues: list[SecurityIssue] = []
    for path in iter_source_files(root):
        if path.suffix not in _GENERIC_LANGS:
            continue
        rel = str(path.relative_to(root))
        content = safe_read_text(path)
        for lineno, line in enumerate(content.splitlines(), start=1):
            for test_id, severity, pattern, description in _GENERIC_RULES:
                if pattern.search(line):
                    issues.append(
                        SecurityIssue(
                            file=rel,
                            line=lineno,
                            severity=severity,
                            confidence="LOW",  # pattern-match, not AST-verified
                            test_id=test_id,
                            description=description,
                        )
                    )
    return issues


_SECRET_NAME_RE = re.compile(r"(?i)secret|jwt.*key|signing.*key")
_BCRYPT_HASH_CALLS = {"hashpw", "hash", "encrypt"}  # bcrypt.hashpw / passlib .hash / pyca .encrypt
_FASTAPI_MUTATING_METHODS = {"post", "put", "patch", "delete"}


def _is_falsy_default(node: ast.AST) -> bool:
    """A default value that provides no real secret: "", None, or a short
    placeholder-looking literal. Conservative on purpose — only flags
    defaults that clearly can't be a real key, to avoid false positives on
    repos that do set a real (if hardcoded-for-dev) default."""
    if isinstance(node, ast.Constant):
        if node.value in ("", None):
            return True
        if isinstance(node.value, str) and len(node.value) < 8:
            return True
    return False


def _find_insecure_default_secrets(tree: ast.AST, rel: str) -> list[SecurityIssue]:
    """os.getenv("SECRET_KEY", "") / os.environ.get(...) patterns where the
    fallback default is empty or clearly a placeholder — lets the app boot
    with a signing key an attacker can also "guess" (the empty string),
    enabling forged JWTs. Scoped to names that look secret-ish so this
    doesn't fire on unrelated getenv() calls."""
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        is_getenv = (
            (isinstance(func, ast.Attribute) and func.attr in ("getenv", "get"))
            or (isinstance(func, ast.Name) and func.id == "getenv")
        )
        if not is_getenv or len(call.args) < 2:
            continue
        key_arg = call.args[0]
        default_arg = call.args[1]
        target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        key_literal = key_arg.value if isinstance(key_arg, ast.Constant) else ""
        name_hits = any(_SECRET_NAME_RE.search(n) for n in target_names) or (
            isinstance(key_literal, str) and _SECRET_NAME_RE.search(key_literal)
        )
        if name_hits and _is_falsy_default(default_arg):
            issues.append(
                SecurityIssue(
                    file=rel,
                    line=node.lineno,
                    severity="HIGH",
                    confidence="MEDIUM",
                    test_id="FW-INSECURE-SECRET-DEFAULT",
                    description=(
                        "Secret/signing key falls back to an empty or placeholder default "
                        "when the env var is unset — the app can boot with a known/empty key, "
                        "allowing forged tokens (CWE-798)."
                    ),
                )
            )
    return issues


def _find_unbounded_bcrypt_password(tree: ast.AST, rel: str) -> list[SecurityIssue]:
    """bcrypt (and bcrypt-backed passlib contexts) silently truncate or raise
    on inputs over 72 bytes. A function that hashes/verifies a password with
    no length check anywhere in its body is a likely unhandled-500 waiting
    on any sufficiently long input. Heuristic: only fires inside functions
    whose parameter is literally named `password`, and only when neither
    `len(` nor a slice (`[:`) appears anywhere in that function body."""
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        param_names = {a.arg for a in node.args.args if "password" in a.arg.lower()}
        if not param_names:
            continue

        hash_calls = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in _BCRYPT_HASH_CALLS
        ]
        if not hash_calls:
            continue

        body_src = ast.dump(node)
        has_length_guard = "len(" in body_src or "Slice(" in body_src
        if not has_length_guard:
            issues.append(
                SecurityIssue(
                    file=rel,
                    line=node.lineno,
                    severity="MEDIUM",
                    confidence="LOW",
                    test_id="FW-BCRYPT-UNBOUNDED-LENGTH",
                    description=(
                        f"`{node.name}` hashes/verifies a password with no visible length check — "
                        "bcrypt rejects/truncates inputs over 72 bytes, which can surface as an "
                        "unhandled 500 instead of a clean validation error."
                    ),
                )
            )
    return issues


def _find_unprotected_mutating_routes(tree: ast.AST, rel: str) -> list[SecurityIssue]:
    """FastAPI routes that mutate data (POST/PUT/PATCH/DELETE) but declare no
    `Depends(...)` anywhere in their parameters — a likely missing auth
    dependency. Low-confidence heuristic (a route could be intentionally
    public, e.g. signup/login), so this is reported at MEDIUM/LOW, not HIGH."""
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        route_decorators = [
            d for d in node.decorator_list
            if isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr in _FASTAPI_MUTATING_METHODS
        ]
        if not route_decorators:
            continue

        defaults = node.args.defaults + node.args.kw_defaults
        has_depends = any(
            isinstance(default, ast.Call)
            and (
                (isinstance(default.func, ast.Name) and default.func.id == "Depends")
                or (isinstance(default.func, ast.Attribute) and default.func.attr == "Depends")
            )
            for default in defaults
            if default is not None
        )
        if not has_depends:
            issues.append(
                SecurityIssue(
                    file=rel,
                    line=node.lineno,
                    severity="MEDIUM",
                    confidence="LOW",
                    test_id="FW-ROUTE-NO-AUTH-DEP",
                    description=(
                        f"`{node.name}` is a data-mutating route ({route_decorators[0].func.attr.upper()}) "
                        "with no `Depends(...)` in its parameters — confirm this is intentionally public "
                        "(e.g. signup/login); otherwise it's likely missing an auth dependency."
                    ),
                )
            )
    return issues


def _find_sqlite_without_wal(tree: ast.AST, rel: str, source: str) -> list[SecurityIssue]:
    """SQLAlchemy create_engine() pointed at a sqlite file with no WAL-mode
    PRAGMA anywhere in the file — under concurrent writers, SQLite's default
    rollback-journal mode serializes writers and can raise "database is
    locked" under load that WAL mode avoids."""
    issues = []
    has_wal_pragma = "journal_mode" in source and "WAL" in source.upper()
    if has_wal_pragma:
        return issues
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "create_engine"
        ):
            continue
        url_arg = node.args[0] if node.args else None
        url_literal = url_arg.value if isinstance(url_arg, ast.Constant) else ""
        if isinstance(url_literal, str) and "sqlite" in url_literal.lower():
            issues.append(
                SecurityIssue(
                    file=rel,
                    line=node.lineno,
                    severity="LOW",
                    confidence="LOW",
                    test_id="FW-SQLITE-NO-WAL",
                    description=(
                        "SQLite engine created without enabling WAL mode "
                        "(`PRAGMA journal_mode=WAL`) — concurrent writes may hit "
                        "'database is locked' under load."
                    ),
                )
            )
    return issues


def python_backend_security_scan(root: Path) -> list[SecurityIssue]:
    """Framework-aware AST rules layered on top of bandit's generic ones.
    Each file is parsed once; a file that fails to parse is skipped (the
    static analyzer already reports syntax errors separately)."""
    issues: list[SecurityIssue] = []
    for path in iter_source_files(root):
        if path.suffix != ".py":
            continue
        rel = str(path.relative_to(root))
        source = safe_read_text(path)
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        issues.extend(_find_insecure_default_secrets(tree, rel))
        issues.extend(_find_unbounded_bcrypt_password(tree, rel))
        issues.extend(_find_unprotected_mutating_routes(tree, rel))
        issues.extend(_find_sqlite_without_wal(tree, rel, source))
    return issues


def run_security_scan(root: Path) -> SecurityReport:
    root = Path(root)
    bandit_report = run_bandit(root)
    generic_issues = generic_security_scan(root)
    framework_issues = python_backend_security_scan(root)

    all_issues = list(bandit_report.issues) + generic_issues + framework_issues
    high = sum(1 for i in all_issues if i.severity == "HIGH")
    medium = sum(1 for i in all_issues if i.severity == "MEDIUM")

    return SecurityReport(
        issues=all_issues,
        high_severity_count=high,
        medium_severity_count=medium,
        # The generic pattern scan and framework-aware AST rules have no
        # external dependency, so the combined scan always produces a real
        # result even if bandit itself was skipped (not installed, or a
        # non-Python repo).
        ran=True,
    )
