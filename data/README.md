# Sample Data

This directory contains curated, synthetic ESP workload automation datasets structured across 5 complexity levels for testing, demonstration, and evaluation:

| Level | Schedule File | Events File | Description |
|:---|:---|:---|:---|
| **Level 1: Basic Batch** | `samples/01_basic_batch.esp` | `samples/01_basic_events.esp` | Basic mainframe batch (sequential & fan-out/fan-in pipelines, CCCHK) |
| **Level 2: Multi-Platform** | `samples/02_multi_platform.esp` | `samples/02_multi_platform_events.esp` | Heterogeneous platforms (WinRM, SSH, AS400 / IBM i, AIX) |
| **Level 3: Dependencies & Triggers** | `samples/03_dependencies_and_triggers.esp` | `samples/03_trigger_events.esp` | Dataset triggers (`DSTRIG`), `EXTERNAL` task sensors, `LINK` markers, `NOTWITH` exclusion pools |
| **Level 4: Advanced Scheduling** | `samples/04_advanced_scheduling.esp` | `samples/04_scheduling_events.esp` | Calendar logic, `GENTIME`, `IFHOLIDAYPLUS`, bi-weekly, cyclic executions |
| **Level 5: Enterprise Production** | `samples/05_enterprise_production.esp` | `samples/05_enterprise_events.esp` | Comprehensive 11-application enterprise estate covering all features |

## Running Sample Conversions

### 1. Compile Level 1 (Basic Batch) to Airflow 3 Python DAGs
```bash
python -m esp2dag dag data/samples/01_basic_batch.esp data/samples/01_basic_events.esp -o out/basic
```

### 2. Full Compile of Level 5 (Enterprise Production Estate)
```bash
python -m esp2dag compile data/samples/05_enterprise_production.esp data/samples/05_enterprise_events.esp -o out/enterprise
```

More details and CLI options can be found in [docs/USAGE.md](../docs/USAGE.md).

## License

All sample files in this directory are synthetic and anonymized for evaluation. Commercial and production use requires permission (see [LICENSE](../LICENSE)).

