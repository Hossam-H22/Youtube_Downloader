"""Bump the app version in metadata.json — the single source of truth.

Usage (from anywhere):
    python3 .claude/skills/bump-version/bump.py X.Y.Z

The banner in youtube_downloader/cli.py reads project metadata at runtime (see
youtube_downloader/metadata.py), so this is the only file to edit.
"""

import json
import os
import re
import sys

# Repo root is three levels up from this file: .claude/skills/bump-version/bump.py
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
METADATA_JSON = os.path.join(REPO_ROOT, "metadata.json")

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def fail(message: str) -> "None":
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def bump_metadata_json(new_version: str) -> str:
    with open(METADATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    old = data.get("version", "<missing>")
    data["version"] = new_version
    with open(METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")
    return old


def main() -> "None":
    if len(sys.argv) != 2:
        fail("usage: python3 bump.py X.Y.Z")
    new_version = sys.argv[1].lstrip("v")
    if not SEMVER_RE.match(new_version):
        fail(f"'{sys.argv[1]}' is not a valid semver X.Y.Z")

    old = bump_metadata_json(new_version)

    print(f"metadata.json : {old} -> {new_version}")
    print("done. the app banner picks this up automatically; run /verify, then commit if the user asks.")


if __name__ == "__main__":
    main()
