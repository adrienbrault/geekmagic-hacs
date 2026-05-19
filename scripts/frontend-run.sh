#!/usr/bin/env bash
# Run an npm script inside the frontend directory, installing dependencies
# first if node_modules is missing.
#
# Usage: ./scripts/frontend-run.sh <npm-script-name>
# Example: ./scripts/frontend-run.sh typecheck
#
# Bootstrapping `npm ci` on demand makes the pre-commit hooks work in fresh
# clones and CI environments without requiring contributors to remember a
# manual setup step.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <npm-script-name>" >&2
  exit 2
fi

cd "$(dirname "$0")/../custom_components/geekmagic/frontend"

if [[ ! -d node_modules ]]; then
  echo "frontend: node_modules missing, running npm ci..." >&2
  npm ci --silent
fi

exec npm run --silent "$1"
