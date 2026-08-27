from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "ha_bridge" / "config.yaml"
CHANGELOG_PATH = ROOT / "ha_bridge" / "CHANGELOG.md"
BASE_VERSION_PATTERN = re.compile(r"^\d\.\d\.\d$")
ADDON_VERSION_PATTERN = re.compile(r"^\d\.\d\.\d-[1-9]\d*$")
CONFIG_VERSION_PATTERN = re.compile(r'^(version:\s*")[^"]+("\s*)$', re.MULTILINE)


def addon_version(base_version: str, revision: int) -> str:
    if not BASE_VERSION_PATTERN.fullmatch(base_version):
        raise SystemExit(f"invalid HA Bridge base version: {base_version}")
    if revision < 1:
        raise SystemExit("Add-on revision must be at least 1")
    return f"{base_version}-{revision}"


def read_current_version() -> str:
    source = CONFIG_PATH.read_text(encoding="utf-8")
    match = re.search(r'^version:\s*"([^"]+)"\s*$', source, flags=re.MULTILINE)
    if not match or not ADDON_VERSION_PATTERN.fullmatch(match.group(1)):
        raise SystemExit("invalid or missing Add-on version in config.yaml")
    return match.group(1)


def set_version(base_version: str, revision: int) -> str:
    target = addon_version(base_version, revision)
    source = CONFIG_PATH.read_text(encoding="utf-8")
    updated, count = CONFIG_VERSION_PATTERN.subn(rf'\g<1>{target}\g<2>', source, count=1)
    if count != 1:
        raise SystemExit("unable to update Add-on version in config.yaml")
    CONFIG_PATH.write_text(updated, encoding="utf-8")

    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    heading = f"## {target}"
    if heading not in changelog:
        entry = (
            f"{heading}\n\n"
            "- 修复了一些已知内容。\n\n"
        )
        marker = "# 更新日志\n\n"
        if not changelog.startswith(marker):
            raise SystemExit("unexpected Add-on CHANGELOG.md header")
        CHANGELOG_PATH.write_text(marker + entry + changelog[len(marker) :], encoding="utf-8")
    return target


def check_version(base_version: str, revision: int) -> str:
    expected = addon_version(base_version, revision)
    current = read_current_version()
    if current != expected:
        raise SystemExit(f"Add-on version mismatch: expected {expected}, got {current}")
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    if f"## {expected}" not in changelog:
        raise SystemExit(f"Add-on changelog is missing {expected}")
    print(f"Add-on version surfaces aligned: {expected}")
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the HA Bridge Add-on release version.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("current")
    for command in ("set", "check"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("base_version")
        command_parser.add_argument("revision", type=int)
    args = parser.parse_args()

    if args.command == "current":
        print(read_current_version())
    elif args.command == "set":
        print(set_version(args.base_version, args.revision))
    elif args.command == "check":
        check_version(args.base_version, args.revision)


if __name__ == "__main__":
    main()
