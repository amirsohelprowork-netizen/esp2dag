# Usage guide

## Install

```bash
git clone https://github.com/amirsohelprowork-netizen/ESP_schedules_to_dagfactory.git
cd ESP_schedules_to_dagfactory
poetry install
poetry run esp2dag --help
```

Without Poetry:

```bash
pip install -e .
python -m esp2dag --help
```

## Inputs

| Path | Description |
|------|-------------|
| `data/samples/demo_app.esp` | Small demo application |
| `data/samples/demo_events.esp` | Matching events |
| `data/anonymized/schedule.esp` | Full anonymized ESP schedule |
| `data/anonymized/events.esp` | Full anonymized ESP events |

Use your own `.esp` / schedule extract + events file the same way (paths as arguments).

## Commands

### YAML only (most common)

```bash
python -m esp2dag yaml <schedule> [events] -o out/yaml_full
```

Example:

```bash
python -m esp2dag yaml data/anonymized/schedule.esp data/anonymized/events.esp -o out/yaml_full
```

### Full compile (YAML + graphs + reports)

```bash
python -m esp2dag compile data/anonymized/schedule.esp data/anonymized/events.esp -o out/full
```

### Graphs only

```bash
python -m esp2dag graph data/samples/demo_app.esp -o out/graphs --format mermaid,json,graphviz
```

### Reports only

```bash
python -m esp2dag report data/anonymized/schedule.esp data/anonymized/events.esp -o out/reports
```

### Limit apps (smoke test)

```bash
python -m esp2dag yaml data/anonymized/schedule.esp data/anonymized/events.esp -o out/smoke -n 5
```

### Extract applications from a multi-app schedule

```bash
python -m esp2dag extract data/anonymized/schedule.esp -o out/extract
```

## Output layout

```text
out/<run>/
  yaml/*.yaml          # DAG Factory documents (one file per application)
  graphs/*.mmd         # Mermaid (if compile/graph)
  graphs/*.json
  reports/             # statistics, validation, migration, dependencies
```

## Airflow notes

1. Load YAML with [DAG Factory](https://github.com/astronomer/dag-factory) (or your org’s loader).
2. Create Airflow connections matching `conn_id` / `winrm_conn_id` / `ssh_conn_id` values.
3. Create pools named `nw_XXXX` with **slots = 1** for ESP `NOTWITH` exclusion groups.
4. Custom operators (`AS400Operator`, `MainframeSubmitJobOperator`, …) must exist in your Airflow image.

## Tests

```bash
poetry run pytest -m "not slow"
```

## License / commercial use

Public evaluation is welcome. **Commercial / production use requires permission.**  
See [LICENSE](../LICENSE) and contact **amirsohelprowrok@gmail.com**.
