# Prolog

A standalone Home Assistant custom integration that reports Python object memory,
class-level GC usage, and global garbage-collector statistics from the running
Home Assistant process.

This project has no relationship to any other project on this machine.

## Features

- `prolog.refresh` action — immediately refreshes the snapshot.
- `prolog.set_frequency` action — enables periodic refreshes in seconds;
  use `0` to disable automatic refreshes.
- `number.prolog_top_n` — sets how many of the highest-memory classes receive
  class sensors. It defaults to `50`.
- `sensor.prolog` — global summary sensor. Its state is the total live object
  count, and it exposes attributes for total memory, garbage counts,
  collection totals, and `gc_stats`.
- `sensor.class_<class_name>` — one entity per supported object class. The
  state is the estimated referent memory in bytes, and the attributes include
  the live object count, the class memory total, and `gc_stats`.

Only the configured highest-memory classes receive class sensors. The set is
updated dynamically on the next refresh.

## Installation

Copy `custom_components/prolog` into your Home Assistant
`config/custom_components/` directory (or install via HACS as a custom
repository), restart Home Assistant, then add the integration from
**Settings → Devices & Services → Add Integration → Prolog**.

## Usage

```yaml
action: prolog.refresh
```

To refresh automatically every 60 seconds:

```yaml
action: prolog.set_frequency
data:
  frequency: 60
```

The summary sensor exposes the overall GC snapshot and total object count. The
class sensors expose memory and count for each top-memory Python class. Use
`number.prolog_top_n` to adjust which classes are supported; the default is `50`.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
