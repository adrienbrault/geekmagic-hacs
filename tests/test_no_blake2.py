"""No code in the integration may use BLAKE2 (issue #262).

CPython 3.14's ``hashlib.blake2b``/``blake2s`` choose their AVX2 code from
the CPUID feature bits alone, without checking that the OS enabled AVX
(OSXSAVE/XGETBV). A hypervisor that advertises AVX2 but hides XSAVE
(seen on Synology Virtual Machine Manager) runs that code and gets
SIGILL: Home Assistant dies with no traceback. The frame push key used
it; byte comparison or OpenSSL-backed digests (``hashlib.sha256``) are
safe.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "custom_components" / "geekmagic"
FORBIDDEN = {"blake2b", "blake2s"}


def _uses(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN:
            found.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            found.update(alias.name for alias in node.names if alias.name in FORBIDDEN)
        elif isinstance(node, ast.Constant) and node.value in FORBIDDEN:
            found.add(node.value)  # hashlib.new("blake2b")
    return found


def test_no_module_uses_blake2() -> None:
    offenders = {
        str(path.relative_to(PACKAGE)): sorted(uses)
        for path in sorted(PACKAGE.rglob("*.py"))
        if (uses := _uses(ast.parse(path.read_text(encoding="utf-8"))))
    }
    assert not offenders, f"BLAKE2 can SIGILL Home Assistant (issue #262): {offenders}"


def test_the_check_sees_each_way_to_reach_blake2() -> None:
    for source in (
        "import hashlib\nhashlib.blake2b(b'')",
        "from hashlib import blake2s",
        "import hashlib\nhashlib.new('blake2b')",
    ):
        assert _uses(ast.parse(source)), source
