#!/usr/bin/env python3
"""Background orchestrator for the AI-native lab.

Reads a feature's tasks.md, builds the DAG (depends_on), runs the ready tasks
IN PARALLEL via `claude -p` (headless), passes the eval gate after each task
(max 3 iterations), and handles checkpoints according to their mode:
  - `mode: blocking` (default) — pause + notification, human validation via
        lab/engine/approve.sh CP-1 <feature_dir>
  - `mode: auto` — auto-validated if and only if evals green AND reviewer PASS;
        otherwise falls back to blocking. The final (merge) checkpoint is ALWAYS blocking.

Autonomy levels:
    --dry-run       show the plan, nothing runs
    --supervised    force all checkpoints to blocking (ignore auto modes)
    (default)       cruise: respect the modes of the plan approved by the Owner
    --validate      plan-lint: check tasks.md and exit (to be run by the planner
                    BEFORE proposing the plan, and by the Owner before approving)

Autonomy guardrails:
  - structured verdict: the implementer ends with STATUS: done|blocked — an agent
    blocked on a spec gap (OQ) never passes for finished
  - anti-empty-gate: a task that implements spec IDs fails if NO eval is
    collected (no eval written = no done, even if `just evals` exits 0)
  - failure containment: a failed/blocked task only blocks its own subtree of
    dependents (skipped); the other branches continue
  - scoped commits: we only stage the task's files_touched + the feature
    directory under lock (never `git add -A`, nor `tests`/`evals` wholesale which
    would suck in the files of other tasks and the goldens — findings H3/H5)

Usage:
    python3 lab/engine/orchestrate.py work/my-feature --validate
    python3 lab/engine/orchestrate.py work/my-feature --dry-run
    caffeinate -i python3 lab/engine/orchestrate.py work/my-feature &   # runs in background

Prerequisites: claude CLI installed and authenticated; tasks.md with status: approved
(frontmatter) — the orchestrator refuses an unvalidated plan (Cognition pattern).
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path

import approvals
from notify import notify
from planlint import validate
from plan import (
    SPEC_ID,
    Node,
    parse_tasks_md,
    paths_overlap,
    skip_dependents,
)
from kit import kit_root, kit_version
from registry import load_registry, resolve_model
import runner
from runner import DEFAULT_ALLOWED_TOOLS, get_runner
from verify import parse_verify


# ROOT = kit root: LAB_ROOT (test seam) else the dir holding lab/models/registry.toml —
# resolved by the ONE function in kit.py (design ADR-5).
ROOT = kit_root()
# LAB is the framework root (engine, model registry, agent definitions, docs).
# It is an alias of ROOT — kept distinct in intent so the prompts and the
# add-dir grant read clearly.
LAB = ROOT
# PROJECT is where the BUILD lives: work/<feature>, the code under build, the evals,
# and the git repo that receives the commits. It defaults to LAB (and every existing
# test sets only LAB_ROOT) so behaviour is unchanged — unless an external build target
# is selected via --project <path> or LAB_PROJECT_ROOT. main() may override it after
# parsing the CLI; the env default keeps it defined for any earlier reference.
PROJECT = (
    Path(os.environ["LAB_PROJECT_ROOT"]).resolve()
    if os.environ.get("LAB_PROJECT_ROOT")
    else ROOT
)
REGISTRY = load_registry(
    LAB
)  # model×role assignment (empty if no lab/models/registry.toml)
# Engine constants: reads of the effective policy (ADR-14, I-20), resolved ONCE in main()
# after --project (resolve_policy / apply_policy). These are only the pre-resolution
# defaults (= the `squad` floor); env LAB_BUDGET_USD, when set, wins over budget_usd.
MAX_EVAL_RETRIES = 3  # policy: max_task_attempts
MAX_PARALLEL = 3  # policy: max_parallel
MAX_CP_REJECTS = 2  # policy: max_cp_rejects — beyond this: CP failed, manual resume
BUDGET_USD = float(os.environ.get("LAB_BUDGET_USD", "0") or 0)  # 0 = no cap
BUDGET_SOURCE = "LAB_BUDGET_USD" if os.environ.get("LAB_BUDGET_USD") else "budget_usd"
POLICY: dict | None = None  # {key: (value, origin)} — policy.effective_policy
PROFILE: str | None = None
TASK_TIMEOUT_S = int(
    os.environ.get("LAB_TASK_TIMEOUT", "2400")
)  # wall per agent: 40 min
MAX_TURNS = 100
# Bash whitelist so the implementer can run its tests (acceptEdits covers edits,
# not Bash). NOT a security boundary — real confinement is the sandbox runner.
ALLOWED_TOOLS = list(DEFAULT_ALLOWED_TOOLS)
# Execution backend (LAB_RUNNER: claude-cli default | sandbox). The orchestrator
# depends on this interface, not on the `claude` binary.
RUNNER = get_runner()

# Interrupt (spec BHV-1, INV-1; design ADR-2): set by the SIGINT/SIGTERM handler of a real
# run. Workers poll it before an agent turn, after it and before any commit, and drain
# ("interrupted") instead of committing; checkpoint / Owner-lane waits return on it.
STOP = threading.Event()
_SIGNALS_SEEN: list[str] = []  # names of the signals received, in order (plain list:
# appended by the handler on the main thread, no lock taken in handler context)

DRY_RUN = False  # set from args.dry_run in main(): journal() writes nothing (INV-2)

COMMIT_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
COST_LOCK = threading.Lock()
COST_TOTAL = {"usd": 0.0}
# files_touched of the tasks currently running (parallel waves): a sibling's
# in-flight edits are not a scope leak of the task being checked.
RUNNING_LOCK = threading.Lock()
# files_touched of every task of the CURRENT wave, kept until the wave ends: a sibling
# that stopped without committing (blocked/failed) leaves files that are its own, not a
# scope leak of another task (fde-kit iteration 2: T22's docs charged to T20).
RUNNING_FILES: dict[str, list[str]] = {}
# Tasks of the wave whose agent is mid-turn. A task is judged (verify, gate, scope leak)
# only once no sibling is mid-turn, so it never sees a sibling's half-done edits in the
# shared tree (T22's lint gate went red on T20's unformatted work in progress).
ACTIVE: set[str] = set()
JUDGING: set[str] = set()  # settled tasks running verify / gate / scope check
ACTIVE_COND = threading.Condition()


def _set_active(node_id: str, active: bool) -> None:
    """active=True: the task is about to edit (start or resume an agent turn). It first
    leaves the judging set and waits until no sibling is judging, so a queued or retrying
    task never edits the tree while a sibling's verify/gate reads it. active=False: the
    task is done with the wave (finished, blocked, failed, or an Owner-lane wait)."""
    with ACTIVE_COND:
        JUDGING.discard(node_id)
        if active:
            ACTIVE_COND.notify_all()
            ACTIVE_COND.wait_for(lambda: not (JUDGING - {node_id}))
            ACTIVE.add(node_id)
        else:
            ACTIVE.discard(node_id)
        ACTIVE_COND.notify_all()


def _settle(node_id: str) -> None:
    """Leave the active set and wait until no sibling agent is mid-turn, then judge.
    Waiting tasks are not active, so siblings that all reach this point proceed
    together; a wave of one never waits. Queued tasks are not active until they start
    (registering them up front would hold worker threads and deadlock the pool) —
    _set_active keeps them from editing while this task is judging."""
    with ACTIVE_COND:
        ACTIVE.discard(node_id)
        ACTIVE_COND.notify_all()
        ACTIVE_COND.wait_for(lambda: not (ACTIVE - {node_id}))
        JUDGING.add(node_id)


# fd of the inter-process flock kept open for the whole run (released on process
# exit by the OS). Prevents two orchestrators from racing on the same feature.
_ORCH_LOCK_FD: int | None = None


def acquire_orchestrator_lock(feature: Path) -> None:
    """Exclusive OS flock on .runs/orchestrator.lock — fail-fast if already held (finding H6).

    Two orchestrate.py processes on the same feature would corrupt state.json, the
    git index, the journal and the budget (COST_TOTAL is per-process). threading.Lock
    only protects intra-process. The fd stays open: the OS releases it at process end.
    """
    global _ORCH_LOCK_FD
    lock_path = feature / ".runs" / "orchestrator.lock"
    lock_path.parent.mkdir(exist_ok=True, parents=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # exclusive, non-blocking
    except OSError as e:
        os.close(fd)
        raise OSError(
            f"orchestrator lock already held on {lock_path} — another run is active "
            "on this feature. Wait for it to finish (or delete the .lock if it is stale)."
        ) from e
    _ORCH_LOCK_FD = fd


def _begin_shutdown() -> None:
    """Runs in a helper thread (never in handler context, so it cannot deadlock on a lock
    the interrupted main thread holds): raise the stop flag, then kill the agents."""
    STOP.set()
    runner.terminate_all()


def _on_signal(signum: int, _frame) -> None:
    """SIGINT / SIGTERM handler (main thread only — E-1). First signal: start a graceful
    drain. Second signal: exit at once (BHV-1a) — state.json is only ever written
    atomically, so what is already on disk stays valid."""
    _SIGNALS_SEEN.append(signal.Signals(signum).name)
    if len(_SIGNALS_SEEN) > 1:
        runner.kill_all_now()  # best effort: leave no agent process behind
        os._exit(130)
    threading.Thread(target=_begin_shutdown, daemon=True).start()


def install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)


def atomic_write_json(path: Path, obj: dict) -> None:
    """Write a JSON atomically (tempfile + os.replace) — no truncation
    on SIGKILL mid-write (finding L9)."""
    path.parent.mkdir(exist_ok=True, parents=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=str(path.parent), delete=False, suffix=".tmp", encoding="utf-8"
    ) as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        tmp = f.name
    try:
        os.replace(tmp, str(path))
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def eval_covers(spec_id: str, collected: str) -> bool:
    """True if a collected eval carries spec_id, by matching the pytest NODE ID
    (finding M7). We look at the test name AFTER "::" (not the file path),
    and forbid a numeric prefix collision: eval_1 != eval_10,
    and tests/eval_2_helpers.py does not "cover" EVAL-2."""
    slug = spec_id.lower().replace("-", "_")  # EVAL-1 -> eval_1
    pat = re.compile(rf"(?<![a-z0-9]){re.escape(slug)}(?![0-9])")
    for line in collected.splitlines():
        if "::" not in line:
            continue
        node_id = line.rsplit("::", 1)[1]  # test name, not the path
        if pat.search(node_id.lower()):
            return True
    return False


# ---------------------------------------------------------------- execution


def run_log(feature: Path, node: Node, agent: str, result: str) -> None:
    line = f"| {datetime.now():%Y-%m-%d %H:%M} | {node.id} | {agent} | {result} | |\n"
    with LOG_LOCK, (feature / "tasks.md").open("a", encoding="utf-8") as f:
        f.write(line)


def journal(feature: Path, **event) -> None:
    """Run telemetry: one JSON line per event in .runs/journal.jsonl (no-op in a dry run)."""
    if DRY_RUN:
        return
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    path = feature / ".runs" / "journal.jsonl"
    with LOG_LOCK:
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")


# ---- kit guardrails on every agent call (spec BHV-2, INV-1; design ADR-2, ADR-10) ----

PLUGIN_REL = Path("lab") / "plugin"
RUN_SETTINGS_REL = Path("lab") / "engine" / "run_settings.json"
RULES_REL = PLUGIN_REL / "rules" / "hard-rules.md"
MIN_CLAUDE_VERSION = (2, 1, 295)  # `onFailure` hooks (design ADR-6)


SANDBOX_KIT = "/kit"  # where the sandbox mounts the kit root, read-only (ADR-15)


class SandboxPathError(ValueError):
    """A host path that would not exist inside the sandbox container."""


def sandboxed_external() -> bool:
    """External instance driven through the sandbox runner: the kit lives at /kit."""
    return (
        PROJECT != LAB
        and (os.environ.get("LAB_RUNNER") or "").strip().lower() == "sandbox"
    )


def kit_ref(path: Path | None = None) -> str:
    """A kit path as the agent sees it: `/kit/…` in the external sandbox, host path else."""
    p = Path(path) if path is not None else LAB
    if not sandboxed_external():
        return str(p)
    rel = p.resolve().relative_to(LAB.resolve())
    return str(Path(SANDBOX_KIT) / rel)


def project_ref(path: Path) -> str:
    """A path under the instance as the agent sees it: `/workspace/…` in the external
    sandbox (the instance is mounted there), host path else."""
    if not sandboxed_external():
        return str(path)
    return str(Path("/workspace") / Path(path).resolve().relative_to(PROJECT.resolve()))


def translate_add_dirs(dirs: list[str]) -> list[str]:
    """Sandbox + external: `--add-dir` paths inside the kit become `/kit/…`; any other host
    path is refused (it would not exist in the container, ADR-15, I-24)."""
    out = []
    for d in dirs:
        try:
            out.append(kit_ref(Path(d)))
        except ValueError:
            raise SandboxPathError(
                f"add_dir {d} is outside the kit ({LAB}): not reachable from the sandbox"
            ) from None
    return out


def guardrail_options() -> dict:
    """Plugin dir, run settings and hard rules for EVERY agent call (implementer and
    reviewer alike). Resolved from the KIT root (LAB), never from PROJECT (I-2). Kit mode
    (PROJECT == LAB): cwd-relative paths, valid on the host and inside the sandbox's
    /workspace (ADR-10). External instance: absolute paths under the kit. The engine never
    passes `--bare`."""
    external = PROJECT != LAB
    if sandboxed_external():  # kit mounted read-only at /kit (ADR-15)
        plugin_dir = kit_ref(LAB / PLUGIN_REL)
        settings = kit_ref(LAB / RUN_SETTINGS_REL)
    else:
        base = LAB if external else Path()
        plugin_dir, settings = str(base / PLUGIN_REL), str(base / RUN_SETTINGS_REL)
    return {
        "plugin_dir": plugin_dir,
        "settings": settings,
        "append_system_prompt": (LAB / RULES_REL).read_text(encoding="utf-8"),
    }


def agent_file(role: str) -> Path:
    """Agent definition for `role`, evaluated per call: always the plugin's
    `lab/plugin/agents/<role>.md` (single source, ADR-3; no legacy fallback)."""
    return LAB / PLUGIN_REL / "agents" / f"{role}.md"


def _parse_version(text: str) -> tuple[int, ...] | None:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return tuple(int(x) for x in m.groups()) if m else None


def resolve_policy(
    force: bool,
) -> tuple[dict | None, str | None, list[str]]:
    """Effective policy of PROJECT (ADR-14, ADR-16). Returns (policy, profile, refusals).
    Refusals (rc 1): no .lab/lab.toml (names `lab init`), PolicyError, sandbox_required
    without LAB_RUNNER=sandbox, allow_force=false with --force."""
    from lab_init import LabTomlError, read_lab_toml
    from policy import PolicyError, effective_policy

    try:
        lab_toml = read_lab_toml(PROJECT)
        policy = effective_policy(lab_toml)
    except (LabTomlError, PolicyError) as e:
        return None, None, [str(e)]
    refusals = []
    runner = (os.environ.get("LAB_RUNNER") or "").strip().lower()
    if policy["sandbox_required"][0] is True and runner != "sandbox":
        refusals.append(
            f"sandbox_required is true (profile '{lab_toml['profile']}'): "
            "set LAB_RUNNER=sandbox to run"
        )
    if force and policy["allow_force"][0] is False:
        refusals.append(
            f"allow_force is false (profile '{lab_toml['profile']}'): --force is refused"
        )
    return policy, lab_toml["profile"], refusals


def apply_policy(policy: dict) -> None:
    """The engine constants become reads of the effective policy (I-20)."""
    global MAX_EVAL_RETRIES, MAX_PARALLEL, MAX_CP_REJECTS, BUDGET_USD, BUDGET_SOURCE
    MAX_EVAL_RETRIES = int(policy["max_task_attempts"][0])
    MAX_PARALLEL = int(policy["max_parallel"][0])
    MAX_CP_REJECTS = int(policy["max_cp_rejects"][0])
    if (os.environ.get("LAB_BUDGET_USD") or "").strip():
        BUDGET_USD = float(os.environ["LAB_BUDGET_USD"])  # operator setting wins
        BUDGET_SOURCE = "LAB_BUDGET_USD"
    else:
        BUDGET_USD = float(policy["budget_usd"][0] or 0)
        # origin ∈ {floor, override}: "override (free key)" reads as plain "override" (BHV-5)
        origin = str(policy["budget_usd"][1]).split(" (")[0]
        BUDGET_SOURCE = f"budget_usd, {origin}"


def preflight() -> list[str]:
    """Fail-closed pre-flight (ADR-6, I-5). Returns the refusal messages (empty = go).
    Order: kit root; plugin dir; (external instance) pin; claude CLI; runner/instance."""
    external = PROJECT != LAB
    plugin = LAB / PLUGIN_REL
    if not plugin.is_dir():
        return [
            f"plugin directory {plugin} not found — the kit install is broken "
            "(reinstall fde-kit or set LAB_ROOT to the kit)"
        ]
    for f in (LAB / RULES_REL, LAB / RUN_SETTINGS_REL):
        if not f.is_file():
            return [f"{f} not found — the kit install is broken"]
    if external:
        from lab_init import LabTomlError, read_lab_toml

        try:
            pinned = read_lab_toml(PROJECT)["kit_version"]
        except LabTomlError as e:
            return [str(e)]
        running = kit_version()
        if pinned != running:
            return [
                f"plugin {running} ≠ pinned kit {pinned} "
                f"(.lab/lab.toml in {PROJECT}; upgrading the kit is an explicit commit of the instance)"
            ]
    try:
        p = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"cannot run `claude --version`: {e}"]
    found = _parse_version(p.stdout) if p.returncode == 0 else None
    minimum = ".".join(map(str, MIN_CLAUDE_VERSION))
    if found is None:
        return [f"cannot read the claude CLI version (need >= {minimum})"]
    if found < MIN_CLAUDE_VERSION:
        return [
            f"claude CLI {'.'.join(map(str, found))} is too old (need >= {minimum})"
        ]
    return []


def run_claude(
    prompt: str, resume: str | None = None, model: str | None = None
) -> dict:
    """Headless claude call. Returns {ok, text, session_id, cost_usd, error}.

    Wall-clock wall TASK_TIMEOUT_S: a stuck agent never blocks its wave
    indefinitely. --output-format json output: result text, session_id
    (to resume the SAME session on retry instead of starting over) and
    cost, aggregated into COST_TOTAL for the summary (Twin Track metric).
    model: --model passed as-is (CLI default if None).
    """
    # The approval secret must NEVER be visible to a sub-agent: otherwise
    # it could sign its own checkpoint validation (finding H1).
    child_env = {k: v for k, v in os.environ.items() if k != approvals.ENV_SECRET}
    # When the build lives in an external project, the agent runs there (cwd=PROJECT)
    # but must still READ the framework files (agent defs, engineering-rules, …) which
    # live under the LAB — grant that dir explicitly. When PROJECT==LAB (every test and
    # the in-repo path) no --add-dir is added, so the argv is unchanged.
    add_dirs = [str(LAB)] if PROJECT != LAB else None
    extra: dict = {}
    if (
        sandboxed_external()
    ):  # ADR-15: kit at /kit (ro); host paths translated or refused
        add_dirs = translate_add_dirs(add_dirs or [])
        extra["kit_mount"] = LAB
    r = RUNNER.run(
        prompt,
        cwd=PROJECT,
        model=model,
        resume=resume,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=MAX_TURNS,
        timeout=TASK_TIMEOUT_S,
        env=child_env,
        add_dirs=add_dirs,
        **extra,
        **guardrail_options(),
    )
    with COST_LOCK:
        COST_TOTAL["usd"] += r.cost_usd
    return {
        "ok": r.ok,
        "text": r.text,
        "session_id": r.session_id,
        "cost_usd": r.cost_usd,
        "error": r.error,
    }


def run_evals() -> tuple[bool, str]:
    p = subprocess.run(["just", "evals"], cwd=PROJECT, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr)[-3000:]


def _just_has_recipe(name: str) -> bool:
    """True iff PROJECT's justfile defines a recipe `name`. Fail-closed: any
    error / missing `just` / non-zero exit ⇒ False, so a pytest-only project (or
    a test sandbox without the recipe) falls back to the pytest path unchanged.
    `just --summary` prints the recipe names space-separated."""
    try:
        p = subprocess.run(
            ["just", "--summary"], cwd=PROJECT, capture_output=True, text=True
        )
    except Exception:
        return False
    return p.returncode == 0 and name in p.stdout.split()


def evals_collected() -> str:
    """Raw list of collected evals (node-ids `path::test_name`).

    Serves the anti-empty-gate (empty = nothing to gate) AND ID coverage:
    the convention "test name containing the lowercased ID" makes each
    EVAL-n in the spec mechanically verifiable — language-agnostic, as long as
    the lines are `something::test_name`.
    LAB_EVALS_COLLECTED_FILE: test seam (content read as-is).
    """
    hook = os.environ.get("LAB_EVALS_COLLECTED_FILE")
    if hook:
        p = Path(hook)
        return p.read_text(encoding="utf-8") if p.exists() else ""
    # Language-agnostic collection: if the project provides an `evals-collect`
    # recipe, it owns listing its evals (pytest + vitest + playwright + …) as
    # normalized `path::test_eval_n_…` node-ids. Mirrors the `just evals`
    # delegation (run path) so the engine stays stack-neutral.
    if _just_has_recipe("evals-collect"):
        p = subprocess.run(
            ["just", "evals-collect"], cwd=PROJECT, capture_output=True, text=True
        )
        return p.stdout
    if not (PROJECT / "pyproject.toml").exists():
        return ""
    p = subprocess.run(
        ["uv", "run", "pytest", "-m", "eval", "--collect-only", "-q"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )
    return p.stdout


def scoped_commit(node: Node, feature: Path, message: str) -> None:
    """Stage only the task's scope, under lock (parallel waves).

    We NO LONGER stage `tests`/`evals` wholesale (findings H3/H5): by convention,
    files_touched already contains the task's tests/evals paths. Wholesale staging
    used to suck in the files of other tasks in the wave AND the
    `evals/golden/**` oracles — an out-of-scope tampered golden ended up
    auto-committed, corrupting the scorecard ground truth. So we stage node.files +
    the feature directory (spec/design/tasks), then un-stage any undeclared golden.
    """
    with COMMIT_LOCK:
        paths = [*node.files, str(feature.relative_to(PROJECT))]
        for p in paths:
            subprocess.run(["git", "add", "--", p], cwd=PROJECT, capture_output=True)
        # Oracle guardrail: a golden is committed only if it is explicitly in
        # files_touched. Otherwise we un-stage it (finding H3, scorecard anti-tamper).
        staged = subprocess.run(
            ["git", "diff", "--cached", "--no-renames", "--name-only"],
            cwd=PROJECT,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        for f in staged:
            if f.startswith("evals/golden/") and not any(
                paths_overlap(f, d) for d in node.files
            ):
                subprocess.run(
                    ["git", "reset", "-q", "HEAD", "--", f],
                    cwd=PROJECT,
                    capture_output=True,
                )
                print(
                    f"⚠️  {node.id}: golden outside files_touched un-staged (oracle protected): {f}",
                    flush=True,
                )
        leftover = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT,
            capture_output=True,
            text=True,
        ).stdout
        out_of_scope = [
            line
            for line in leftover.splitlines()
            if line and not line.startswith(("A ", "M ", "R ", "D "))
        ]
        if out_of_scope:
            print(
                f"⚠️  {node.id}: changes outside files_touched left uncommitted:",
                flush=True,
            )
            for line in out_of_scope[:10]:
                print(f"     {line}", flush=True)
        # INV-3: the Artifacts trailer is what the commit really carries (staged paths,
        # after the golden un-staging), computed here and not from node.files.
        final = subprocess.run(
            ["git", "diff", "--cached", "--no-renames", "--name-only"],
            cwd=PROJECT,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if final:
            message = _with_artifacts(message, sorted(set(final)))
        subprocess.run(
            ["git", "commit", "-m", message], cwd=PROJECT, capture_output=True
        )


def _with_artifacts(message: str, paths: list[str]) -> str:
    """Insert `Artifacts: <paths>` before the `Run:` trailer (canonical trailer order)."""
    line = f"Artifacts: {', '.join(paths)}"
    lines = message.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("Run: "):
            lines.insert(i, line)
            break
    else:
        lines.append(line)
    return "\n".join(lines)


def _dirty_paths() -> set[str]:
    """Paths (repo-relative) that differ from HEAD: modified, deleted, renamed
    (both sides) and untracked — gitignored files excluded."""
    out = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
    ).stdout
    paths: set[str] = set()
    entries = out.split("\0")
    i = 0
    while i < len(entries):
        e = entries[i]
        i += 1
        if len(e) < 4:
            continue
        paths.add(e[3:])
        if e[0] in "RC" and i < len(entries):  # -z: rename source follows
            paths.add(entries[i])
            i += 1
    return paths


def _scope_leaks(node: Node, feature: Path, baseline: set[str]) -> list[str]:
    """Changes this task made OUTSIDE its files_touched (plan gap found in CP-3).

    `verify` and the eval gate run on the WORKING TREE, but scoped_commit only
    stages files_touched + the feature dir: an out-of-scope edit that makes the
    verify pass is silently left behind, so the committed tree can be red while
    the run log says green. Excluded: what was already dirty before the task
    (baseline), the feature dir (run log, reviews), and the files_touched of the
    tasks running in parallel with it."""
    feat = str(feature.relative_to(PROJECT))
    with RUNNING_LOCK:
        sibling = [f for nid, fs in RUNNING_FILES.items() if nid != node.id for f in fs]
    return sorted(
        p
        for p in _dirty_paths() - baseline
        if not paths_overlap(p, feat)
        and not any(paths_overlap(p, f) for f in node.files)
        and not any(paths_overlap(p, f) for f in sibling)
    )


def _commit_message(node: Node, feature: Path, real_ids: list[str]) -> str:
    """Canonical commit format (docs/reference/commit-format.md): subject + Why + trailers.

    The orchestrator's [auto] commits use the SAME shape as the human `/commit` skill,
    so git history — the project's memory — reads uniformly and agents can mine the
    `Why:` line and the trailers to recover the reasoning behind a change. The deep
    "why" of a contract lives in the human spec-amendment commits; an [auto] commit
    implements an already-approved task, so its why is the task itself.
    """
    tag = f"[{', '.join(real_ids)}]" if real_ids else "[auto]"
    # Flatten newlines: a newline in title/done_when would split the subject line
    # or forge a fake "Key: value" line in the body (commit-structure integrity).
    title = node.title.strip().replace("\n", " ")
    dw = node.done_when.strip().replace("\n", " ")
    subject = f"feat({feature.name}): {node.id} {title} {tag}"
    why = title + (f" — done when: {dw}" if dw else "")
    # A rework carries the decision that triggered it: the checkpoint rejection
    # reason belongs in git (hard rule "the why lives in git"), not only in the
    # tasks.md run log (found at fde-kit CP-4: bc58ecd said nothing of it).
    rm = re.search(r"OWNER REVIEW FEEDBACK \(rejection ([\w-]+)\): (.*)", node.rework)
    if rm:
        reason = rm.group(2).strip()
        why += f"\nRework after the {rm.group(1)} rejection: {reason}"
    lines = [subject, "", f"Why: {why}", ""]
    if real_ids:
        lines.append(f"Spec-IDs: {', '.join(real_ids)}")
    lines.append("Run: owner" if node.agent == "owner" else "Run: auto")
    return "\n".join(lines)


def _build_base_prompt(node: Node, feature: Path) -> str:
    return (
        f"You act as the implementer agent ({kit_ref(agent_file('implementer'))}). "
        f"Framework references (engineering rules, deployment standard, other agent files) "
        f"live under {kit_ref()} — resolve any such path there, not under the project. "
        f"Read {project_ref(feature)}/spec.md then {project_ref(feature)}/design.md "
        f"then {project_ref(feature)}/tasks.md. "
        f"Execute ONLY task {node.id} — {node.title}. "
        f"Respect its files_touched scope and its done_when. "
        f"If the spec is ambiguous or has gaps: do not invent, record the question (OQ-n format) in spec.md §8 "
        f"and end blocked. "
        f"You MUST end your reply with a single line: "
        f'"STATUS: done" or "STATUS: blocked — <reason, e.g. OQ-3>".\n{node.prompt}{node.rework}'
    )


def _run_verify(node: Node) -> tuple[bool, str, str]:
    """Run the task's `verify` (no shell). Returns (passed, agent_feedback, log_label)."""
    if not node.verify:
        return True, "", ""
    try:
        argv, venv = parse_verify(node.verify)
    except ValueError as e:
        # Should not happen (plan-lint already blocks), but defense in depth under
        # --force: we never launch a shell.
        return False, f"\n\n⛔ invalid verify (`{node.verify}`): {e}", "verify INVALID"
    v = subprocess.run(
        argv,
        cwd=PROJECT,
        capture_output=True,
        text=True,
        env={**os.environ, **venv} if venv else None,
    )
    if v.returncode != 0:
        return (
            False,
            f"\n\n⛔ verify failed (`{node.verify}`):\n{(v.stdout + v.stderr)[-2000:]}",
            "verify FAIL",
        )
    return True, "", ""


# Source files that, when touched, REQUIRE an eval (anti-empty-gate, finding M6).
# Stack-neutral lists — extend HERE, not in the gate logic — so a JS/TS feature
# (e.g. front/Button.tsx) is gated exactly like a Python one. Over-matching a
# config file fails CLOSED (asks for an eval); it never lets ungated code through.
SOURCE_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte")
SOURCE_DIRS = ("src", "app", "lib", "modules", "front", "back")


def _eval_gate(node: Node, real_ids: list[str]) -> tuple[bool, str]:
    """Run evals + anti-empty-gate (M6) + ID coverage (M7). Returns (ok, agent_feedback)."""
    ok, out = run_evals()
    # A task that touches source code MUST have evals even without a declared
    # implements (finding M6) — otherwise `just evals` green by absence (masked
    # exit-5) would let ungated code through.
    touches_source = any(
        f.endswith(SOURCE_EXTS) and not f.startswith(("tests/", "evals/"))
        for f in node.files
    ) or any(paths_overlap(f, p) for f in node.files for p in SOURCE_DIRS)
    if ok and (real_ids or touches_source):
        collected = evals_collected()
        if "::" not in collected:
            reason = (
                f"implements {node.implements}"
                if real_ids
                else f"modifies source code {node.files}"
            )
            return False, (
                "Empty gate: `just evals` is green but NO eval is collected "
                f"while the task {reason}. Write the evals from spec.md §7 "
                "(pytest -m eval) — no eval, no done."
            )
        if real_ids:
            missing = [
                i
                for i in real_ids
                if i.startswith("EVAL-") and not eval_covers(i, collected)
            ]
            if missing:
                return False, (
                    f"Incomplete eval coverage: no collected test carries {missing}. "
                    f"Convention: node-id `test_{missing[0].lower().replace('-', '_')}_<case>` "
                    "(lowercased ID, dashes→underscores)."
                )
    if ok and _just_has_recipe("lint-check"):
        # The project's own non-mutating lint is part of "done": a task whose verify
        # only runs its test (fde-kit T14) otherwise lands unformatted code that turns
        # `gate-ci` red at the merge checkpoint. No recipe ⇒ no lint imposed.
        lp = subprocess.run(
            ["just", "lint-check"], cwd=PROJECT, capture_output=True, text=True
        )
        if lp.returncode != 0:
            return False, (
                "LINT RED: `just lint-check` (the project's own lint, part of the "
                "merge gate) fails — fix formatting/lint in your files, without "
                "touching files outside files_touched:\n"
                + (lp.stdout + lp.stderr)[-2000:]
            )
    return ok, out


def run_owner_task(node: Node, feature: Path, dry: bool, real_ids: list[str]) -> str:
    """Owner lane (`agent: owner`): work a headless agent cannot do — writes under
    protected paths (the Claude Code config dir, a plugin's agents/skills/hooks) or commands outside
    its allowlist. No agent is dispatched: the Owner does the task by hand, then
    signs it with approve.sh. The engine still owns "done": the task's verify and
    the eval gate must be green, then the scoped commit carries the work
    (`Run: owner`). reject.sh on the task = the Owner gives up → blocked."""
    if dry:
        print(f"  [dry-run] OWNER TASK {node.id} — waits for a signed approval")
        return "done"
    rel = feature.relative_to(PROJECT)
    notify(
        f"OWNER TASK {node.id} — {node.title}: do it by hand (tasks.md prompt; scope: "
        f"{', '.join(node.files)}), then lab/engine/approve.sh {node.id} {rel} "
        f'(or reject.sh {node.id} {rel} "reason" to block it)'
    )
    outcome, info = _await_token(node, feature, "owner task")
    if outcome == "interrupted":  # BHV-1b: waiting, not in flight — stays pending
        return "interrupted_waiting"
    if outcome == "approved":
        # The Owner-lane counterpart of a successful task_attempt: the trajectory
        # guard (BHV-2a) accepts a task_done only after one of the two.
        journal(feature, event="owner_signed", id=node.id)
    if outcome != "approved":
        journal(
            feature, event="task_blocked", id=node.id, reason=info.get("reason", "")
        )
        return "blocked"
    if STOP.is_set():  # BHV-1c: signed, then interrupted: pending, the Owner re-signs
        return "interrupted"
    passed, feedback, label = _run_verify(node)
    ok, out = _eval_gate(node, real_ids) if passed else (False, feedback)
    if STOP.is_set():  # BHV-1c: the consumed signature is never reused
        return "interrupted"
    if not (passed and ok):
        run_log(
            feature,
            node,
            "owner",
            f"owner task RED after signature ({label or 'evals'})",
        )
        journal(feature, event="task_failed", id=node.id)
        notify(
            f"{node.id}: signed but verify/evals red — fix and restart:\n{out[:500]}"
        )
        return "failed"
    run_log(feature, node, "owner", "done by the Owner, verify + evals green")
    scoped_commit(node, feature, _commit_message(node, feature, real_ids))
    journal(feature, event="task_done", id=node.id, attempts=1, lane="owner")
    return "done"


def run_task(node: Node, feature: Path, dry: bool) -> str:
    try:
        return _run_task(node, feature, dry)
    finally:
        _set_active(node.id, False)  # finished, blocked or failed: never hold siblings


def _run_task(node: Node, feature: Path, dry: bool) -> str:
    """Returns done | failed | blocked. Per attempt: run the agent → parse the
    STATUS verdict → run verify → run the eval gate → scoped commit on green."""
    if node.agent == "owner":
        ids = list(
            dict.fromkeys(s for t in node.implements for s in SPEC_ID.findall(t))
        )
        _set_active(
            node.id, False
        )  # no agent turn: waiting on a human never holds siblings
        return run_owner_task(node, feature, dry, ids)
    if STOP.is_set():  # a queued task picked up after the interrupt never starts
        return "not_started"
    if dry:
        print(
            f"  [dry-run] {RUNNER.name} run: {node.id} "
            f"(acceptEdits, max_turns={MAX_TURNS}, {len(ALLOWED_TOOLS)} allowed tools)"
        )
        return "done"

    real_ids = list(
        dict.fromkeys(s for t in node.implements for s in SPEC_ID.findall(t))
    )
    mid = resolve_model("implementer", node.model, REGISTRY)
    base_prompt = _build_base_prompt(node, feature) + REGISTRY.profile_text(mid)
    baseline = _dirty_paths()
    with RUNNING_LOCK:  # cleared at the start of the next wave, not here
        RUNNING_FILES[node.id] = list(node.files)
    return _run_task_attempts(node, feature, real_ids, base_prompt, mid, baseline)


def _run_task_attempts(
    node: Node,
    feature: Path,
    real_ids: list[str],
    base_prompt: str,
    mid: str | None,
    baseline: set[str],
) -> str:
    session: str | None = None
    extra = ""
    for attempt in range(1, MAX_EVAL_RETRIES + 1):
        print(f"▶ {node.id} (attempt {attempt}/{MAX_EVAL_RETRIES})", flush=True)
        t0 = time.monotonic()
        if session:
            # Retry in the SAME session: the agent fixes its work instead of redoing it
            prompt = (
                f"Still on task {node.id} — {node.title}. Fix without rewriting everything:{extra}\n"
                f'End with "STATUS: done" or "STATUS: blocked — <reason>".'
            )
        else:
            prompt = base_prompt + extra
        # INV-1: no agent turn after an interrupt. Before the first turn the task is
        # not in flight (nothing started): it stays pending, outside `inflight`.
        if STOP.is_set():
            return "not_started" if attempt == 1 else "interrupted"
        _set_active(node.id, True)
        if STOP.is_set():
            return "not_started" if attempt == 1 else "interrupted"
        r = run_claude(prompt, resume=session, model=mid)
        if STOP.is_set():  # the turn was killed (or ended) by the interrupt: drop it
            return "interrupted"
        _settle(node.id)  # judge the turn only on a tree no sibling is still editing
        if STOP.is_set():
            return "interrupted"
        journal(
            feature,
            event="task_attempt",
            id=node.id,
            attempt=attempt,
            model=mid,
            duration_s=round(time.monotonic() - t0, 1),
            cost_usd=r["cost_usd"],
            session=r["session_id"],
            ok=r["ok"],
        )
        if not r["ok"]:
            print(r["error"], file=sys.stderr)
            run_log(feature, node, "implementer", f"claude error (t{attempt})")
            session = None  # unknown/lost session: start clean
            continue
        session = r["session_id"] or session

        sm = re.search(r"STATUS:\s*(done|blocked)([^\n]*)", r["text"], re.I)
        if sm and sm.group(1).lower() == "blocked":
            reason = sm.group(2).strip(" —-:") or "unspecified reason"
            run_log(feature, node, "implementer", f"BLOCKED — {reason}")
            journal(feature, event="task_blocked", id=node.id, reason=reason)
            notify(
                f"{node.id} blocked: {reason} — Owner response expected (spec.md §8)"
            )
            return "blocked"
        if not sm:
            print(
                f"⚠️  {node.id}: no STATUS line in the reply — falling back to the evals",
                flush=True,
            )

        passed, feedback, label = _run_verify(node)
        if STOP.is_set():
            return "interrupted"
        if not passed:
            extra = feedback
            run_log(feature, node, "implementer", f"{label} (t{attempt})")
            # Telemetry for the failure clusters of `just report` (sdlc-rework BHV-1b)
            journal(
                feature, event="verify_fail", id=node.id, attempt=attempt, label=label
            )
            continue

        ok, out = _eval_gate(node, real_ids)
        if STOP.is_set():
            return "interrupted"
        leaks = _scope_leaks(node, feature, baseline) if ok else []
        if leaks:
            # Green, but only thanks to files the scoped commit will NOT carry.
            listed = "\n".join(f"  - {p}" for p in leaks[:20])
            extra = (
                "\n\n⛔ SCOPE LEAK: verify/evals are green, but you changed files OUTSIDE "
                f"this task's files_touched; they would be left out of the commit:\n{listed}\n"
                "Revert those changes and make the task pass within files_touched. If that "
                'is impossible, end with "STATUS: blocked — files_touched gap: <files>" '
                "so the Owner amends the plan."
            )
            print(f"⚠️  {node.id}: scope leak — {', '.join(leaks[:5])}", flush=True)
            run_log(feature, node, "implementer", f"SCOPE LEAK (t{attempt})")
            journal(
                feature, event="scope_leak", id=node.id, attempt=attempt, files=leaks
            )
            continue
        if ok:
            if STOP.is_set():  # last check before the commit (INV-1)
                return "interrupted"
            run_log(feature, node, "implementer", f"done, evals green (t{attempt})")
            scoped_commit(node, feature, _commit_message(node, feature, real_ids))
            journal(feature, event="task_done", id=node.id, attempts=attempt)
            return "done"
        extra = f"\n\n⛔ EVAL GATE RED on the previous attempt. Fix:\n{out}"
        run_log(feature, node, "eval-runner", f"FAIL (t{attempt})")
        journal(feature, event="eval_fail", id=node.id, attempt=attempt)
    notify(f"{node.id}: {MAX_EVAL_RETRIES} eval failures — Owner escalation")
    journal(feature, event="task_failed", id=node.id)
    return "failed"


REVIEW_LENSES = [
    "correctness: does the code do what the spec says (INV/BHV), values and bounds included",
    "spec/design conformance: traceability, scope, ADR compliance, no scope creep",
    "edge cases & robustness: extreme inputs, errors, does the deliverable actually run",
]


def pick_reviewer_models(cp: Node, n: int) -> list[str | None]:
    """n models for the panel. Separation of duties: we prefer a reviewer model
    DIFFERENT from the implementer (a model must not validate its own work alone)."""
    impl = resolve_model("implementer", "", REGISTRY)
    base = resolve_model("reviewer", cp.model, REGISTRY)
    # An explicit panel in the registry ([review] panel) wins when every seat is
    # reviewer-eligible and no checkpoint forces its own model.
    eligible_ids = {m.id for m in REGISTRY.eligible("reviewer")}
    panel = REGISTRY.review_panel
    if panel and not cp.model and all(m in eligible_ids for m in panel):
        return [panel[i % len(panel)] for i in range(n)]
    pool = [m.id for m in REGISTRY.eligible("reviewer")] or ([base] if base else [None])
    # priority to models != implementer, then the rest
    ordered = [m for m in pool if m != impl] + [m for m in pool if m == impl]
    if base in ordered:  # keep the role default at the front if it is admissible
        ordered = [base] + [m for m in ordered if m != base]
    return [ordered[i % len(ordered)] for i in range(n)]


def _aggregate_verdict(verdicts: list[str]) -> str:
    if any(v == "BLOCK" for v in verdicts):
        return "BLOCK"
    if sum(v == "PASS" for v in verdicts) > len(verdicts) / 2:  # strict majority
        return "PASS"
    return "WARN"


def run_review(cp: Node, feature: Path, dry: bool) -> tuple[str, Path, bool]:
    """Reviewer panel. Returns (aggregated_verdict, report, self_review_only).
    self_review_only = True if all panelists run on the implementer's model
    (separation of duties impossible → self-validation will be refused)."""
    report = feature / ".runs" / f"{cp.id}-review.md"
    if dry:
        print(f"  [dry-run] reviewer×{cp.reviewers} → {report}")
        return "PASS", report, False

    n = cp.reviewers
    models = pick_reviewer_models(cp, n)
    impl = resolve_model("implementer", "", REGISTRY)
    verdicts: list[str] = []
    sections: list[str] = []
    for i, mid in enumerate(models):
        if STOP.is_set():  # INV-1: no reviewer turn starts after an interrupt
            return "WARN", report, False
        lens = REVIEW_LENSES[i % len(REVIEW_LENSES)] if n > 1 else "full review"
        prompt = (
            f"You act as the reviewer agent ({kit_ref(agent_file('reviewer'))}). Feature: {project_ref(feature)}. "
            f"Checkpoint {cp.id} — {cp.title}. Tasks covered: {', '.join(cp.depends_on) or 'all'}. "
            f"REVIEW LENS imposed: {lens}. "
            f"Produce the report (✅/⚠️/❌ with file:line) and you MUST end with a "
            f'single line: "VERDICT: PASS", "VERDICT: WARN" or "VERDICT: BLOCK".'
        ) + REGISTRY.profile_text(mid)
        r = run_claude(prompt, model=mid)
        if STOP.is_set():  # the turn was cut by the interrupt: no verdict, no report
            return "WARN", report, False
        vm = re.findall(r"VERDICT:\s*(PASS|WARN|BLOCK)", r["text"])
        v = vm[-1] if vm else "WARN"
        verdicts.append(v)
        sections.append(
            f"## Panelist {i + 1} — {mid or 'CLI default'} — lens: {lens}\nVERDICT: {v}\n\n{r['text'] or r['error']}"
        )
        journal(
            feature,
            event="review",
            id=cp.id,
            model=mid,
            lens=lens,
            verdict=v,
            cost_usd=r["cost_usd"],
            ok=r["ok"],
        )

    agg = _aggregate_verdict(verdicts)
    self_only = impl is not None and all(m == impl for m in models)
    report.parent.mkdir(exist_ok=True)
    header = f"# Review {cp.id} — panel of {n} — aggregated verdict: {agg} ({', '.join(verdicts)})\n\n"
    report.write_text(header + "\n\n---\n\n".join(sections), encoding="utf-8")
    return agg, report, self_only


def parse_rejection(path: Path) -> dict:
    info: dict = {"reason": "", "tasks": []}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("reason="):
            info["reason"] = line[len("reason=") :].strip()
        elif line.startswith("tasks="):
            info["tasks"] = line[len("tasks=") :].split()
    return info


def is_merge_checkpoint(node: Node, nodes: list[Node]) -> bool:
    """Final/merge checkpoint — same test as plan-lint (INV-5): sink of the graph, or
    "merge" in its title."""
    is_sink = not any(node.id in m.depends_on for m in nodes)
    return is_sink or "merge" in (node.title + " ").lower()


def wait_checkpoint(
    node: Node, feature: Path, dry: bool, supervised: bool, merge: bool = False
) -> tuple[str, dict]:
    """Returns ("approved", {}) or ("rejected", {reason, tasks}).
    `merge`: a final/merge CP is NEVER auto-approved — whatever its mode, --force or the
    profile (INV-5); it always waits for a signed human approval."""
    approval = feature / ".approvals" / node.id
    if dry:
        print(
            f"  [dry-run] CHECKPOINT {node.id} (mode {node.mode}) — attend {approval}"
        )
        return "approved", {}

    # A rejection already waiting (e.g. dropped while the engine was restarted) is
    # honored BEFORE paying for a new review panel: rejecting is the conservative
    # outcome, the review would change nothing. An approval is never short-cut —
    # the review is regenerated first (self-hosting protocol).
    if (feature / ".approvals" / f"{node.id}.rejected").exists():
        return _await_token(node, feature, "checkpoint")

    if STOP.is_set():
        return "interrupted", {}
    verdict, report, self_only = run_review(node, feature, dry)
    if STOP.is_set():
        return "interrupted", {}
    evals_ok, _ = run_evals()
    if STOP.is_set():
        return "interrupted", {}

    if node.mode == "auto" and merge:
        notify(
            f"{node.id} (auto): final/merge checkpoint — never auto-approved (INV-5) "
            "→ human validation required."
        )
    elif node.mode == "auto" and not supervised:
        if self_only:
            notify(
                f"{node.id} (auto): separation of duties impossible (reviewer = implementer's model) "
                "→ human validation required. Configure a distinct reviewer model in lab/models/registry.toml."
            )
        elif verdict == "PASS" and evals_ok:
            approval.parent.mkdir(exist_ok=True)
            # Signed like a human approval (the orchestrator has the secret) to
            # stay verifiable if the token is re-read; "auto-approved" stays in
            # the author for traceability (finding H1, auto-path consistency).
            approval.write_text(
                approvals.sign(
                    feature,
                    node.id,
                    "auto-approved (evals green + reviewer panel PASS)",
                    datetime.now().isoformat(),
                )
            )
            run_log(
                feature,
                node,
                "reviewer",
                "checkpoint auto-validated (PASS, evals green)",
            )
            notify(f"{node.id} auto-validated — report: {report.relative_to(PROJECT)}")
            return "approved", {}
        else:
            notify(
                f"{node.id} (auto): panel {verdict} / evals {'green' if evals_ok else 'RED'} → falling back to human validation"
            )

    notify(
        f"CHECKPOINT {node.id}: Owner decision → lab/engine/approve.sh {node.id} {feature.relative_to(PROJECT)} "
        f'or lab/engine/reject.sh {node.id} {feature.relative_to(PROJECT)} "reason" [Tn …] '
        f"(reviewer report: {report.relative_to(PROJECT)}, verdict {verdict})"
    )
    return _await_token(node, feature, "checkpoint")


def _await_token(node: Node, feature: Path, kind: str) -> tuple[str, dict]:
    """Block until the Owner signs `.approvals/<id>` (approve.sh) or drops
    `.approvals/<id>.rejected` (reject.sh). Shared by checkpoints and Owner-lane
    tasks. Returns ("approved", {}) or ("rejected", {reason, tasks})."""
    approval = feature / ".approvals" / node.id
    rejection = feature / ".approvals" / f"{node.id}.rejected"
    print(f"⏸  {node.id} — waiting for {approval} (or .rejected)", flush=True)
    while True:
        if STOP.is_set():  # interrupted while waiting: the checkpoint stays pending
            return "interrupted", {}
        if rejection.exists():
            info = parse_rejection(rejection)
            rejection.rename(
                rejection.parent
                / f"{node.id}.rejected.handled-{datetime.now():%Y%m%d%H%M%S}"
            )
            run_log(feature, node, "owner", f"{kind} REJECTED — {info['reason']}")
            journal(feature, event="checkpoint_rejected", id=node.id, **info)
            notify(
                f"{node.id} rejected — reopening: {', '.join(info['tasks']) or 'all the checkpoint tasks'}"
            )
            return "rejected", info
        if approval.exists():
            ok, why = approvals.verify(
                feature, node.id, approval.read_text(encoding="utf-8")
            )
            if not ok:
                # Forged token / invalid signature: discard it and keep
                # waiting for a real human validation (finding H1).
                approval.rename(
                    approval.parent / f"{node.id}.invalid-{datetime.now():%Y%m%d%H%M%S}"
                )
                journal(
                    feature, event="checkpoint_forgery_rejected", id=node.id, why=why
                )
                notify(
                    f"⛔ {node.id}: approval REJECTED ({why}) — token discarded, "
                    "still waiting for a signed human validation."
                )
                continue
            if "unsigned" in why:
                notify(f"⚠️ {node.id}: approval accepted but {why}")
            # Consumed after honoring: a token does not replay (finding H4).
            approval.rename(
                approval.parent / f"{node.id}.handled-{datetime.now():%Y%m%d%H%M%S}"
            )
            run_log(feature, node, "owner", f"{kind} validated")
            notify(f"{node.id} validated — resuming execution")
            return "approved", {}
        STOP.wait(20)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("feature", help="feature directory (contains tasks.md)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--validate", action="store_true", help="plan-lint: check tasks.md and exit"
    )
    ap.add_argument(
        "--supervised",
        action="store_true",
        help="force all checkpoints to blocking",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="ignore status approved + lint errors (not recommended)",
    )
    ap.add_argument(
        "--project",
        help="external project root where work/, code, evals and the git repo live "
        "(default: the lab repo). Equivalent to LAB_PROJECT_ROOT.",
    )
    args = ap.parse_args()

    if args.project:
        global PROJECT
        PROJECT = Path(args.project).resolve()

    # Effective policy, resolved ONCE after --project (ADR-14). Pre-flight refusals apply
    # to real runs and --dry-run, never to --validate (which only lints, policy if any).
    global POLICY, PROFILE
    POLICY, PROFILE, policy_refusals = resolve_policy(args.force)
    if policy_refusals and not args.validate:
        for m in policy_refusals:
            print(f"⛔ pre-flight: {m}", file=sys.stderr)
        return 1
    if POLICY is not None:
        apply_policy(POLICY)

    global DRY_RUN
    DRY_RUN = bool(args.dry_run)
    feature = (PROJECT / args.feature).resolve()
    fm, nodes = parse_tasks_md(feature / "tasks.md")

    try:  # nodes already done in a previous run: capability lint no longer applies
        prev = json.loads(
            (feature / ".runs" / "state.json").read_text(encoding="utf-8")
        )
        done_ids = {k for k, v in prev.items() if v == "done"}
    except (OSError, json.JSONDecodeError, AttributeError):
        done_ids = set()
    errors, warnings = validate(
        feature, fm, nodes, REGISTRY, project=PROJECT, done=done_ids, policy=POLICY
    )
    if args.validate or errors or warnings:
        print(
            f"Plan-lint — {len(nodes)} nodes, frontmatter status: {fm.get('status', '∅')}"
        )
        for w in warnings:
            print(f"  ⚠️  {w}")
        for e in errors:
            print(f"  ❌ {e}")
        if not errors and not warnings:
            print("  ✅ no problem")
        if args.validate:
            # Surface every verify: the Owner signs these commands by approving the
            # plan (they will run on the host, without a shell — finding H2).
            verifs = [(n.id, n.verify) for n in nodes if n.verify]
            if verifs:
                print("\n  Verify commands (run without a shell, to validate):")
                for nid, vcmd in verifs:
                    print(f"    {nid}: {vcmd}")
    if args.validate:
        return 1 if errors else 0
    if errors and not args.force:
        print("⛔ Invalid plan — fix it (or --force, not recommended).")
        return 1

    if fm.get("status") != "approved" and not (args.dry_run or args.force):
        print(
            f"⛔ tasks.md has status '{fm.get('status')}' — a plan must be 'approved' by the Owner before execution."
        )
        return 1

    # Fail-closed (finding H1): a plan with checkpoints requires a signing
    # secret, otherwise any .approvals/<CP> file (which an agent can write via
    # Bash) would be honored. Without a secret we REFUSE to start, except with
    # explicit opt-in LAB_ALLOW_UNSIGNED_APPROVALS=1 (back-compat / legacy).
    has_checkpoint = any(n.is_checkpoint for n in nodes)
    # .strip(): an empty/blank secret counts as absent (consistent with approvals._secret).
    secret_set = bool((os.environ.get(approvals.ENV_SECRET) or "").strip())
    allow_unsigned = os.environ.get("LAB_ALLOW_UNSIGNED_APPROVALS") == "1"
    if has_checkpoint and not secret_set and not allow_unsigned and not args.dry_run:
        print(
            "⛔ Plan with a checkpoint but LAB_APPROVAL_SECRET not set: an "
            "unsigned approval would be forgeable by an agent (finding H1). "
            "Export LAB_APPROVAL_SECRET (recommended) or, knowingly, "
            "LAB_ALLOW_UNSIGNED_APPROVALS=1 to allow unsigned tokens."
        )
        return 1

    # Pre-flight (fail-closed, before the lock): real runs AND --dry-run, never --validate.
    refusals = preflight()
    if refusals:
        for m in refusals:
            print(f"⛔ pre-flight: {m}", file=sys.stderr)
        return 1

    by_id = {n.id: n for n in nodes}
    print(f"Plan: {len(nodes)} nodes — " + ", ".join(n.id for n in nodes))
    if REGISTRY.models:
        roles_used = {
            "implementer": resolve_model("implementer", "", REGISTRY),
            "reviewer": resolve_model("reviewer", "", REGISTRY),
        }
        print(
            "Models (registry): "
            + ", ".join(f"{r}={m or 'CLI default'}" for r, m in roles_used.items())
        )

    rejections: dict[str, int] = {}
    state_f = feature / ".runs" / "state.json"
    if not args.dry_run:
        state_f.parent.mkdir(
            exist_ok=True
        )  # INV-2: a dry run creates nothing under .runs/
        # Inter-process lock (finding H6): forbids two concurrent runs on the
        # same feature (race on state.json / git index / journal / budget).
        try:
            acquire_orchestrator_lock(feature)
        except OSError as e:
            print(f"⛔ {e}", file=sys.stderr)
            return 1
    if not args.dry_run:
        journal(
            feature,
            event="run_start",
            profile=PROFILE,
            policy={
                k: {"value": v, "origin": o} for k, (v, o) in (POLICY or {}).items()
            },
        )
    if state_f.exists() and not args.dry_run:
        # Tolerant resume (finding L9): a truncated state.json (kill mid-write)
        # must not crash the resume — we start clean rather than crash.
        try:
            restored = json.loads(state_f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"⚠️  state.json unreadable ({e}) — fresh restart (all tasks pending).",
                file=sys.stderr,
            )
            restored = {}
        for nid, st in restored.items():
            if nid in by_id and st == "done":
                by_id[nid].status = "done"

    def save() -> None:
        if not args.dry_run:
            atomic_write_json(state_f, {n.id: n.status for n in nodes})

    def finish_interrupted(inflight: list[str]) -> int:
        """BHV-1: in-flight tasks go back to pending (done ones keep done), atomic state
        write, one run_interrupted event, how to resume, rc 130. Never a commit."""
        runner.terminate_all()  # a worker may have launched an agent after the handler ran
        for n in nodes:
            if n.id in inflight:
                n.status = "pending"
        save()
        sig = _SIGNALS_SEEN[0] if _SIGNALS_SEEN else "SIGINT"
        journal(feature, event="run_interrupted", inflight=inflight, signal=sig)
        print(
            f"\n⛔ Interrupted ({sig}) — {len(inflight)} in-flight task(s) back to pending: "
            f"{', '.join(inflight) or 'none'}. Nothing was committed after the signal.\n"
            f"   Resume: python3 lab/engine/orchestrate.py {args.feature} "
            "(done tasks are kept in .runs/state.json).",
            flush=True,
        )
        return 130

    if not args.dry_run:
        install_signal_handlers()

    while any(n.status == "pending" for n in nodes):
        if STOP.is_set():
            return finish_interrupted([])
        if BUDGET_USD and COST_TOTAL["usd"] >= BUDGET_USD:
            notify(
                f"⛔ Budget reached: ${COST_TOTAL['usd']:.2f} ≥ ${BUDGET_USD:.2f} ({BUDGET_SOURCE}) — "
                "stopping before the next wave. Restart after review (resume via .runs/state.json)."
            )
            journal(
                feature,
                event="budget_stop",
                spent_usd=round(COST_TOTAL["usd"], 4),
                cap_usd=BUDGET_USD,
            )
            return 1
        ready = [
            n
            for n in nodes
            if n.status == "pending"
            and all(by_id[d].status == "done" for d in n.depends_on if d in by_id)
        ]
        if not ready:
            print(
                "⛔ Deadlock: no ready task. Check the depends_on graph (--validate)."
            )
            return 1

        cps = [n for n in ready if n.is_checkpoint]
        tasks = [n for n in ready if not n.is_checkpoint]

        if tasks:
            wave = ", ".join(n.id for n in tasks)
            print(f"\n=== Parallel wave: {wave} ===")
            with RUNNING_LOCK:
                RUNNING_FILES.clear()
            with ACTIVE_COND:  # registered before any starts: no task judges too early
                ACTIVE.clear()
                JUDGING.clear()
                ACTIVE.update(n.id for n in tasks[:MAX_PARALLEL])
            ex = ThreadPoolExecutor(max_workers=MAX_PARALLEL)
            futs = {ex.submit(run_task, n, feature, args.dry_run): n for n in tasks}
            waiting = set(futs)
            inflight: list[str] = []
            try:
                while waiting:
                    finished, waiting = wait(waiting, timeout=0.2)
                    if STOP.is_set():
                        # Queued futures never start (E-3); late agent launches are killed.
                        waiting = {f for f in waiting if not f.cancel()}
                        runner.terminate_all()
                    for fut in finished:
                        n = futs[fut]
                        res = fut.result()
                        if res == "interrupted":
                            inflight.append(n.id)
                            continue
                        if res in ("interrupted_waiting", "not_started"):
                            continue  # never in flight (BHV-1b / not started): stays pending
                        n.status = res
                        if n.status in ("failed", "blocked"):
                            skip_dependents(n, nodes)
                        save()
            finally:
                ex.shutdown(wait=True, cancel_futures=True)
            if STOP.is_set():
                return finish_interrupted([n.id for n in tasks if n.id in inflight])
        for cp in cps:
            outcome, info = wait_checkpoint(
                cp,
                feature,
                args.dry_run,
                args.supervised,
                merge=is_merge_checkpoint(cp, nodes),
            )
            if outcome == "interrupted":  # BHV-1b: the checkpoint stays pending
                return finish_interrupted([])
            if outcome == "approved":
                cp.status = "done"
            else:  # rejected — on_reject: back to the targeted tasks with a comment
                rejections[cp.id] = rejections.get(cp.id, 0) + 1
                if rejections[cp.id] > MAX_CP_REJECTS:
                    cp.status = "failed"
                    notify(
                        f"{cp.id}: rejected {rejections[cp.id]} times — stopping, manual resume required"
                    )
                    skip_dependents(cp, nodes)
                else:
                    targets = info["tasks"] or list(cp.depends_on)
                    for tid in targets:
                        t = by_id.get(tid)
                        if t and not t.is_checkpoint:
                            t.status = "pending"
                            t.rework = (
                                f"\n\n⚠️ OWNER REVIEW FEEDBACK (rejection {cp.id}): {info['reason']}\n"
                                f"Fix accordingly before re-delivering."
                            )
                    cp.status = "pending"  # re-triggered when the tasks come back done
            save()

    bad = [n for n in nodes if n.status in ("failed", "blocked", "skipped")]
    print("\n=== Summary ===")
    for n in nodes:
        mark = {"done": "✅", "failed": "❌", "blocked": "🛑", "skipped": "⏭"}.get(
            n.status, "·"
        )
        print(f"  {mark} {n.id} — {n.status}")
    print(f"  Σ agent cost: ${COST_TOTAL['usd']:.2f} (detail: .runs/journal.jsonl)")
    journal(
        feature,
        event="run_end",
        cost_usd_total=round(COST_TOTAL["usd"], 4),
        statuses={n.id: n.status for n in nodes},
    )
    if bad:
        notify(
            f"{feature.name}: run finished with {len(bad)} node(s) not done — "
            "answer the blocks then restart (resume via .runs/state.json)."
        )
        return 1
    notify(f"🎉 {feature.name}: all tasks are done. Merge = human decision (final CP).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
