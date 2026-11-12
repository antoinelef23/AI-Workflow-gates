# Sandbox runner — hard confinement for agents

The orchestrator runs agents through an `AgentRunner` interface (`lab/engine/runner.py`).
The default `claude-cli` runner executes on the host; the **sandbox** runner
(`lab/engine/sandbox_runner.py`, `LAB_RUNNER=sandbox`) runs the same `claude -p` call
inside a hardened container.

## Why it exists

An implementer that runs its own tests inherently has code execution. On the host
that means it could read the Owner's dotfiles/keychain to steal `LAB_APPROVAL_SECRET`
and then **forge a signed checkpoint approval** — so the signed-approval gate is only
defense-in-depth on the host (findings M3/M4). The sandbox removes the agent's reach:

- **Only the repo is mounted** (`<repo>:/workspace:rw`). `$HOME`, dotfiles, keychain,
  and the rest of the host filesystem are unreachable.
- **The approval secret is never passed in** — a curated env allowlist
  (`SANDBOX_ENV_ALLOW`) forwards only what the agent needs (model credentials, locale,
  proxy), and `LAB_APPROVAL_SECRET` is explicitly excluded.
- **Egress is allowlisted** — the container joins a restricted network so it can reach
  only the model API and the package registry, not the open internet.
- **Least privilege** — host uid (non-root), `--read-only` rootfs + tmpfs, `--cap-drop ALL`,
  `--security-opt no-new-privileges`, pids/memory limits.

With the secret unreachable and egress closed, an unsigned token the agent writes is
rejected by the orchestrator (which verifies on the host, with the secret). The boundary
holds.

## Enable

```bash
# 1. Build the agent image
docker build -t lab-agent:latest -f deploy/sandbox/Dockerfile.agent .

# 2. Create the egress-restricted network (see "Egress" below)
docker network create lab-egress   # + allowlist proxy, or an internal network

# 3. Run the orchestrator with the sandbox runner
LAB_RUNNER=sandbox LAB_APPROVAL_SECRET=… python3 lab/engine/orchestrate.py work/my-feature
```

## External instance

With `--project <instance>` the sandbox mounts **two** directories:

| Host | Container | Mode |
|---|---|---|
| the instance | `/workspace` (agent cwd) | read-write |
| the kit root | `/kit` | **read-only** |

The engine then passes `--plugin-dir /kit/lab/plugin` and
`--settings /kit/lab/engine/run_settings.json`, so the guardrails apply in the container exactly as
on the host, even though the instance has no `.claude/` and no `CLAUDE.md`. Extra directories that
point inside the kit are translated to `/kit/…`; any other host path is refused. The agent can read
the kit but not alter it. In kit mode (no `--project`) plugin and settings stay cwd-relative
(`lab/plugin`, `lab/engine/run_settings.json`).

```bash
LAB_RUNNER=sandbox LAB_APPROVAL_SECRET=… lab run work/my-feature --project <instance>
```

The `regulated` profile requires this: `sandbox_required = true` makes a run without
`LAB_RUNNER=sandbox` refuse to start (rc 1). See
[choose-an-organization-profile.md](choose-an-organization-profile.md) and
[policy-profiles.md](../reference/policy-profiles.md). Setup of the instance:
[activate-an-instance.md](activate-an-instance.md).

Tuning env: `LAB_SANDBOX_IMAGE` (default `lab-agent:latest`), `LAB_SANDBOX_NETWORK`
(default `lab-egress`), `LAB_SANDBOX_MEMORY` (default `2g`). The agent's model
credential (`ANTHROPIC_API_KEY`) is forwarded if present; it is the agent's own
credential, distinct from the approval secret.

## Egress allowlist

`--network none` would be maximal isolation but breaks the model call, so the runner
defaults to a named network you control. Two ways to make it an allowlist:

1. **Filtering proxy (recommended, portable):** run a small allowlisting forward proxy
   (tinyproxy/squid with an allow list of `api.anthropic.com` + your package index) on
   an internal docker network, and forward via `HTTPS_PROXY`/`HTTP_PROXY` (both are in
   `SANDBOX_ENV_ALLOW`). The agent has no direct route out.
2. **Firewalled network:** an internal docker network plus host nftables/iptables rules
   that permit only the model API and registry CIDRs.

## Validation status

The security-critical part — the `docker run` argv (mounts, dropped caps, read-only
rootfs, **secret excluded**, host uid) — is built by the pure function
`sandbox_runner.build_docker_argv` and unit-tested in `tests/test_runner.py` (no
Docker needed).

**Validated end-to-end on Docker** (server 29.x): with `LAB_APPROVAL_SECRET` set on
the host, a container run via `SandboxedClaudeRunner` reports the secret **absent**
inside the container, the repo mounted at `/workspace`, and no host `$HOME` leak —
i.e. the agent cannot reach the secret. Full *production* runs additionally require
the agent image (`deploy/sandbox/Dockerfile.agent`) and `claude` auth inside it, plus
the egress-allowlist proxy (above), which is operator infrastructure and not bundled.
