"""`lab init` — activate an instance: plan first, never overwrite (design ADR-7, ADR-8).

Pattern of Copier (E-13, no dependency): the whole plan is computed first, each file is
classified ``create`` / ``identical`` / ``skip`` (never ``overwrite``), one line per file is
printed, then the plan is applied unless ``--dry-run``. A second run is ``0 changement``.

Writes ONLY data (INV-8): ``.lab/lab.toml``, ``work/`` (README + triplet templates) and the
``evals`` / ``evals-collect`` justfile recipes. Nothing under ``.claude/``, no CLAUDE.md /
AGENTS.md, no CI workflow.

Also exposes :func:`read_lab_toml`, the explicit reader of ``.lab/lab.toml`` reused by the
run pre-flight (not the silent-empty pattern of registry.py:55-56).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import kit_root, kit_version  # noqa: E402

PROFILES = ("solo", "squad", "regulated")
SCHEMA_VERSION = 1
RECIPES = ("evals", "evals-collect")
LAB_TOML = Path(".lab") / "lab.toml"

# work/<dest> ← lab/templates/<src> (never named spec.md / design.md / tasks.md — OQ-10)
WORK_TEMPLATES = {
    "work/_templates/spec.template.md": "spec.md",
    "work/_templates/design.template.md": "design.md",
    "work/_templates/tasks.template.md": "tasks.md",
}


class InitError(Exception):
    """Fatal problem: the command ends rc 1, nothing (more) is written."""


class LabTomlError(InitError):
    """`.lab/lab.toml` missing or invalid."""


# ---- .lab/lab.toml ---------------------------------------------------------


def render_lab_toml(profile: str, version: str) -> str:
    return (
        f"schema_version = {SCHEMA_VERSION}\n"
        f'kit_version = "{version}"   # exact pin (INV-7), checked against the installed kit\n'
        f'profile = "{profile}"       # solo | squad | regulated\n'
    )


def read_lab_toml(project: Path) -> dict:
    """Read and validate ``<project>/.lab/lab.toml``; raise :class:`LabTomlError` otherwise."""
    path = Path(project) / LAB_TOML
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise LabTomlError(
            f"{path} not found — run `lab init <project> --profile <p>` first"
        ) from None
    except OSError as e:
        raise LabTomlError(f"cannot read {path}: {e}") from None
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as e:
        raise LabTomlError(f"{path} is not valid TOML: {e}") from None
    if data.get("schema_version") != SCHEMA_VERSION:
        raise LabTomlError(
            f"{path}: unsupported schema_version {data.get('schema_version')!r} "
            f"(expected {SCHEMA_VERSION})"
        )
    kv = data.get("kit_version")
    if not isinstance(kv, str) or not kv:
        raise LabTomlError(f"{path}: kit_version must be a non-empty string")
    if data.get("profile") not in PROFILES:
        raise LabTomlError(
            f"{path}: profile {data.get('profile')!r} not in {', '.join(PROFILES)}"
        )
    return data


# ---- justfile (ADR-8) ------------------------------------------------------


def just_recipes(justfile: Path) -> set[str]:
    """Names (recipes + aliases) defined by an explicit justfile.

    ``--justfile`` makes just read exactly this file (no walk up to a parent justfile);
    a parse error raises :class:`InitError`.
    """
    try:
        p = subprocess.run(
            ["just", "--justfile", str(justfile), "--dump", "--dump-format", "json"],
            capture_output=True,
            text=True,
        )
    except OSError as e:
        raise InitError(f"cannot run `just` to read {justfile}: {e}") from None
    if p.returncode != 0:
        raise InitError(
            f"{justfile} does not parse (just rc {p.returncode}) — nothing written:\n"
            f"{p.stderr.strip()}"
        )
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise InitError(
            f"unreadable `just --dump` output for {justfile}: {e}"
        ) from None
    return set(data.get("recipes", {})) | set(data.get("aliases", {}))


def _snippet(kind: str, recipe: str) -> str:
    path = (
        kit_root(honor_env=False)
        / "lab"
        / "templates"
        / "instance"
        / f"{recipe}.{kind}.just"
    )
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        raise InitError(f"kit template missing: {path} ({e})") from None


def _template(name: str) -> str:
    path = kit_root(honor_env=False) / "lab" / "templates" / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        raise InitError(f"kit template missing: {path} ({e})") from None


# ---- plan ------------------------------------------------------------------


@dataclass
class Item:
    action: str  # create | identical | skip
    label: str  # shown path (file, or justfile#recipe)
    path: Path | None = None  # file to create (whole-file items)
    content: str = ""
    recipe: str = ""  # justfile#recipe items: snippet to append
    note: str = ""


def _file_item(project: Path, rel: str, content: str) -> Item:
    dest = project / rel
    if not dest.exists():
        return Item("create", rel, dest, content)
    try:
        same = dest.read_text(encoding="utf-8") == content
    except (OSError, UnicodeDecodeError):
        same = False
    if same:
        return Item("identical", rel)
    return Item("skip", rel, note="exists, left as is")


def build_plan(project: Path, profile: str) -> list[Item]:
    version = kit_version()
    items = [
        _file_item(project, LAB_TOML.as_posix(), render_lab_toml(profile, version))
    ]
    readme = _template("instance/work-README.md")
    items.append(_file_item(project, "work/README.md", readme))
    for dest, src in WORK_TEMPLATES.items():
        items.append(_file_item(project, dest, _template(src)))
    items.extend(_justfile_items(project))
    return items


def _justfile_items(project: Path) -> list[Item]:
    kind = "python" if (project / "pyproject.toml").is_file() else "generic"
    justfile = project / "justfile"
    if not justfile.exists():
        model = "\n".join(_snippet(kind, r) for r in RECIPES)
        return [Item("create", "justfile", justfile, model, note=f"{kind} model")]
    model = "\n".join(_snippet(kind, r) for r in RECIPES)
    try:
        if justfile.read_text(encoding="utf-8") == model:
            # still must parse, but nothing to change
            just_recipes(justfile)
            return [Item("identical", "justfile")]
    except UnicodeDecodeError:
        pass
    present = just_recipes(justfile)  # parse error ⇒ InitError, before any write
    items = []
    for r in RECIPES:
        if r in present:
            items.append(
                Item("skip", f"justfile#{r}", note="recipe exists, kept as is")
            )
        else:
            items.append(
                Item(
                    "create",
                    f"justfile#{r}",
                    justfile,
                    recipe=r,
                    content=_snippet(kind, r),
                    note=f"appended, {kind} model",
                )
            )
    return items


# ---- apply -----------------------------------------------------------------


def _append_recipes(justfile: Path, items: list[Item]) -> None:
    original = justfile.read_bytes()
    text = original.decode("utf-8")
    for it in items:
        if text and not text.endswith("\n"):
            text += "\n"
        if text:
            text += "\n"
        text += it.content
    justfile.write_bytes(text.encode("utf-8"))
    try:
        names = just_recipes(justfile)
        missing = [it.recipe for it in items if it.recipe not in names]
        if missing:
            raise InitError(
                f"{justfile}: recipe(s) {', '.join(missing)} not found after append"
            )
    except InitError:
        justfile.write_bytes(original)  # restore the exact original bytes
        raise


def apply_plan(plan: list[Item]) -> None:
    appends = []
    for it in plan:
        if it.action != "create":
            continue
        if it.recipe:
            appends.append(it)
        else:
            assert it.path is not None
            it.path.parent.mkdir(parents=True, exist_ok=True)
            it.path.write_text(it.content, encoding="utf-8")
    if appends:
        _append_recipes(appends[0].path, appends)


def run(project: Path, profile: str | None, dry_run: bool = False) -> int:
    project = Path(project)
    try:
        if profile not in PROFILES:
            shown = "missing" if profile is None else f"unknown {profile!r}"
            raise InitError(
                f"--profile is required ({shown}): one of {', '.join(PROFILES)}"
            )
        if not project.is_dir():
            raise InitError(f"{project}: not a directory")
        plan = build_plan(project, profile)
        for it in plan:
            tail = f"  ({it.note})" if it.note else ""
            print(f"{it.action:<9} {it.label}{tail}")
        changes = sum(1 for it in plan if it.action == "create")
        if dry_run:
            print(
                f"{changes} changement(s) — dry-run, rien écrit"
                if changes
                else "0 changement"
            )
            return 0
        apply_plan(plan)
    except InitError as e:
        print(f"lab init: {e}", file=sys.stderr)
        return 1
    print(f"{changes} changement(s) appliqué(s)" if changes else "0 changement")
    return 0
