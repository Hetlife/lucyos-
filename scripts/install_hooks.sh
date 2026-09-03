#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ln -sf "${REPO}/scripts/pre-commit" "${REPO}/.git/hooks/pre-commit"
chmod +x "${REPO}/scripts/pre-commit"
echo "pre-commit hook installed: secret scan + test suite"
