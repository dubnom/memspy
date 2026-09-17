# Prolog

A standalone Home Assistant custom integration that reports per-class Python
referent memory usage and garbage-collector statistics from the running Home
Assistant process.

This project has no relationship to any other project on this machine.

## Features

- `prolog.refresh` action — immediately refreshes all object sensors.
- `prolog.set_frequency` action — enables periodic refreshes in seconds;
  use `0` to disable automatic refreshes.
- `number.prolog_top_n` — sets how many of the highest-memory classes receive
  sensors. It defaults to `50`.
- One `sensor.prolog_{class_name}` entity per object class — its state is the
  referent memory estimate in bytes; its `count` attribute is the live object
  count and its `gc_stats` attribute contains the per-generation
  `gc.get_stats()` values.

Only the configured highest-memory classes receive sensors. The set is updated
dynamically on the next refresh.

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

The object sensors expose one entity per supported Python class. Their state is
the memory estimate and their `count` attribute is the live object count. The
top-memory-user limit defaults to `50`; use `number.prolog_top_n` to change
which classes are supported.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
