#!/usr/bin/env python3
"""Validate or install this vault as a local Codex plugin bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from wiki_common import ROOT


PLUGIN_MANIFEST = ROOT / ".codex-plugin/plugin.json"


def load_manifest() -> dict:
    if not PLUGIN_MANIFEST.exists():
        raise SystemExit("missing .codex-plugin/plugin.json")
    data = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    for key in ["name", "version", "description", "skills"]:
        if key not in data:
            raise SystemExit(f"plugin manifest missing key: {key}")
    skills_path = ROOT / data["skills"]
    if not skills_path.exists():
        raise SystemExit(f"plugin skills path does not exist: {data['skills']}")
    return data


def copy_plugin(target_root: Path, name: str) -> Path:
    target = target_root.expanduser().resolve() / name
    if target.exists():
        shutil.rmtree(target)
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "tmp")
    shutil.copytree(ROOT, target, ignore=ignore)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate manifest only.")
    parser.add_argument(
        "--target",
        default="~/.codex/plugins",
        help="Target plugin directory for install. Default: ~/.codex/plugins",
    )
    parser.add_argument("--install", action="store_true", help="Copy this vault to the target plugin directory.")
    args = parser.parse_args()

    manifest = load_manifest()
    print(f"plugin: {manifest['name']} {manifest['version']}")
    print(f"skills: {manifest['skills']}")
    if args.check or not args.install:
        print("plugin manifest: OK")
        return 0
    target = copy_plugin(Path(args.target), manifest["name"])
    print(f"installed: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
