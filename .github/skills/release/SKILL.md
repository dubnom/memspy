---
name: release
description: "Use when cutting a full Memspy Home Assistant integration release: everything the install skill does, plus tagging the release and publishing a GitHub Release so the HACS/GitHub release badge and HACS update feed pick it up."
---

# Release

Perform a complete Memspy release: prepare the install (docs, version bump, validation, commit, push), then tag and publish a GitHub Release.

## Workflow

1. Run the full `install` skill workflow first (see `.github/skills/install/SKILL.md`):
   - Inspect repo status, branch, remote, recent commits, and the version in `custom_components/memspy/manifest.json`.
   - Update `README.md` and other docs to match the current entity layout, controls, and features. Keep the `Version:` line (no "Current") synchronized with the manifest version.
   - Bump the integration patch version in `manifest.json` unless the user specifies a different release level.
   - Validate: `git diff --check`, `. .venv/bin/activate && python -m pytest -q` when `.venv` exists, and Python compilation for changed integration modules.
   - Stage only intended changes (never captured logs, credentials, `.venv`, caches, or the user's personal `custom_components/dashboard.yaml`).
   - Commit as `Release Memspy X.Y.Z` and push the current branch to its configured upstream/`origin`.
2. Tag the release commit with an annotated tag `vX.Y.Z` matching the manifest version, and push the tag: `git tag -a vX.Y.Z -m "Release Memspy X.Y.Z" && git push origin vX.Y.Z`. Skip this step (and say why) if a tag `vX.Y.Z` already exists.
3. Publish a GitHub Release for the tag:
   - If the `gh` CLI is installed and authenticated (`gh auth status`), run `gh release create vX.Y.Z --title "Memspy X.Y.Z" --generate-notes`.
   - If `gh` is unavailable or unauthenticated, do not attempt to install or authenticate it yourself. Report that the tag was pushed and that the user (or a `gh`/GitHub Actions setup) needs to publish the GitHub Release, e.g. via `gh release create` or the repository's **Releases → Draft a new release** page.
4. Verify and report: commit hash, tag name, whether the GitHub Release was published (or why not), test result, and final clean/synchronized Git status.

## Safety

- Never commit tokens, passwords, Home Assistant secrets, `.venv`, caches, or captured logs that exceed repository limits.
- Do not rewrite history or force-push unless the user explicitly requests it.
- Do not force-push tags or delete/recreate an existing tag without explicit user confirmation.
- If no remote is configured, or authentication requires a secret, stop and ask the user to configure it directly in their terminal.
- If validation fails, fix only relevant release blockers before committing; report unrelated failures separately.
