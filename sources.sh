#!/usr/bin/env bash
#
# Parse all references from README.md to list all sources.

echo 'Current sources:'
grep -E "^- https:" README.md | awk '{ print $2 }'

echo '---'
echo 'Pending sources:'
echo 'https://bitcoinops.org/en/topics/responsible-disclosures/'
echo 'https://lightning.community/SI/'
