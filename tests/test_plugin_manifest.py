"""The repository is a Claude plugin marketplace whose one plugin is the repository itself.

``.claude-plugin/marketplace.json`` lists the plugin with ``"source": "./"``,
so installing it copies the whole repository, integration included: the
``geekmagic-views`` skill's renderer finds ``custom_components/geekmagic``
by walking up from itself. These tests keep that installable on Claude Code
and on claude.ai, whose limits are stricter.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
PLUGIN_DIR = REPO_ROOT / ".claude-plugin"
MARKETPLACE = json.loads((PLUGIN_DIR / "marketplace.json").read_text(encoding="utf-8"))
PLUGIN = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
MANIFEST = json.loads(
    (REPO_ROOT / "custom_components" / "geekmagic" / "manifest.json").read_text(encoding="utf-8")
)
RENDER_VIEW = REPO_ROOT / "skills" / "geekmagic-views" / "scripts" / "render_view.py"
SKILL_MD = REPO_ROOT / "skills" / "geekmagic-views" / "SKILL.md"

NAME = "geekmagic-hacs"
# claude.ai refuses a plugin over these (Customize > Plugins)
CLAUDE_AI_MAX_FILES = 5000
CLAUDE_AI_MAX_BYTES = 200 * 1024 * 1024


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607 - git from PATH, as the dev workflow
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [REPO_ROOT / name for name in out.decode().split("\0") if name]


def _script_constant(name: str) -> str:
    match = re.search(
        rf'^{name} = "([^"]+)"$', RENDER_VIEW.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert match is not None, f"{name} not found in {RENDER_VIEW}"
    return match[1]


def test_versions_are_the_integration_release():
    """plugin.json, the renderer's download tag and manifest.json move together.

    A release bumps all three (CLAUDE.md, Release Process): Claude Code
    updates an installed plugin only when its version changes, and the
    renderer downloads the release tagged INTEGRATION_VERSION when it runs
    without the repository around it.
    """
    assert PLUGIN["version"] == MANIFEST["version"]
    assert _script_constant("INTEGRATION_VERSION") == MANIFEST["version"]


def test_marketplace_lists_the_repository_as_its_plugin():
    assert MARKETPLACE["name"] == NAME
    assert MARKETPLACE["owner"]["name"]
    [entry] = MARKETPLACE["plugins"]
    assert entry["name"] == NAME
    assert entry["source"] == "./"
    # plugin.json is the one place the version lives (it wins anyway)
    assert "version" not in entry
    assert PLUGIN["name"] == NAME


def test_plugin_paths_exist():
    icon = PLUGIN.get("icon")
    assert icon is None or (REPO_ROOT / icon).is_file()


def test_no_top_level_bin_directory():
    """claude.ai and Cowork refuse to install a plugin with a top-level ``bin/``."""
    assert not (REPO_ROOT / "bin").exists()


def test_skill_frontmatter():
    """``name`` and ``description`` within the limits claude.ai enforces on skills."""
    match = re.match(r"---\n(.*?)\n---\n", SKILL_MD.read_text(encoding="utf-8"), re.DOTALL)
    assert match is not None, "SKILL.md starts with a --- frontmatter block"
    meta = yaml.safe_load(match[1])
    assert meta["name"] == SKILL_MD.parent.name
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    description = meta["description"]
    assert isinstance(description, str)
    assert 0 < len(description) <= 1024
    assert not re.search(r"[<>]", meta["name"] + description)
    assert "GeekMagic" in description


def test_skill_references_exist():
    """Every path SKILL.md names (relative to its folder) is in the repository.

    The docs and the HTML gallery are referenced in place, not copied, so a
    move there must update the skill.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    refs = set(re.findall(r"`((?:\.\./)+[^`\s]+|(?:scripts|examples|demo)/[^`\s]+)`", text))
    for required in (
        "scripts/render_view.py",
        "demo/home.json",
        "../../docs/html-widget.md",
        "../../docs/widgets.md",
        "../../docs/layouts.md",
        "../../scripts/html_examples/*.html",
    ):
        assert required in refs
    for ref in refs:
        if "*" in ref:
            assert list(SKILL_MD.parent.glob(ref)), f"SKILL.md: {ref} matches nothing"
        else:
            assert (SKILL_MD.parent / ref).exists(), f"SKILL.md: {ref} does not exist"


def test_within_claude_ai_plugin_limits():
    """claude.ai takes at most 5,000 files and 200 MB per plugin."""
    files = _tracked_files()
    assert len(files) < CLAUDE_AI_MAX_FILES
    assert sum(path.stat().st_size for path in files if path.is_file()) < CLAUDE_AI_MAX_BYTES
