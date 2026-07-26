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

2. **Tag the release and push it — but get the user's approval first.**
   Tagging and pushing are outward-facing, hard-to-reverse actions, so **always
   ask the user to approve before running them**. Show the exact commands you are
   about to run and wait for a clear yes. If the user declines, stop here and
   leave the bump uncommitted for them to handle.

   Once approved, run these steps (a tag must point at a commit, so the bump is
   committed first):

   ```bash
   git add metadata.json
   git commit -m "chore: bump version to X.Y.Z"
   git tag vX.Y.Z
   git push               # push the commit on the current branch
   git push origin vX.Y.Z # push the new tag
   ```

   Substitute the real `X.Y.Z`. If the current branch has no upstream, use
   `git push -u origin <branch>` for the first push. Report the outcome of each
   command (don't claim success if a push failed).
