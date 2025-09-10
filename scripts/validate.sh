#!/usr/bin/env bash
set -euo pipefail
need(){ command -v "$1" >/dev/null 2>&1 || { echo "Missing $1"; exit 1; }; }
need jq
if command -v ajv >/dev/null 2>&1; then
  ajv validate -s schema/redesign.schema.json -d plans/*.json
else
  echo "ajv not found; checking JSON well-formedness via jq."
  find plans -name '*.json' -print0 | xargs -0 -n1 jq empty
fi
echo "OK"
