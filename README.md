# MemSpy

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/dubnom/memspy)](https://github.com/dubnom/memspy/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/dubnom/memspy)](https://github.com/dubnom/memspy/commits/main)
[![License](https://img.shields.io/github/license/dubnom/memspy)](LICENSE)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dubnom&repository=memspy&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=memspy)

*Written by Michael Dubno* -
Version: 1.2.22

A Home Assistant custom integration used for debugging memory issues. It reports memory allocations by integrations, Python object memory usage, and garbage-collector statistics. It exposes all of this through standard Home Assistant entities.

## Purpose and Concepts

Some integrations leak memory and cause Home Assistant to eventually crash - an issue primarily with custom integrations. It has been difficult and requires some skill to determine which integrations are leaking, and even harder to find the suspicious code.  This affects all developers and users of custom integrations.  MemSpy is designed to make finding leaks easier. It is implemented as a standard integration that allows full Home Assistant use - Lovelace panels, automations, etc.

MemSpy tools run only on demand to conserve memory and CPU.

Three ways of looking at memory:
- Tracing the allocation of memory in the code - [tracemalloc](https://docs.python.org/3/library/tracemalloc.html)
- Watching object memory use - [gc](https://docs.python.org/3/library/gc.html)
- Examining the garbage collector - [gc](https://docs.python.org/3/library/gc.html)

### Using `tracemalloc` entities:
The `select.memspy_tracemalloc_include` control selects the source tree to examine. It offers `all`, `custom`, and each configured integration domain. The `text.memspy_tracemalloc_exclude` control adds newline-separated filename patterns to exclude; blank lines and comment lines beginning with `#` are ignored. MemSpy and Spook paths are always excluded.

Enable `switch.memspy_tracemalloc_active` to start a session. Disable it to capture the snapshot, publish the results, and stop the session. The snapshot is taken before the switch turns off, so `mph` uses the elapsed time of that tracing session.

`sensor.memspy_tracemalloc` stores the number of raw allocation rows as its state. Its `snapshot` attribute is a JSON string containing up to `number.memspy_results_limit` rows. Each row contains:

- `filename` — source file containing the allocation.
- `lineno` — source line number.
- `size` — allocated memory in bytes.
- `count` — number of allocation blocks represented by the row.
- `mph` — `size` converted to observed bytes per hour for the session.

`sensor.memspy_tracemalloc_by_integration` stores the number of aggregated integrations as its state. Its `results` attribute contains up to `number.memspy_results_limit` integration objects. To improve aggregation quality, it considers up to ten times that limit in the raw snapshot before selecting the highest-memory integrations. Each object contains:

- `integration` — detected Home Assistant integration domain, or `unknown` when the path cannot be classified.
- `memory` — total `size` across that integration's included rows, in bytes.
- `mph` — total memory converted to observed bytes per hour.
- `allocations` — rows containing `filename`, `line`, `memory`, `count`, and `mph`.

Both result sets are sorted from highest memory to lowest. If a snapshot is captured before any measurable tracing time has elapsed, `mph` is `0` rather than an infinite value.

### Using `memory` entities:
Approaching memory issues by seeing how Python objects use memory is another path for finding leaks. The  `gc` library is used to expose the Python classes, the object count, and the total amount of memory consumed. A `sensor.memspy_class_###` is create from 1 to `sensor.memspy_results_limit`.  The class sensors have - the Python class name, the state is the memory used, and a `count` attribute for number of instances. `number.memspy_memory_scan_frequency` controls how often these class entities update. `switch.memspy_memory_scanning` starts and stops the scanning.

`sensor.memspy` tracks Python garbage collector data. The state is the `object count` and the attributes are:
- Attribute
- Collected
- Collections
- Uncollectable
- Garbage
- Gc stats (list)
  - collections
  - collected
  - uncollectable
- Memory
- Object count

The [gc](https://docs.python.org/3/library/gc.html) documentation provides an explanation for what the garbage collector does, and what these values mean.

## Finding Leaks

When looking for memory leaks, we're looking for any memory number that continuously grows. The workflow that works best (for me) is -
- Use `sensor.memory_use_percent` from Home Assistant's System Monitor integration and chart it over time.
- Check third-party app memory usage with the System Monitor integration. Rule this out before diving into individual integrations.
- Set `tracemalloc` entities to `custom` and start `tracemalloc`. Let it run for a few minutes and then turn it off and check the results. The list is sorted from largest memory use to smallest. Integrations may show up multiple times with different seqments of suspect code. Performing the step a number of times, or over long time spans, usually finds the leading culprits.  Examine the code in the [File Editor](https://github.com/home-assistant/addons/blob/master/configurator/DOCS.md) addon.
- If you suspect a specific integration, change the include filter to the name of your integration.
- Disable the integration for a long enough period of time to see if it really was the offender.
- If a leaky integration wasn't found, try the same process using `all` for the include.
- If you are still searching, use the `memory` sensors to examine the classes using the most memory, and look at charts of their memory and instance growth.
- Finally, check `sensor.memspy` to make sure the garbage collector is working.

Using the profiler and turning on debugging for specific integrations is also helpful. However, the profiler puts an enormous load on the system making it difficult to use while dealing with memory exhaustion. The debug logging also has its limits - it relies on the developer to embed logging statemments, and for these log entries to be something you care about. Debug writes to logs, and requires you to read through them. Debug and Logs are extremely useful to fix integrations generating errors.

For a good description of how memory works and finding leaks read - [How to Debug Memory Leaks in Python](https://oneuptime.com/blog/post/2026-01-24-debug-memory-leaks-python/view)

## Features

- `number.memspy_memory_scan_frequency` — sets the automatic object-memory scan interval in seconds. It defaults to `30`.
- `switch.memspy_memory_scanning` — enables or disables periodic object-memory scanning. It is disabled by default. Object-memory scanning is controlled by this frequency number and switch; there are no refresh or set-frequency services.
- `number.memspy_results_limit` — sets the number of the highest-memory class sensors, number of tracemalloc rows, and how number of aggregated integrations. It defaults to  `10`.
- `select.memspy_tracemalloc_include` — selects the tracemalloc include source: `all`, `custom`, or a configured integration domain. Its `code_location` attribute exposes the resolved source directory for the current selection.
- `text.memspy_tracemalloc_exclude` — newline-separated tracemalloc filename patterns to exclude. It defaults to an empty value; Memspy and Spook are always excluded in addition to any patterns entered here. Blank lines and lines beginning with `#` are ignored.
- `switch.memspy_tracemalloc_active` — starts tracemalloc when enabled and captures a final snapshot, fires the `memspy_tracemalloc_snapshot` event, and stops tracemalloc when turned off.
- `sensor.memspy_tracemalloc_duration` — reports the elapsed tracemalloc session time in seconds and keeps the final duration after tracing stops.
- `sensor.memspy_tracemalloc` — stores the number of rows in the most recent snapshot and exposes the top-N snapshot as JSON in its `snapshot` attribute. Rows include `filename`, `line`, `memory`, `count`, and `mph` fields.
- `sensor.memspy_tracemalloc_by_integration` — stores aggregated and grouped integrations in its `results` attribute. Results include `integration`, `total memory`, `total mph`, and detailed `allocations` rows. Aggregation considers up to ten times the `results limit` to save resources.
- `binary_sensor.memspy_dashboard_out_of_date` — is `on` when the dedicated dashboard is missing or older than the bundled dashboard. Press the MemSpy device's **Install or Upgrade** button to update it.
- `sensor.memspy` — global summary sensor for total live objects, memory, garbage-collector statistics, and GC stats.
- `sensor.class_001`, `sensor.class_002`, etc. — rank slots for supported Python classes, ordered by memory usage.

Only the configured highest-memory classes receive class sensors. The set is updated during the next object-memory scan.

Class sensor friendly names are the raw Python class names, without the `Memspy` prefix.

## Installation

### HACS (recommended)

1. Ensure [HACS](https://hacs.xyz) is installed.
2. Add this repository as a custom repository in HACS: **HACS → Integrations → ⋮ → Custom repositories**, enter `https://github.com/dubnom/memspy`, category **Integration** — or use the button below.
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dubnom&repository=memspy&category=integration)
3. Search for **MemSpy** in HACS and install it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration**, search for **MemSpy**, and add it — or use the button below.
   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=memspy)

### Manual

1. Copy `custom_components/memspy` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & Services → Add Integration → MemSpy**.

## Usage

Set `number.memspy_memory_scan_frequency` to the desired interval in seconds, then use `switch.memspy_memory_scanning` to enable or disable object-memory scanning.

Use `select.memspy_tracemalloc_include` and `text.memspy_tracemalloc_exclude` to configure filtering. The include select offers:

- `all` — include allocations from every source.
- `custom` — include the `/config/custom_components` tree.
- a configured integration domain — include that integration's source tree.

The select exposes a `code_location` attribute with the resolved source directory for the current selection. Enable `switch.memspy_tracemalloc_active` to start tracing. Turning it off captures the final top-N allocation snapshot and stops tracing.

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

A dedicated **MemSpy** dashboard appears in the Home Assistant sidebar at `/lovelace/memspy-dashboard` after you press the MemSpy device's **Install or Upgrade** button or call the `memspy.install_dashboard` action. Upgrading MemSpy may overwrite its managed `memspy` view, so copy or rename the view if you customize it. The following custom cards (from HACS) & integrations are used:
- [custom:custom-icons](https://github.com/thomasloven/hass-custom_icons)
- [custom:apex_charts](https://github.com/romrider/apexcharts-card)
- [custom:mushroom-select-card](https://github.com/piitaya/lovelace-mushroom/blob/main/docs/cards/select.md)
- [custom:auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
- [System monitor](https://www.home-assistant.io/integrations/systemmonitor/)

![Dashboard](screenshot.png)

## Development

```bash
pip install -r requirements_test.txt
pytest
```

## License

[MIT](LICENSE)
