# Review CP-5 — panel of 3 — aggregated verdict: BLOCK (BLOCK, WARN, WARN)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: BLOCK

# CP-5 review (merge): correctness lens

**Verdict: BLOCK.** The spec behaviours I checked are correct, but `just gate-ci` is red at HEAD. CP-5 requires it green, and the cause is a one-line formatting issue in the T14 test file.

I ran the kit suites directly. I could not run `just` itself because permission was refused in this session, so I ran each part of `gate-ci` by hand:

| Check | Result |
|---|---|
| Full test suite | 216 passed |
| Evals (`-m eval`) | 60 passed |
| `examples/devis` evals | 1063 passed |
| `examples/booking` evals | 8 passed |
| `content_guard` on spec and design | substance identical |
| `uv lock --check` | green |
| `ruff check` | green |
| `ruff format --check` | **red** (1 file) |
| `brand_guard --all` | green, but the denylist is empty, so it enforces nothing |
| `trajectory_guard` | **2 violations** (known) |

## ✅ Conformant (INV/BHV, values and bounds)

**Kit root and version (INV-7, ADR-5)**
- `lab/engine/kit.py:27-39` resolves the root in the specified order: `LAB_ROOT`, then `parents[2]` with the marker, then rc 1. It never walks up the tree.
- `kit.py:42-57` reads the version from installed metadata first, then falls back to `pyproject.toml`.

**`lab init` (BHV-1 and its edge cases, INV-7, INV-8)**
- **Files created:** it writes only `.lab/lab.toml`, `work/README.md`, `work/_templates/*.template.md` and the two justfile recipes (`lab/engine/lab_init.py:169-179`). That matches EX-4, and nothing goes under `.claude/`, `CLAUDE.md` or `AGENTS.md`.
- **Never overwrites:** existing files are classified `create`, `identical` or `skip`, never overwritten (`:156-166`). A second run prints "0 changement" (`:283`), which covers BHV-1c.
- **`--dry-run` (BHV-1d):** prints the plan and returns before `apply_plan` (`:272-278`).
- **Existing justfile (BHV-1e):** it is read with `--justfile … --dump`, and a file that does not parse means nothing is written (`:93-118`). Existing recipes are skipped. Appended recipes are re-read afterwards, and the original bytes are restored if that fails (`:220-239`).
- **Non-Python projects (BHV-1b):** both recipes fail closed with exit 1 (`lab/templates/instance/*.generic.just`).
- **`--profile`:** it is mandatory, and a missing or unknown value gives rc 1 listing the three profiles (`:260-264`), as decided in OQ-11.
- **Pin:** `.lab/lab.toml` records `kit_version` from `kit_version()` (`:52-57`). Its reader checks `schema_version`, `kit_version` and `profile`, and errors explicitly when the file is missing (`:60-87`).

**Guardrails on every run (BHV-2, BHV-2a, INV-1, EX-5)**
- **Every agent call:** `run_claude` passes `**guardrail_options()` (`orchestrate.py:303`). Both the implementer call (`:687`) and the reviewer call (`:813`) go through it.
- **Kit paths:** plugin and settings come from the kit root (LAB), never from PROJECT. They are absolute paths for an external instance and cwd-relative in kit mode (`orchestrate.py:203-215`, ADR-10).
- **Argv:** `claude_argv` adds the three options only when asked, so the argv is unchanged otherwise, and it never passes `--bare` (`lab/engine/runner.py:48-103`).
- **Pre-flight, in order (`orchestrate.py:229-271`):**
  - plugin directory, rules file and run settings must exist;
  - with `--project`: `lab.toml` is read and the pin compared, refusing with the spec's literal message `plugin X ≠ pinned kit Y` (`:251-253`, observation O-1);
  - `claude` CLI version ≥ 2.1.295;
  - sandbox runner together with `--project` is refused.
- **When the pre-flight runs:** before the lock, for real runs and `--dry-run`, and never for `--validate` (that path returns at `:1012`).
- **Run denies:** `lab/engine/run_settings.json` holds exactly the two `Edit` denies and no `hooks` key, as I-3 and ADR-2 require.
- **Versions agree:** pyproject, `plugin.json` and the marketplace entry are all `0.1.0` (I-19).

**Plugin hooks (ADR-4, I-4, BHV-2b)**
- `hooks.json` declares PreToolUse, SessionStart, PostToolUse, Stop and SubagentStop, all through `${CLAUDE_PLUGIN_ROOT}`.
- `guard_paths.sh` catches both relative and absolute paths, because it pattern-matches on `"/$FILE"`. It fails closed when it cannot parse its input.
- `eval_gate.sh:16` now also runs when `.lab/lab.toml` exists, which fixes the I-4 `:15` anti-pattern.
- `session_start.sh` prints the rules file.

**Rest of the plan**
- **Single source of rules (T12):** `CLAUDE.md` points to `lab/plugin/rules/hard-rules.md` and no longer restates the rules. The sdlc_rework tests (EVAL-5 of the earlier sdlc-rework feature, plus the `AGENTS.md` size limit) are green.
- **Model-eval harness (T13):** argv is built with `claude_argv`, and the single `--add-dir` is `lab/plugin/agents`, as the CP-4 reject notes required.
- **Examples move (INV-9):** both example instances pin `kit_version = "0.1.0"`, and their evals are green on their own.
- **Docs (T14):** `docs/reference/cli.md` and `docs/how-to/activate-an-instance.md` match the code (refusal messages, the `--profile` rule, sandbox refused with `--project`, "0 changement").

## ⚠️ To arbitrate

1. **The PreToolUse guard does not catch NotebookEdit.**
   - **Bug:** `lab/plugin/hooks/guard_paths.sh:7` reads only `tool_input.file_path`, but NotebookEdit sends its path as `notebook_path`.
   - **Effect:** a notebook write under `.approvals/` gets an empty path and exits 0, so it is allowed. I could not run the script here (permission refused), so this comes from reading the code.
   - **Where it matters:** in orchestrated runs, the `Edit(**/.approvals/**)` deny in `run_settings.json` still covers it. Interactive sessions rely on this hook alone, so INV-1 is incomplete there for that tool.
   - **Fix:** fall back to `notebook_path`, and add a test case for it.
2. **The eval gate skips non-Python instances.**
   - `eval_gate.sh:23` only runs the evals when a changed file ends in `.py`, `.toml`, `.ts`, `.js` or similar.
   - A non-Python instance with `.lab/lab.toml` that changes `.go` or `.java` files exits 0 without running anything.
   - So the I-4 fix only takes effect when one of those extensions changed. This filter predates the feature, but it limits "identical guardrails" (INV-1) for non-Python instances.
3. **The trajectory guard is still red, and CP-5 lists it as a criterion.** Neither violation is in the code, and both were already raised at CP-4:
   - ⛔ T15 has a `task_done` entry with no attempt before it (an Owner-lane entry written before `94f273e`).
   - ⛔ `192203b9` (T7) touched `progress.md` outside its scope.
   - ⚠️ T13 took 3 attempts; both retries were Owner rejections, not the implementer looping.

   The Owner should waive these explicitly in the PR, or record why.
4. **The brand guard enforces nothing.** `brand_guard` reports an empty denylist (`lab/engine/brand_denylist.txt`), so "check-brand green" proves nothing for this merge.
5. **Still to do, from the CP-5 list:** attach the CP-4 scorecards to the PR, decide on the `v0.1.0` tag, and announce O-6 to the team: a kit session without `--plugin-dir lab/plugin` has no guardrails.

## ❌ Blockers

1. **`gate-ci` is red: `ruff format --check` fails on `tests/fde_kit/test_doc_pointers.py:39`.**
   - T14 (`10293ef`) added a regex line over 88 characters that ruff wants to wrap.
   - `lint-check` (`justfile:57-59`) is the first dependency of `gate-ci` (`justfile:121`), so the whole gate fails.
   - The orchestrator did not catch it because T14's `verify` only runs the pointer test, and `just evals` does not lint.
   - **Fix:** run `uv run ruff format tests/fde_kit/test_doc_pointers.py`. That is a whitespace-only change inside T14's `files_touched`, so it is a targeted reject: `lab/engine/reject.sh CP-5 work/fde-kit "ruff format test_doc_pointers.py" T14`.

VERDICT: BLOCK

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: WARN

{"duration_api_ms":92660,"stop_reason":"stop_sequence","session_id":"f3386cec-e388-446a-80d2-f95ba9a693bb","total_cost_usd":2.5153845,"usage":{"input_tokens":44,"cache_creation_input_tokens":118893,"cache_read_input_tokens":2275719,"output_tokens":7535,"output_tokens_details":{"thinking_tokens":2447},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":118893,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iterations":[{"input_tokens":2,"output_tokens":324,"cache_read_input_tokens":118068,"cache_creation_input_tokens":825,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":825},"type":"message"}],"speed":"standard","fallback_credit":null},"modelUsage":{"claude-opus-4-8":{"inputTokens":44,"outputTokens":7535,"cacheReadInputTokens":2275719,"cacheCreationInputTokens":118893,"webSearchRequests":0,"costUSD":2.5153845,"contextWindow":1000000,"maxOutputTokens":64000,"thinkingTokens":2447,"cacheCreationEphemeral5mInputTokens":0,"cacheCreationEphemeral1hInputTokens":118893,"canonicalModel":"claude-opus-4-8","provider":"firstParty","costBasis":"list"}},"permission_denials":[{"tool_name":"Bash","tool_use_id":"toolu_01GHweRmmHo4S5qR7nsHWn31","tool_input":{"command":"echo \"=== .claude/ tracked? ===\" && git ls-files .claude | head && echo \"(empty = good)\" && echo \"=== lab/plugin tree ===\" && git ls-files lab/plugin | head -50 && echo \"=== examples/ top ===\" && git ls-files examples | sed 's#\\(examples/[^/]*/[^/]*\\).*#\\1#' | sort -u","description":"Check plugin and examples structure"}},{"tool_name":"Bash","tool_use_id":"toolu_017WdLUivkMnfufC7nZEdGSJ","tool_input":{"command":"git ls-files examples/ | awk -F/ '{print $1\"/\"$2\"/\"$3}' | sort -u","description":"List examples structure third level"}},{"tool_name":"Bash","tool_use_id":"toolu_01BFdghnCzgBg5LUeKNMkzeo","tool_input":{"command":"for d in examples/devis examples/booking; do echo \"=== $d ===\"; git ls-files \"$d\" | grep -E '(pyproject.toml|uv.lock|lab.toml|justfile|work/[^_])' | head -20; done","description":"Check examples standalone instance files"}},{"tool_name":"Bash","tool_use_id":"toolu_015DG9Z6QxNqWDw7JyNQt7GV","tool_input":{"command":"echo \"=== check-brand ===\" && python3 lab/engine/brand_guard.py --all 2>&1 | tail -5; echo \"rc=$?\" && echo \"=== check-lock ===\" && uv lock --check 2>&1 | tail -3","timeout":120000,"description":"Run brand guard and lockfile check"}},{"tool_name":"Bash","tool_use_id":"toolu_01GRMJ4qgdDQ2YefkPkyuEed","tool_input":{"command":"python3 lab/engine/brand_guard.py --all; echo \"brand rc=$?\"","description":"Run brand guard"}},{"tool_name":"Bash","tool_use_id":"toolu_01R2udqF7VNmhP9Hf83t7Mz6","tool_input":{"command":"uv lock --check 2>&1 | tail -3; echo \"lock rc=$?\"","description":"Check lockfile freshness"}},{"tool_name":"Bash","tool_use_id":"toolu_012jU81JBqwWXh88SSr2c1NA","tool_input":{"command":"python3 lab/engine/orchestrate.py work/fde-kit --validate > /tmp/claude-0/-home-user-AI-Workflow-gates/f3386cec-e388-446a-80d2-f95ba9a693bb/scratchpad/planlint.txt 2>&1; echo \"exit=$?\"; head -40 /tmp/claude-0/-home-user-AI-Workflow-gates/f3386cec-e388-446a-80d2-f95ba9a693bb/scratchpad/planlint.txt","description":"Capture plan-lint exit code and header"}},{"tool_name":"Bash","tool_use_id":"toolu_01G1G5yqctwAQN9zkZGvPooQ","tool_input":{"command":"python3 lab/engine/orchestrate.py work/fde-kit --validate > /tmp/claude-0/-home-user-AI-Workflow-gates/f3386cec-e388-446a-80d2-f95ba9a693bb/scratchpad/planlint.txt 2>&1\necho \"exit=$?\"\nhead -25 /tmp/claude-0/-home-user-AI-Workflow-gates/f3386cec-e388-446a-80d2-f95ba9a693bb/scratchpad/planlint.txt","description":"Capture plan-lint exit code and header"}},{"tool_name":"Bash","tool_use_id":"toolu_01KW1757wBBLapTQW9rEC3Hk","tool_input":{"command":"python3 lab/engine/orchestrate.py work/fde-kit --validate >/dev/null 2>&1; echo \"plan-lint exit=$?\"","description":"Get plan-lint exit code"}}],"terminal_reason":"api_error","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":true,"num_turns":32,"subtype":"success","api_error_status":429,"api_error":"usage_limit_reached","result":"You've hit your 5-hour limit · resets 6:50pm (UTC)","type":"result","duration_ms":121031,"uuid":"4f079477-72e2-41fb-8d3d-5af334b4e010","process_turn_index":0,"queued_turn_count":0,"result_index":0,"process_start_tuning":0}


---

## Panelist 3 — claude-sonnet-4-6 — lens: edge cases & robustness: extreme inputs, errors, does the deliverable actually run
VERDICT: WARN

{"duration_api_ms":0,"stop_reason":"stop_sequence","session_id":"0e951623-32c9-4e3a-8a9b-6cbddb3e1f1c","total_cost_usd":0,"usage":{"output_tokens_details":{"thinking_tokens":0},"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],"speed":"standard","fallback_credit":null},"modelUsage":{},"permission_denials":[],"terminal_reason":"api_error","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":true,"num_turns":1,"subtype":"success","api_error_status":429,"api_error":"usage_limit_reached","result":"You've hit your 5-hour limit · resets 6:50pm (UTC)","type":"result","duration_ms":306,"uuid":"910c56f7-8aba-437c-bebd-ca7a95499167","process_turn_index":0,"queued_turn_count":0,"result_index":0,"process_start_tuning":0}
