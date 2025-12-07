#!/usr/bin/env bash

# Parse README.md to create the index for copy-paste.

while IFS= read -r heading; do
  title=$(echo "$heading" | sed -E 's/^## (.*)/\1/')
  link=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_]+/-/g')
  echo "- [$title](#$link)"
done < <(grep '##' README.md)
