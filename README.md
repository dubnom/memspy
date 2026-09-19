# Prolog

Current version: 1.1.11

A standalone Home Assistant custom integration that reports Python object memory,
class-level GC usage, global garbage-collector statistics, and tracemalloc
snapshots from the running Home Assistant process.

This project has no relationship to any other project on this machine.

## Features

- `prolog.refresh` action — immediately refreshes the GC snapshot.
- `prolog.set_frequency` action — enables periodic refreshes in seconds;
  use `0` to disable automatic refreshes.
- `prolog.start_tracemalloc` action — starts a tracemalloc session.
- `prolog.snapshot_tracemalloc` action — captures a tracemalloc snapshot,
  fires the `prolog_tracemalloc_snapshot` event, and returns the top-N entries
  using the current `number.prolog_top_n` limit.
- `prolog.stop_tracemalloc` action — stops the tracemalloc session.
- `number.prolog_top_n` — sets how many of the highest-memory classes receive
  class sensors and how many tracemalloc rows are returned. It defaults to `50`.
- `text.prolog_snapshot_filter` — sets the directory prefix used to filter
  tracemalloc rows before the top-N limit is applied. The value `*` means all
  files; the default is `/config/custom_components`.
- `sensor.prolog_tracemalloc` — stores the number of rows in the most recent
  tracemalloc snapshot as its state and exposes the full top-N snapshot as a
  JSON string in the `snapshot` attribute. The list is limited by the current
  `number.prolog_top_n` value and the active directory filter.
- `sensor.prolog` — global summary sensor. Its state is the total live object
  count. The attributes include `memory`, `garbage`, `collections`,
  `collected`, `uncollectable`, and `gc_stats`.
- `sensor.class_001`, `sensor.class_002`, etc. — rank slots for the supported
  Python classes, ordered by memory usage. The sensor state is the estimated
  referent memory in bytes for the class currently occupying that rank. The
  attributes include `count` (live object count) and `memory` (class total).

The class sensors use a friendly display name equal to the plain class name
(e.g. `dict`, `list`). Their entity IDs use a zero-padded rank so
`sensor.class_001` is always the highest-memory class.

Only the configured highest-memory classes receive class sensors. The set is
updated dynamically on the next refresh.

## Installation

Copy `custom_components/prolog` into your Home Assistant
`config/custom_components/` directory (or install via HACS as a custom
repository), restart Home Assistant, then add the integration from
**Settings → Devices & Services → Add Integration → Prolog**.

## Usage

Refresh immediately:

```yaml
action: prolog.refresh
```

Refresh automatically every 60 seconds:

```yaml
action: prolog.set_frequency
data:
  frequency: 60
```

Start a tracemalloc session and snapshot the heaviest allocations:

```yaml
action: prolog.start_tracemalloc
---
action: prolog.snapshot_tracemalloc
```

```yaml
action: prolog.stop_tracemalloc
```

The summary sensor exposes the overall GC snapshot and total object count. The
class sensors expose memory and count for each top-memory Python class. Use
`number.prolog_top_n` to adjust which classes are supported and how many
tracemalloc rows are returned; the default is `50`. Use
`text.prolog_snapshot_filter` to restrict entries to a specific Python source
path, or set it to `*` to include all files.

## Sensor examples

- `sensor.prolog` state: total object count
- `sensor.prolog` attributes: `memory`, `garbage`, `collections`, `collected`,
  `uncollectable`, `gc_stats`
- `text.prolog_snapshot_filter` state: current include path, or `*` for all files
- `sensor.class_001` state: estimated memory for the highest-memory class
- `sensor.class_001` attributes: `count`, `memory`

## Development

```bash
pip install -r requirements_test.txt
pytest
```
