# ESP to Airflow DAG Factory Builder (`esp2dag`)

Compiler that converts **ESP Workload Automation** schedule + event files into **DAG Factory YAML** for Apache Airflow.

```
Schedule + Events → Extract → Lex → Parse → Semantic → IR → Event Merge → DAG Factory YAML
```

## Inputs (redacted)

| File | Role |
|------|------|
| [`data/anonymized/schedule.esp`](data/anonymized/schedule.esp) | Full anonymized schedule |
| [`data/anonymized/events.esp`](data/anonymized/events.esp) | Full anonymized events |
| [`data/samples/`](data/samples/) | Tiny fixtures for quick demos / tests |

## Setup

```bash
poetry install
poetry run pytest
poetry run esp2dag --help
```

## Convert to DAG Factory YAML

Full estate:

```bash
python -m esp2dag yaml data/anonymized/schedule.esp data/anonymized/events.esp -o out/yaml_full
```

YAML + graphs + reports:

```bash
python -m esp2dag compile data/anonymized/schedule.esp data/anonymized/events.esp -o out/full
```

Small sample:

```bash
python -m esp2dag yaml data/samples/demo_app.esp data/samples/demo_events.esp -o out/demo
```

Output: `out/<run>/yaml/*.yaml`

## Design docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/PIPELINE.md](docs/PIPELINE.md)
