# No eval collector known for this stack: fail closed.
evals-collect:
    #!/usr/bin/env bash
    echo 'no evals configured — define `evals` and `evals-collect`' >&2
    exit 1
