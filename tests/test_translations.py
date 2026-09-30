"""The English translation Home Assistant actually loads covers every flow step.

Custom integrations are translated from ``translations/en.json`` —
``strings.json`` is only the source. A step or error key missing from
en.json renders as its raw key in the UI.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

COMPONENT = Path(__file__).parent.parent / "custom_components" / "geekmagic"


def _flow_keys(class_name: str) -> tuple[set[str], set[str]]:
    """``step_id`` and ``errors["base"]`` literals used by a flow class."""
    tree = ast.parse((COMPONENT / "config_flow.py").read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    steps: set[str] = set()
    errors: set[str] = set()
    for node in ast.walk(cls):
        if (
            isinstance(node, ast.keyword)
            and node.arg == "step_id"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            steps.add(node.value.value)
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and any(
                isinstance(t, ast.Subscript)
                and isinstance(t.value, ast.Name)
                and t.value.id == "errors"
                for t in node.targets
            )
        ):
            errors.add(node.value.value)
    return steps, errors


def _check(section: str, class_name: str) -> None:
    en = json.loads((COMPONENT / "translations" / "en.json").read_text())[section]
    source = json.loads((COMPONENT / "strings.json").read_text())[section]
    steps, errors = _flow_keys(class_name)
    assert steps, class_name
    for step in steps:
        assert step in en["step"], f"en.json {section}.step.{step} missing"
        assert en["step"][step] == source["step"][step], f"{section}.step.{step} out of sync"
    for error in errors:
        assert error in en.get("error", {}), f"en.json {section}.error.{error} missing"


def test_config_flow_translations_present() -> None:
    _check("config", "GeekMagicConfigFlow")


def test_options_flow_translations_present() -> None:
    _check("options", "GeekMagicOptionsFlow")
