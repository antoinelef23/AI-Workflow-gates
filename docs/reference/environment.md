# Environment variables reference

Every environment variable read by the lab's `lab/engine/`. Variables are read at
process start; export them before invoking `just` / the script. Security-sensitive
variables are marked **(sec)** — they govern the approval boundary, secrets, or the
sandbox confinement.

## Variables

| Variable | Default | Effect | Read by |
| --- | --- | --- | --- |
| `LAB_APPROVAL_SECRET` **(sec)** | unset | HMAC key for signed checkpoint approvals. Unset: unsigned tokens are accepted (back-compat) and the orchestrator refuses a plan with a checkpoint unless `LAB_ALLOW_UNSIGNED_APPROVALS=1`. Set: a token without a valid HMAC signature is rejected. Removed from sub-agent env (`orchestrate.py` strips it from `child_env`; the sandbox never forwards it). | `approvals.py`, `orchestrate.py`, `approve.sh`, `sandbox_runner.py` |
| `LAB_ALLOW_UNSIGNED_APPROVALS` **(sec)** | unset | `=1` lets the orchestrator run a plan that has a checkpoint while `LAB_APPROVAL_SECRET` is unset (knowingly accepting unsigned, forgeable tokens). Any other value: a checkpoint plan without the secret is refused. | `orchestrate.py` |
| `LAB_RUNNER` | `claude-cli` | Selects the execution backend: `claude-cli` (host) or `sandbox` (hardened container). Any other value raises `ValueError`. | `runner.py`, `orchestrate.py` |
| `LAB_ROOT` | repo root (`lab/engine/..`) | Data/config root: model registry, golden files, outputs. Override for tests. Framework code is resolved via `__file__`, not this. | `orchestrate.py`, `eval_models.py` |
| `LAB_BUDGET_USD` | `0` | USD cost cap for an orchestrator run. `0` = no cap. Run aborts when cumulative cost ≥ the cap. | `orchestrate.py` |
| `LAB_TASK_TIMEOUT` | `2400` (orchestrate), `1800` (eval_models) | Wall-clock timeout in seconds per agent invocation. | `orchestrate.py`, `eval_models.py` |
| `LAB_GCHAT_WEBHOOK` | unset | Team-chat webhook URL for checkpoint/block notifications. No-op if unset; failures are swallowed. | `notify.py` |
| `LAB_NO_NOTIFY` | unset | Any truthy value silences all external notifications (chat + macOS banner). Used by tests/CI. | `notify.py` |
| `LAB_EVALS_COLLECTED_FILE` | unset | Test seam: path whose contents replace `pytest --collect-only` output for the anti-empty-gate / eval-ID coverage check. Read as-is. | `orchestrate.py` |
| `LAB_MODEL_SHIM` | unset | `=1` allows `eval_models.py` to run without `--live` using a deterministic `claude` shim on `PATH` (tests). Without it and without `--live`, the campaign refuses to run. | `eval_models.py` |
| `LAB_BRAND_DENYLIST` | `lab/engine/brand_denylist.txt` | Override the brand/proper-noun denylist path (tests). | `brand_guard.py` |
| `LAB_SANDBOX_IMAGE` | `lab-agent:latest` | Container image used by the sandbox runner. | `sandbox_runner.py` |
| `LAB_SANDBOX_NETWORK` **(sec)** | `lab-egress` | Docker network for the sandbox. Defaults to a named egress-restricted network the operator creates (model API + package registry only). `none` would break the model call. | `sandbox_runner.py` |
| `LAB_SANDBOX_MEMORY` | `2g` | Memory limit for the sandbox container. | `sandbox_runner.py` |

## Sandbox env allowlist

When `LAB_RUNNER=sandbox`, only the variables in `SANDBOX_ENV_ALLOW`
(`lab/engine/sandbox_runner.py`) are forwarded into the container.
`LAB_APPROVAL_SECRET` is excluded by allowlist and explicitly popped
(`curate_env`).

| Forwarded variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` **(sec)** | Agent's model credential. |
| `ANTHROPIC_AUTH_TOKEN` **(sec)** | Agent's model credential. |
| `ANTHROPIC_BASE_URL` | Model API endpoint override. |
| `LANG`, `LC_ALL`, `TZ` | Locale / timezone. |
| `CI` | CI marker. |
| `NO_COLOR` | Disables colored output. |
| `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` | Egress proxy configuration. |
| `UV_CACHE_DIR` | `uv` dependency cache location. |

Variables outside this set — including `LAB_APPROVAL_SECRET` — never reach the
sandboxed agent.

## See also

- [run-the-orchestrator.md](../how-to/run-the-orchestrator.md) — set these variables for a run.
- [use-the-sandbox.md](../how-to/use-the-sandbox.md) — build the image and the `lab-egress` network.
- [cli.md](cli.md) — command-line flags (`--live`, `--budget`, …).
