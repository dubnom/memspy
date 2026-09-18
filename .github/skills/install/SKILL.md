---
name: install
description: "Use when preparing and publishing an installable Prolog Home Assistant integration release: update documentation, bump the integration version, validate the project, commit the changes, and push the current branch to its configured remote."
---

# Install

Prepare and publish the current Prolog integration.

## Workflow

1. Inspect the repository status, current branch, configured remote, recent commits, and the integration version in `custom_components/prolog/manifest.json`.
2. Read the current `README.md`, integration metadata, action descriptions, and changed implementation files. Update documentation so it describes the actual sensors, controls, refresh behavior, installation steps, and versioned feature set. Keep the documentation version number synchronized with the version in `custom_components/prolog/manifest.json`, updating both when the release version changes. In particular, confirm that the docs match the current entity layout:
   - `sensor.prolog` is the global summary sensor with total object count as its state.
   - The summary sensor exposes `memory`, `garbage`, `collections`, `collected`, `uncollectable`, and `gc_stats` as attributes.
   - `sensor.class_<class_name>` sensors are per-class memory sensors whose state is memory usage in bytes.
   - Per-class sensors expose `count`, `memory`, and `gc_stats` as attributes.
   - `number.prolog_top_n` controls the top-N class filter and defaults to `50`.
   - The `prolog.refresh` and `prolog.set_frequency` actions still exist and are documented correctly.
3. Bump the integration patch version in `custom_components/prolog/manifest.json` unless the user specifies a different release level. Preserve the config-flow schema version unless the config-entry data schema changes.
4. Run the project validation available in the repository:
   - `git diff --check`
   - `. .venv/bin/activate && python -m pytest -q` when `.venv` exists
   - Python compilation for changed integration modules
5. Review the diff and ensure captured log files, credentials, virtual environments, and cache directories are not staged.
6. Stage only the intended project changes and create a concise release commit, using `Release Prolog X.Y.Z` when the manifest version is `X.Y.Z`.
7. Push the current branch to its configured upstream or `origin`. Do not expose credentials in chat or command output.
8. Verify and report the commit hash, pushed branch, test result, and final clean/synchronized Git status.

## Safety

- Never commit tokens, passwords, Home Assistant secrets, `.venv`, caches, or captured logs that exceed repository limits.
- Do not rewrite history or force-push unless the user explicitly requests it.
- If no remote is configured, or authentication requires a secret, stop and ask the user to configure it directly in their terminal.
- If validation fails, fix only relevant release blockers before committing; report unrelated failures separately.