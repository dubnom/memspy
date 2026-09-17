# Prolog

A standalone Home Assistant custom integration that reports live Python object
counts and referent memory estimates from the running Home Assistant process.

This project has no relationship to any other project on this machine.

## Features

- `prolog.refresh` service — immediately refreshes both sensors.
- `prolog.set_frequency` service — enables periodic refreshes in seconds;
  use `0` to disable automatic refreshes.
- One `sensor.prolog_{class_name}` entity per object class — its state is the
  live object count and its `memory` attribute is the referent memory estimate.

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

Read the two sensors for the current totals and their per-type attributes.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
