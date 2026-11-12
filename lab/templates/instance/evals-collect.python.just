# Lists the evals as `path::test_eval_n_…` node-ids (consumed by the orchestrator).
evals-collect:
    #!/usr/bin/env bash
    uv run pytest -m eval --collect-only -q
