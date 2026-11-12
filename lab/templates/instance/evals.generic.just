# No eval runner known for this stack: fail closed, never green by absence.
evals:
    #!/usr/bin/env bash
    echo 'no evals configured — define `evals` and `evals-collect`' >&2
    exit 1
