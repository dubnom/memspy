# MemSpy

Current version: 1.2.3

A standalone Home Assistant custom integration used for debugging memory issues. It reports memory allocations by integrations, Python object memory usage, and garbage-collector statistics. It exposes all of this through standard Home Assistant entities.

## Purpose and Concepts

Some integrations leak memory and cause Home Assistant to eventually crash. This is primarily an issue with custom integrations. It has been a difficult and involved process to determine which integrations are leaking and even harder to find the suspicious code.  This is true for developers and users of custom integrations.  MemSpy is designed to make this process easier. It is implemented as a standard integration that allows full Home Assistant use - Lovelace panels, automations, etc.

MemSpy tools run only on demand to conserve memory and CPU.

To find the integration that is allocating memory, use the `tracemalloc` entities. The `select.memspy_tracemalloc_include` chooses which integrations should be examined. It has special options for `all` and `custom`. Switching `switch.memspy_tracemalloc_active` on starts the trace. When turned off, it populates the `snapshot` attribute of `sensor.memspy_tracemalloc` with a list of `{filename, line number, memory, and count}` entries. The list is filtered to only include files that match `select.memspy_tracemalloc_include`. It is also sorted by memory, high to low. The results are limited to `number.memspy_results_limit`. Tracemalloc is the most useful for pinpointing memory issues.

Sometimes it is more useful to approach memory issues by looking at how Python objects use memory. These entities use the `gc` library to track a list of `{class, memory, objects}` on a recurring basis. They are the `sensor.memspy` summary sensor and the `sensor.memspy_class_###` entities. The period between updates is controlled by `number.memspy_memory_scan_frequency`, which defaults to 30 seconds. Switching `switch.memspy_memory_scanning` on starts the scanning. `sensor.class_###` entities are updated periodically with the results. Turning off `switch.memspy_memory_scanning` stops the scanning.

While scanning, the Python garbage collector has some useful information. The `gc_stats`, `garbage`, `collections`, `collected`, and `uncollectable` attributes of `sensor.memspy` are updated along with the class entities.

## Finding Leaks

We're looking for memory leaks - any memory number that continuously grows. The workflow that works best (for me) is -
- Use `sensor.memory_use_percent` from Home Assistant's System Monitor integration and chart it over time.
- Check third-party app memory usage with the System Monitor integration. Rule this out before diving into individual integrations.
- Set `tracemalloc` entities to `custom` and start `tracemalloc`. Let it run for a few minutes and then turn it off and check the results. The list is sorted from largest memory use to smallest. Integrations may show up multiple times with different seqments of suspect code. Performing the step a number of times, or over long time spans, usually finds the leading culprits.  Examine the code in the [File Editor](https://github.com/home-assistant/addons/blob/master/configurator/DOCS.md) addon.
- If you suspect a specific integration, change the include filter to the name of your integration.
- Disable the integration for a long enough period of time to see if it really was the offender.
- If a leaky integration wasn't found, try the same process using `all` for the include.
- If you are still searching, use the `memory` sensors to examine the classes using the most memory, and look at charts of their memory and instance growth.
- Finally, check `sensor.memspy` to make sure the garbage collector is working.

Using the profiler and turning on debugging for specific integrations is also helpful. However, the profiler puts an enormous load on the system making it difficult to use while dealing with memory exhaustion. The debug logging also has its limits - it relies on the developer to embed logging statemments, and for these log entries to be something you care about. Debug logging also requires you to read through logs. It is extremely useful for integrations that are generating errors.

A good description of how memory works and how to find leaks read - [How to Debug Memory Leaks in Python](https://oneuptime.com/blog/post/2026-01-24-debug-memory-leaks-python/view)

## Features

- `number.memspy_memory_scan_frequency` — sets the automatic object-memory scan interval in seconds. It defaults to `30`.
- `switch.memspy_memory_scanning` — enables or disables periodic object-memory scanning. It is disabled by default. Object-memory scanning is controlled by this frequency number and switch; there are no refresh or set-frequency services.
- `number.memspy_results_limit` — sets how many of the highest-memory classes receive class sensors and how many tracemalloc rows are returned. Its current default is `10`.
- `select.memspy_tracemalloc_include` — selects the tracemalloc include source: `all`, `custom`, or a configured integration domain. Its attributes list configured entries and code locations.
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

Use `select.memspy_tracemalloc_include` and `text.memspy_tracemalloc_exclude` to configure filtering. The include select offers:

- `all` — include allocations from every source.
- `custom` — include the `/config/custom_components` tree.
- a configured integration domain — include that integration's source tree.

The select attributes expose `config_entries`, containing each configured entry's domain, title, and `code_location`, and `code_locations`, mapping `all`, `custom`, and each integration domain to its resolved source directory. Enable `switch.memspy_tracemalloc_active` to start tracing. Turning it off captures the final top-N allocation snapshot and stops tracing.

`text.memspy_tracemalloc_exclude` accepts newline-separated filename patterns. Blank lines and lines beginning with `#` are ignored; Memspy and Spook paths are always excluded in addition to the configured patterns.

The summary sensor exposes the overall GC snapshot and total object count. The class sensors expose memory and count for each top-memory Python class. Use `number.memspy_results_limit` to adjust the supported classes and returned tracemalloc rows; its default is `10`.

## Sensor examples

- `sensor.memspy` state: total object count
- `sensor.memspy` attributes: `memory`, `garbage`, `collections`, `collected`, `uncollectable`, `gc_stats`
- `switch.memspy_memory_scanning` state: `on` when object-memory scanning is active
- `number.memspy_memory_scan_frequency` state: scan interval in seconds
- `switch.memspy_tracemalloc_active` state: `on` when tracemalloc is active
- `sensor.memspy_tracemalloc_duration` state: elapsed tracemalloc time in seconds
- `select.memspy_tracemalloc_include` state: `all`, `custom`, or an integration domain
- `text.memspy_tracemalloc_exclude` state: current exclusion patterns
- `sensor.class_001` state: estimated memory for the highest-memory class

## User Interface (Lovelace)

A view is auto installed by the integration which should help get you started. It needs the following custom cards (from HACS) to work correctly:
- [custom:custom-icons](https://github.com/thomasloven/hass-custom_icons)
- [custom:apex_charts](https://github.com/romrider/apexcharts-card)
- [custom:mushroom-select-card](https://github.com/piitaya/lovelace-mushroom/blob/main/docs/cards/select.md)
- [custom:auto-entities](https://github.com/thomasloven/lovelace-auto-entities)

## Development

```bash
pip install -r requirements_test.txt
pytest
```
