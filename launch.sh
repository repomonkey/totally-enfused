#!/bin/bash
# Launch Totally Enfused using the project virtualenv
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
.venv/bin/python -m backend.main "$@"
