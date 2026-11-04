#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd -P)
cd "$project_root"
python3 -m unittest discover -s tests -p test_release_flow.py
sh -n release/publish_addon_release.sh
sh -n release/verify_addon_upgrade.sh
git diff --check
printf 'Local Add-on checks passed; no publish or remote preflight was run.\n'
