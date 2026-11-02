#!/bin/bash
# Run the mirror locally. Uses Python if available, else Node.
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  exec python3 serve.py
elif command -v node >/dev/null 2>&1; then
  exec node serve.mjs
else
  echo "Need python3 or node installed."; exit 1
fi
