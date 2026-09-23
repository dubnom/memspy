---
name: install
description: "Use when preparing and publishing an installable Memspy Home Assistant integration release: update documentation, bump the integration version, validate the project, commit the changes, and push the current branch to its configured remote."
---

# Install

Prepare and publish the current Memspy integration.

## Workflow

1. Inspect the repository status, current branch, configured remote, recent commits, and the integration version in `custom_components/memspy/manifest.json`.
2. Read the current `README.md`, integration metadata, action descriptions, and changed implementation files. Update documentation so it describes the actual sensors, controls, refresh behavior, installation steps, and versioned feature set. Keep the documentation `Version:` line (no "Current") synchronized with the version in `custom_components/memspy/manifest.json`, updating both when the release version changes. In particular, confirm that the docs match the current entity layout:
   - `sensor.memspy` is the global summary sensor with total object count as its state.
   - The summary sensor exposes `memory`, `garbage`, `collections`, `collected`, `uncollectable`, and `gc_stats` as attributes.
   - `sensor.class_001`, `sensor.class_002`, etc. are zero-padded rank sensors ordered by memory usage; their state is memory usage in bytes.
   - Class sensor friendly names are the current Python class names, while rank IDs remain stable as classes move between ranks.
   - Per-class sensors expose `count` and `memory` as attributes.
   - `number.memspy_results_limit` controls the top-N class filter and defaults to `10`.
   - Object-memory scanning is controlled by `number.memspy_memory_scan_frequency` and `switch.memspy_memory_scanning`; no refresh services exist.
3. Check whether `custom_components/memspy/dashboard_view.yaml` has substantive content changes relative to `HEAD` with `git diff HEAD -- custom_components/memspy/dashboard_view.yaml`. If the dashboard content changed, increment `VIEW_VERSION` in `custom_components/memspy/dashboard.py` and update the matching `memspy_view_version` marker and visible dashboard version label in `dashboard_view.yaml`. Do not increment the view version for a release that only changes the marker or label themselves. This keeps the dashboard freshness sensor and the explicit Install or Upgrade action synchronized with the bundled YAML.
4. Bump the integration patch version in `custom_components/memspy/manifest.json` unless the user specifies a different release level. Preserve the config-flow schema version unless the config-entry data schema changes.
5. Run the project validation available in the repository:
   - `git diff --check`
   - `. .venv/bin/activate && python -m pytest -q` when `.venv` exists
   - Python compilation for changed integration modules
6. Review the diff and ensure captured log files, credentials, virtual environments, and cache directories are not staged.
7. Stage only the intended project changes and create a concise release commit, using `Release Memspy X.Y.Z` when the manifest version is `X.Y.Z`.
8. Push the current branch to its configured upstream or `origin`. Do not expose credentials in chat or command output.
9. Verify and report the commit hash, pushed branch, test result, and final clean/synchronized Git status.

## Safety

- Never commit tokens, passwords, Home Assistant secrets, `.venv`, caches, or captured logs that exceed repository limits.
- Do not rewrite history or force-push unless the user explicitly requests it.
- If no remote is configured, or authentication requires a secret, stop and ask the user to configure it directly in their terminal.
- If validation fails, fix only relevant release blockers before committing; report unrelated failures separately.