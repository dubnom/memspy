# Prolog

Current version: 1.1.17

A standalone Home Assistant custom integration that reports Python object memory, class-level GC usage, global garbage-collector statistics, and tracemalloc snapshots from the running Home Assistant process.

## Features

- `number.prolog_memory_scan_frequency` — sets the automatic object-memory scan interval in seconds. It defaults to `30`.
- `switch.prolog_memory_scanning` — enables or disables periodic object-memory scanning. It is disabled by default. Object-memory scanning is controlled by this frequency number and switch; there are no refresh or set-frequency services.
- `number.prolog_top_n` — sets how many of the highest-memory classes receive class sensors and how many tracemalloc rows are returned. Its current default is `10`.
- `text.prolog_tracemalloc_include` — controls the tracemalloc include path. Set it to `*` to include all files.
- `text.prolog_tracemalloc_exclude` — newline-separated tracemalloc filename patterns to exclude. It defaults to an empty value; Prolog and Spook are always excluded in addition to any patterns entered here. Blank lines and lines beginning with `#` are ignored.
- `switch.prolog_tracemalloc_active` — starts tracemalloc when enabled and captures a final snapshot, fires the `prolog_tracemalloc_snapshot` event, and stops tracemalloc when turned off.
- `sensor.prolog_tracemalloc` — stores the number of rows in the most recent snapshot and exposes the top-N snapshot as JSON in its `snapshot` attribute.
- `sensor.prolog` — global summary sensor for total live objects, memory, garbage-collector statistics, and GC stats.
- `sensor.class_001`, `sensor.class_002`, etc. — rank slots for supported Python classes, ordered by memory usage.

Only the configured highest-memory classes receive class sensors. The set is updated during the next object-memory scan.

Class sensor friendly names are the raw Python class names, without the `Prolog` prefix.

## Installation

Copy `custom_components/prolog` into your Home Assistant `config/custom_components/` directory (or install via HACS as a custom repository), restart Home Assistant, then add the integration from **Settings → Devices & Services → Add Integration → Prolog**.

## Usage

Set `number.prolog_memory_scan_frequency` to the desired interval in seconds, then use `switch.prolog_memory_scanning` to enable or disable object-memory scanning.

Use the tracemalloc entities named `text.prolog_tracemalloc_include` and `text.prolog_tracemalloc_exclude` to configure filtering. Enable `switch.prolog_tracemalloc_active` to start tracing. Turning it off captures the final top-N allocation snapshot and stops tracing.

The summary sensor exposes the overall GC snapshot and total object count. The class sensors expose memory and count for each top-memory Python class. Use `number.prolog_top_n` to adjust the supported classes and returned tracemalloc rows; its default is `10`.

## Sensor examples

- `sensor.prolog` state: total object count
- `sensor.prolog` attributes: `memory`, `garbage`, `collections`, `collected`, `uncollectable`, `gc_stats`
- `switch.prolog_memory_scanning` state: `on` when object-memory scanning is active
- `number.prolog_memory_scan_frequency` state: scan interval in seconds
- `switch.prolog_tracemalloc_active` state: `on` when tracemalloc is active
- `text.prolog_tracemalloc_include` state: current include path
- `text.prolog_tracemalloc_exclude` state: current exclusion patterns
- `sensor.class_001` state: estimated memory for the highest-memory class

## Development

```bash
pip install -r requirements_test.txt
pytest
```
