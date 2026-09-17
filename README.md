# Prolog

A standalone Home Assistant custom integration that reports per-class Python
referent memory usage and garbage-collector statistics from the running Home
Assistant process.

This project has no relationship to any other project on this machine.

## Features

- `prolog.refresh` action — immediately refreshes all object sensors.
- `prolog.set_frequency` action — enables periodic refreshes in seconds;
  use `0` to disable automatic refreshes.
- `number.prolog_min_memory` and `number.prolog_max_memory` — set the inclusive
  memory thresholds for supported class sensors, in bytes.
- One `sensor.prolog_{class_name}` entity per object class — its state is the
  referent memory estimate in bytes; its `count` attribute is the live object
  count and its `gc_stats` attribute contains the per-generation
  `gc.get_stats()` values.

Classes outside the configured range become unavailable. Classes that enter
the range are added automatically on the next refresh.

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
memory range defaults to values from `1000` through the maximum supported
value; use the two number entities to change which classes are supported.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
