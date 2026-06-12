#!/usr/bin/env python3
"""test_integrity_diff.py — conservative assertion-weakening detector.

Diffs TEST FILES between a base revision and HEAD, flagging four finding classes:
  REMOVED_ASSERTION  — deleted lines matching assert/expect/require patterns
  WIDENED_MATCHER    — changed line pairs that appear to relax a matcher
  ADDED_SKIP         — added skip/conditional-guard decorators inside test bodies
  DELETED_TEST_FILE  — entire test file removed

CLI:
  python3 test_integrity_diff.py [--repo <path>] [--base <rev>] [--advisory]

  --repo PATH    repo root (default: .)
  --base REV     base revision to diff against (default: merge-base with origin/main
                 or main; fallback HEAD~1)
  --advisory     always exit 0 even when findings exist (for validate wiring)

Output:
  One line per finding: CLASS<TAB>file<TAB>detail
  A summary line at the end.
  Exit 1 iff >=1 finding (unless --advisory).

Test-file patterns (closed list):
  Directories:  tests/, test/, __tests__/, spec/, __spec__/
  Filename:     test_*.py, *_test.py, *_test.js, *_test.ts,
                *.test.js, *.test.ts, *.test.jsx, *.test.tsx,
                *.spec.js, *.spec.ts, *.spec.jsx, *.spec.tsx,
                *_test.rb, *_spec.rb
"""
import argparse
import re
import subprocess
import sys
from pathlib import PurePosixPath

# ---------------------------------------------------------------------------
# Test-file pattern matching
# ---------------------------------------------------------------------------

# Closed list of directory-component patterns (any path component == one of these)
_TEST_DIRS = {"tests", "test", "__tests__", "spec", "__spec__"}

# Closed list of filename glob-style patterns expressed as regexes
_TEST_FILENAME_RE = re.compile(
    r"(?:"
    r"test_[^/]+\.py$"           # test_*.py
    r"|[^/]+_test\.py$"          # *_test.py
    r"|[^/]+_test\.[jt]sx?$"     # *_test.{js,ts,jsx,tsx}
    r"|[^/]+\.test\.[jt]sx?$"    # *.test.{js,ts,jsx,tsx}
    r"|[^/]+\.spec\.[jt]sx?$"    # *.spec.{js,ts,jsx,tsx}
    r"|[^/]+_test\.rb$"          # *_test.rb
    r"|[^/]+_spec\.rb$"          # *_spec.rb
    r")"
)


def is_test_file(path: str) -> bool:
    """Return True if path looks like a test file per the closed list above."""
    parts = PurePosixPath(path).parts
    # Directory component match
    for part in parts[:-1]:
        if part in _TEST_DIRS:
            return True
    # Filename match
    name = parts[-1] if parts else ""
    return bool(_TEST_FILENAME_RE.search(name))


# ---------------------------------------------------------------------------
# Assertion / skip patterns (per language family, conservative)
# ---------------------------------------------------------------------------

# Python assertions — match lines that clearly assert something
_PY_ASSERT_RE = re.compile(
    r"(?:"
    r"\bassert\s"              # bare assert statement
    r"|self\.assert\w+"        # unittest self.assertX
    r"|pytest\.raises\s*\("    # pytest.raises(
    r")"
)

# JavaScript / TypeScript assertions
_JS_ASSERT_RE = re.compile(
    r"(?:"
    r"expect\s*\("             # expect(
    r"|assert\."               # assert.X
    r")"
)

# Shell assertions (conservative: only the pattern that exits on failure)
_SH_ASSERT_RE = re.compile(
    r"\[\[.*\]\]\s*\|\|\s*exit"
)

# Combined — used for removed-assertion detection
def _is_assertion_line(line: str, filepath: str) -> bool:
    ext = PurePosixPath(filepath).suffix.lower()
    if ext == ".py":
        return bool(_PY_ASSERT_RE.search(line))
    if ext in (".js", ".ts", ".jsx", ".tsx"):
        return bool(_JS_ASSERT_RE.search(line))
    if ext == ".sh":
        return bool(_SH_ASSERT_RE.search(line))
    # For unknown extensions, try all patterns (conservative fallback)
    return bool(
        _PY_ASSERT_RE.search(line)
        or _JS_ASSERT_RE.search(line)
        or _SH_ASSERT_RE.search(line)
    )


# ---------------------------------------------------------------------------
# Widened-matcher patterns
# Conservative: only flag clear loosening of specific matchers.
# Pairs: (tight_pattern, loose_pattern) — both must appear in the same hunk
# on removed vs added sides respectively.
# ---------------------------------------------------------------------------

# Python widening: assertEqual -> assertIn, assertEqual -> assertTrue,
#                  == (comparison) -> in (membership on changed pair)
_PY_WIDENED_PAIRS = [
    (re.compile(r"\bassertEqual\b"), re.compile(r"\bassertIn\b")),
    (re.compile(r"\bassertEqual\b"), re.compile(r"\bassertTrue\b")),
    (re.compile(r"\bassertIs\b"), re.compile(r"\bassertIsInstance\b")),
]

# JS/TS widening: .toBe( -> .toBeTruthy() / .toBeFalsy() / .toBeDefined()
_JS_WIDENED_PAIRS = [
    (re.compile(r"\.toBe\s*\("), re.compile(r"\.toBeTruthy\s*\(")),
    (re.compile(r"\.toBe\s*\("), re.compile(r"\.toBeFalsy\s*\(")),
    (re.compile(r"\.toBe\s*\("), re.compile(r"\.toBeDefined\s*\(")),
    (re.compile(r"\.toEqual\s*\("), re.compile(r"\.toBeTruthy\s*\(")),
    (re.compile(r"\.toStrictEqual\s*\("), re.compile(r"\.toEqual\s*\(")),
]


def _check_widened_matcher(removed_lines: list, added_lines: list, filepath: str) -> list:
    """Return list of detail strings for widened-matcher findings in a hunk."""
    ext = PurePosixPath(filepath).suffix.lower()
    findings = []
    removed_text = " ".join(removed_lines)
    added_text = " ".join(added_lines)
    if ext == ".py":
        for tight_re, loose_re in _PY_WIDENED_PAIRS:
            if tight_re.search(removed_text) and loose_re.search(added_text):
                findings.append(
                    f"{tight_re.pattern} -> {loose_re.pattern}"
                )
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        for tight_re, loose_re in _JS_WIDENED_PAIRS:
            if tight_re.search(removed_text) and loose_re.search(added_text):
                findings.append(
                    f"{tight_re.pattern} -> {loose_re.pattern}"
                )
    return findings


# ---------------------------------------------------------------------------
# Skip / conditional guard patterns
# ---------------------------------------------------------------------------

_SKIP_RE = re.compile(
    r"(?:"
    r"@pytest\.mark\.skip"      # @pytest.mark.skip
    r"|@pytest\.mark\.skipif"   # @pytest.mark.skipif
    r"|@unittest\.skip"         # @unittest.skip
    r"|unittest\.skip\s*\("     # unittest.skip(
    r"|it\.skip\s*\("           # it.skip(
    r"|xit\s*\("                # xit(
    r"|xdescribe\s*\("          # xdescribe(
    r"|test\.skip\s*\("         # test.skip(
    r"|describe\.skip\s*\("     # describe.skip(
    r")"
)

# Conservative: only flag os.environ.get guard at the start of a test function
# (the line immediately follows a def test_ line in the added context).
_ENV_GUARD_RE = re.compile(
    r"if\s+os\.environ\.get\s*\(.*\)\s*:"
)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(args: list, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def resolve_base(repo: str, base_arg: str | None) -> str:
    """Resolve the base revision to diff against."""
    if base_arg:
        return base_arg
    # Try merge-base with origin/main
    for ref in ("origin/main", "main"):
        r = _git(["merge-base", "HEAD", ref], repo)
        if r.returncode == 0:
            return r.stdout.strip()
    # Fallback: HEAD~1
    r = _git(["rev-parse", "HEAD~1"], repo)
    if r.returncode == 0:
        return r.stdout.strip()
    # Truly empty / single-commit repo: diff against empty tree
    return "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def get_diff(repo: str, base: str) -> str:
    """Return the unified diff between base and HEAD for test files."""
    r = _git(["diff", base, "HEAD", "--", "."], repo)
    if r.returncode != 0:
        # Try staged+working-tree diff as fallback (bare/no-commit-yet repos)
        r = _git(["diff", base, "--", "."], repo)
    return r.stdout


def get_deleted_files(repo: str, base: str) -> list:
    """Return list of test files deleted between base and HEAD."""
    r = _git(["diff", "--name-status", base, "HEAD", "--", "."], repo)
    deleted = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0].startswith("D"):
            if is_test_file(parts[1]):
                deleted.append(parts[1])
    return deleted


# ---------------------------------------------------------------------------
# Diff parser
# ---------------------------------------------------------------------------

def parse_diff(diff_text: str):
    """Yield (filepath, hunks) where hunks = list of (removed_lines, added_lines)."""
    current_file = None
    current_removed = []
    current_added = []
    hunks = []

    def _flush_hunk():
        if current_removed or current_added:
            hunks.append((list(current_removed), list(current_added)))
        current_removed.clear()
        current_added.clear()

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_file is not None:
                _flush_hunk()
                yield current_file, list(hunks)
            # Extract b/ filename
            m = re.search(r" b/(.+)$", line)
            current_file = m.group(1) if m else None
            hunks = []
            current_removed.clear()
            current_added.clear()
        elif line.startswith("--- ") or line.startswith("+++ "):
            continue
        elif line.startswith("@@ "):
            _flush_hunk()
        elif line.startswith("-") and not line.startswith("---"):
            current_removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            current_added.append(line[1:])
        # context lines ignored

    if current_file is not None:
        _flush_hunk()
        yield current_file, list(hunks)


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

Finding = tuple  # (class_str, filepath, detail)


def analyze(repo: str, base: str) -> list:
    """Return list of Finding tuples."""
    findings: list[Finding] = []

    diff_text = get_diff(repo, base)
    deleted = get_deleted_files(repo, base)

    # DELETED_TEST_FILE findings
    for fp in deleted:
        findings.append(("DELETED_TEST_FILE", fp, "test file deleted"))

    # Parse diff for per-hunk analysis
    for filepath, hunks in parse_diff(diff_text):
        if not is_test_file(filepath):
            continue

        for removed_lines, added_lines in hunks:
            # (a) REMOVED_ASSERTION
            for line in removed_lines:
                stripped = line.strip()
                if stripped and _is_assertion_line(stripped, filepath):
                    findings.append((
                        "REMOVED_ASSERTION",
                        filepath,
                        f"removed: {stripped[:120]}"
                    ))

            # (b) WIDENED_MATCHER
            for detail in _check_widened_matcher(removed_lines, added_lines, filepath):
                findings.append(("WIDENED_MATCHER", filepath, detail))

            # (c) ADDED_SKIP
            # Track whether we are in a block that just added a skip
            prev_was_def_test = False
            for line in added_lines:
                stripped = line.strip()
                if _SKIP_RE.search(stripped):
                    findings.append((
                        "ADDED_SKIP",
                        filepath,
                        f"added: {stripped[:120]}"
                    ))
                # os.environ.get guard — only flag if immediately following def test_
                if prev_was_def_test and _ENV_GUARD_RE.search(stripped):
                    findings.append((
                        "ADDED_SKIP",
                        filepath,
                        f"added env-guard after test def: {stripped[:120]}"
                    ))
                prev_was_def_test = bool(re.match(r"def\s+test_", stripped))

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for f in findings:
        key = f
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    return deduped


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Conservative test-integrity diff detector."
    )
    parser.add_argument("--repo", default=".", help="repo root (default: .)")
    parser.add_argument(
        "--base",
        default=None,
        help="base revision (default: merge-base with origin/main or main, fallback HEAD~1)",
    )
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="always exit 0 even when findings exist",
    )
    args = parser.parse_args()

    repo = str(args.repo)
    base = resolve_base(repo, args.base)
    findings = analyze(repo, base)

    for cls, fp, detail in findings:
        print(f"{cls}\t{fp}\t{detail}")

    count = len(findings)
    print(f"test-integrity: {count} finding(s) against base {base[:12]}")

    if count > 0 and not args.advisory:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
