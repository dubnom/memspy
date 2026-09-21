# Memspy

Current version: 1.2.0

A standalone Home Assistant custom integration that reports Python object memory, class-level GC usage, global garbage-collector statistics, and tracemalloc snapshots from the running Home Assistant process.

## Features

- `number.memspy_memory_scan_frequency` — sets the automatic object-memory scan interval in seconds. It defaults to `30`.
- `switch.memspy_memory_scanning` — enables or disables periodic object-memory scanning. It is disabled by default. Object-memory scanning is controlled by this frequency number and switch; there are no refresh or set-frequency services.
- `number.memspy_top_n` — sets how many of the highest-memory classes receive class sensors and how many tracemalloc rows are returned. Its current default is `10`.
- `text.memspy_tracemalloc_include` — controls the tracemalloc include path. Set it to `*` to include all files.
- `text.memspy_tracemalloc_exclude` — newline-separated tracemalloc filename patterns to exclude. It defaults to an empty value; Memspy and Spook are always excluded in addition to any patterns entered here. Blank lines and lines beginning with `#` are ignored.
- `switch.memspy_tracemalloc_active` — starts tracemalloc when enabled and captures a final snapshot, fires the `memspy_tracemalloc_snapshot` event, and stops tracemalloc when turned off.
- `sensor.memspy_tracemalloc_duration` — reports the elapsed tracemalloc session time in seconds and keeps the final duration after tracing stops.
- `sensor.memspy_tracemalloc` — stores the number of rows in the most recent snapshot and exposes the top-N snapshot as JSON in its `snapshot` attribute.
- `sensor.memspy` — global summary sensor for total live objects, memory, garbage-collector statistics, and GC stats.
- `sensor.class_001`, `sensor.class_002`, etc. — rank slots for supported Python classes, ordered by memory usage.

Only the configured highest-memory classes receive class sensors. The set is updated during the next object-memory scan.

Class sensor friendly names are the raw Python class names, without the `Memspy` prefix.

## Installation

Copy `custom_components/memspy` into your Home Assistant `config/custom_components/` directory (or install via HACS as a custom repository), restart Home Assistant, then add the integration from **Settings → Devices & Services → Add Integration → Memspy**.

## Usage

Set `number.memspy_memory_scan_frequency` to the desired interval in seconds, then use `switch.memspy_memory_scanning` to enable or disable object-memory scanning.

Use the tracemalloc entities named `text.memspy_tracemalloc_include` and `text.memspy_tracemalloc_exclude` to configure filtering. Enable `switch.memspy_tracemalloc_active` to start tracing. Turning it off captures the final top-N allocation snapshot and stops tracing.

The summary sensor exposes the overall GC snapshot and total object count. The class sensors expose memory and count for each top-memory Python class. Use `number.memspy_top_n` to adjust the supported classes and returned tracemalloc rows; its default is `10`.

## Sensor examples

- `sensor.memspy` state: total object count
- `sensor.memspy` attributes: `memory`, `garbage`, `collections`, `collected`, `uncollectable`, `gc_stats`
- `switch.memspy_memory_scanning` state: `on` when object-memory scanning is active
- `number.memspy_memory_scan_frequency` state: scan interval in seconds
- `switch.memspy_tracemalloc_active` state: `on` when tracemalloc is active
- `sensor.memspy_tracemalloc_duration` state: elapsed tracemalloc time in seconds
- `text.memspy_tracemalloc_include` state: current include path
- `text.memspy_tracemalloc_exclude` state: current exclusion patterns
- `sensor.class_001` state: estimated memory for the highest-memory class

## Development

```bash
pip install -r requirements_test.txt
pytest
```
