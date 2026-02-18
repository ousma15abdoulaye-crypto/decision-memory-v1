#!/bin/bash
# Script to regenerate SHA256SUMS.txt for freeze v3.3.2 under Linux
# This ensures consistent checksums regardless of OS (CRLF vs LF)

set -e

cd docs/freeze/v3.3.2

# Find all .md files and the ADR file, excluding SHA256SUMS.txt itself
find . -type f \( -name "*.md" -o -name "*.txt" \) ! -name "SHA256SUMS.txt" | sort | xargs sha256sum > SHA256SUMS.txt

echo "✅ SHA256SUMS.txt regenerated"
cat SHA256SUMS.txt
