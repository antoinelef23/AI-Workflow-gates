# Status line — orchestrator run state

`lab/plugin/statusline.py` renders the Claude Code status line. Beyond the model name, it
surfaces the **live state of the orchestrator** so you can see, at a glance, where an
autonomous run is without tailing `run.log`.

## What it shows

Claude Code pipes session JSON on stdin; the script reads it and scans
`work/*/.runs/state.json` (the flat `{node_id: status}` map written by
`lab/engine/orchestrate.py`), picking the most-recently-modified feature.

```
Opus 4.8  🔬 devis-pose · ▶ T3 running · 4/9
Opus 4.8  🔬 devis-pose · ⏸ T5 blocked · 4/9     ← a blocker/failure is surfaced first
Opus 4.8  🔬 devis-pose · ✓ all done
```

- The **spotlight** node is the most urgent: `failed` → `blocked` → `running` (in that
  order), so an action-needed state is never hidden behind progress.
- `done/total` is the wave progress. When everything is `done`, it collapses to `✓ all done`.
- Glyphs: `▶` running · `✓` done · `✗` failed · `⏸` blocked · `⏭` skipped · `·` pending.

If no run exists, only the model name shows. The script is read-only, stdlib-only, and
never raises — a broken status line must not break the session.

## Enable / disable

A plugin cannot define the main status line, so the FDE wires it once in their **user** settings
(`~/.claude/settings.json`; nothing in the kit repo or in the instance):

```json
"statusLine": { "type": "command", "command": "python3 /path/to/fde-kit/lab/plugin/statusline.py" }
```

`/path/to/fde-kit` is the kit checkout or the installed plugin directory. Remove that block to
disable. Test it manually by feeding it the session JSON:

```bash
echo '{"model":{"display_name":"Opus 4.8"},"workspace":{"project_dir":"'"$PWD"'"}}' \
  | python3 lab/plugin/statusline.py
```
