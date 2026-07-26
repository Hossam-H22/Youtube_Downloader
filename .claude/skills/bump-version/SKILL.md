---
name: bump-version
description: Bump the app version in metadata.json, the single source of truth. The cli.py banner reads it at runtime, so there is only one place to edit. Use when releasing a new version of the YouTube Downloader.
---

# bump-version

The version lives in **one** place: the `"version"` field of `metadata.json`.
The menu banner in `youtube_downloader/cli.py` reads it at runtime via
`youtube_downloader/metadata.py` (`get_metadata()`), so it always matches — there is
nothing else to keep in sync.

## Usage

From anywhere in the repo:

```bash
python3 .claude/skills/bump-version/bump.py X.Y.Z
```

Example:

```bash
python3 .claude/skills/bump-version/bump.py 1.2.0
```

The script:
- validates the argument is semver-shaped (`X.Y.Z`, a leading `v` is allowed),
- sets `version` in `metadata.json`,
- prints the old → new value.

## After bumping

1. Run the `/verify` skill — the menu smoke test should now show the new banner
   (the banner reads `metadata.json`, so no code change is needed).
2. Commit only if the user asks. Suggested message: `chore: bump version to X.Y.Z`.
   If they want a tag: `git tag vX.Y.Z`.
