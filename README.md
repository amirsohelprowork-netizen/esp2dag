# ESP Schedules → DAG Factory YAML (`esp2dag`)

**CA ESP / Broadcom ESP Workload Automation → Apache Airflow DAG Factory YAML converter**

Migrate legacy **ESP** (CA Workload Automation ESP Edition) applications and events into **DAG Factory**-compatible YAML for **Apache Airflow 2/3**.

> Looking for ESP → Airflow, Cybermation → DAG Factory, mainframe scheduler modernization, AS400 / WinRM / SAP job mapping, or a similar converter for **Control-M, Automic, Tidal, Dollar Universe, Stonebranch, Automic**, etc.? See [Contact](#contact--commercial-licensing) below.

---

## Why this exists

Enterprise batch estates on **ESP** often contain thousands of applications (`APPL`), agent jobs (`NT_JOB`, `AS400_JOB`, `AIX_JOB`, `UNIX_JOB`, `LINUX_JOB`, `SAP_JOB`), `EXTERNAL` waits, `LINK` markers, `NOTWITH` exclusions, and event-driven `SCHEDULE` / `DSTRIG` triggers.

`esp2dag` is a **multi-stage compiler** (not a regex rewrite):

```text
ESP schedule + events
  → extract → lex → parse → semantic analysis
  → workflow IR → event merge → NOTWITH pools
  → DAG Factory YAML (+ optional graphs & migration reports)
```

## Features

- **DAG Factory YAML** ready for Airflow (operators, dependencies, schedules)
- Job-type mapping: WinRM, SSH, AS400, SAP RFC, mainframe submit, sensors, EmptyOperator
- Dependencies from ESP **`RELEASE ADD`** and **`AFTER ADD`**
- **EXTERNAL** → `ExternalTaskSensor` · **LINK** → `EmptyOperator`
- **NOTWITH** → shared Airflow **exclusion pools** (cross-DAG safe)
- Event merge for cron-like schedules from ESP `SCHEDULE` times
- Graphs (Mermaid / JSON / DOT) and migration reports
- Sample **anonymized** schedule + events included for demos

## Quick start

### Requirements

- Python **3.12+**
- [Poetry](https://python-poetry.org/) (recommended) or `pip`

### Install

```bash
git clone https://github.com/amirsohelprowork-netizen/ESP_schedules_to_dagfactory.git
cd ESP_schedules_to_dagfactory
poetry install
# or: pip install -e .
```

### Convert (smallest demo)

```bash
python -m esp2dag yaml data/samples/demo_app.esp data/samples/demo_events.esp -o out/demo
```

YAML lands in `out/demo/yaml/`.

### Convert the full anonymized estate

```bash
python -m esp2dag yaml data/anonymized/schedule.esp data/anonymized/events.esp -o out/yaml_full
```

### Full compile (YAML + graphs + reports)

```bash
python -m esp2dag compile data/anonymized/schedule.esp data/anonymized/events.esp -o out/full
```

See **[docs/USAGE.md](docs/USAGE.md)** for all CLI commands and output layout.

## Example output shape

```yaml
my_app:
  description: MY_APP application
  schedule: 0 11,19 * * *
  catchup: false
  default_args:
    owner: batchuser
    start_date: "2024-01-01"
  tasks:
    wait_upstream:
      operator: airflow.sensors.external_task.ExternalTaskSensor
      external_dag_id: other_app
      external_task_id: LIE.UPSTREAM
      mode: reschedule
    run_windows:
      operator: airflow.providers.microsoft.winrm.operators.winrm.WinRMOperator
      ssh_conn_id: AGENT01
      command: D:\SCRIPTS\JOB.bat
      pool: nw_0001
      dependencies:
        - wait_upstream
```

## Repository layout

```text
src/esp2dag/          # Compiler package (CLI + pipeline)
data/anonymized/      # Redacted full schedule + events (demo input)
data/samples/         # Tiny fixtures
scripts/              # Maintainer helpers (keyword-safe re-anonymize)
docs/                 # Architecture + usage
tests/                # Unit + golden tests
LICENSE               # Source-available, non-commercial without permission
```

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/USAGE.md](docs/USAGE.md) | Install, CLI, inputs, outputs |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Compiler stages |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Stage contracts |
| [docs/WORKFLOW_MODEL.md](docs/WORKFLOW_MODEL.md) | Intermediate representation |
| [LICENSE](LICENSE) | License & commercial terms |

## Keywords (discoverability)

`ESP`, `CA ESP`, `Broadcom ESP`, `Workload Automation`, `Cybermation`, `Apache Airflow`, `Airflow 3`, `DAG Factory`, `dag-factory`, `scheduler migration`, `mainframe batch`, `AS400`, `IBM i`, `WinRM`, `SSHOperator`, `SAP job`, `ExternalTaskSensor`, `NOTWITH`, `ESP to Airflow`, `legacy scheduler modernization`

## Contact / commercial licensing

This project is **public for learning and evaluation**.  
**Commercial use is not free** — contact before production or paid use.

| Need | Contact |
|------|---------|
| Commercial license for this ESP → DAG Factory converter | Email below |
| Custom converter for **another scheduler** (Control-M, Automic, Tidal, Dollar Universe, Autosys, Stonebranch, …) → Airflow / Dagster / Prefect / etc. | Email below |
| Consulting on ESP / Airflow migration strategy | Email below |

**Amir Sohel**  
Email: [amirsohelprowork@gmail.com](mailto:amirsohelprowork@gmail.com)  
GitHub: [amirsohelprowork-netizen](https://github.com/amirsohelprowork-netizen)

Please include: your organization, source scheduler, target platform, and rough estate size (# apps / jobs).

## License

See [LICENSE](LICENSE).

**Source available · Non-commercial without permission · Contact for commercial use.**
