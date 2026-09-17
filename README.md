# Prolog

A standalone Home Assistant custom integration that reports live Python object
counts and referent memory estimates from the running Home Assistant process.

This project has no relationship to any other project on this machine.

## Features

- `prolog.refresh` service — immediately refreshes all object sensors.
- `prolog.set_frequency` service — enables periodic refreshes in seconds;
  use `0` to disable automatic refreshes.
- `number.prolog_min_count` and `number.prolog_max_count` — set the inclusive
  `min_count` and `max_count` thresholds for supported class sensors.
- One `sensor.prolog_{class_name}` entity per object class — its state is the
  live object count and its `memory` attribute is the referent memory estimate.

Classes outside the configured range become unavailable. Classes that enter
the range are added automatically on the next refresh.

## Installation

Copy `custom_components/prolog` into your Home Assistant
`config/custom_components/` directory (or install via HACS as a custom
repository), restart Home Assistant, then add the integration from
**Settings → Devices & Services → Add Integration → Prolog**.

## Usage

```yaml
service: prolog.refresh
```

To refresh automatically every 60 seconds:

```yaml
service: prolog.set_frequency
data:
  frequency: 60
```

The object sensors expose one entity per supported Python class. Their state is
the live count and their `memory` attribute is the memory estimate. The count
range defaults to counts from `1000` through the maximum supported value; use
the two number entities to change which classes are supported.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
