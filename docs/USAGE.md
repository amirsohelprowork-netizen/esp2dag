# Usage Guide

## Installation

### Option A: Standard Pip (Editable Mode)

```bash
git clone https://github.com/amirsohelprowork-netizen/ESP_schedules_to_dagfactory.git
cd ESP_schedules_to_dagfactory
pip install -e .
python -m esp2dag --help
```

### Option B: With Poetry

```bash
poetry install
poetry run esp2dag --help
```

---

## Included Sample Estates

The repository includes 5 curated, synthetic ESP datasets in `data/samples/` representing different batch patterns:

| Level | Schedule File | Events File | Highlights |
|:---|:---|:---|:---|
| **Level 1: Basic Batch** | `data/samples/01_basic_batch.esp` | `data/samples/01_basic_events.esp` | Mainframe JCL, `RUN DAILY`, sequential chains, parallel fan-out/fan-in, `CCCHK` |
| **Level 2: Multi-Platform** | `data/samples/02_multi_platform.esp` | `data/samples/02_multi_platform_events.esp` | `NT_JOB` (WinRM), `LINUX_JOB` / `UNIX_JOB` (SSH), `AS400_JOB`, `AIX_JOB` |
| **Level 3: Dependencies & Triggers** | `data/samples/03_dependencies_and_triggers.esp` | `data/samples/03_trigger_events.esp` | `DSTRIG` dataset triggers, `EXTERNAL` waits (`ExternalTaskSensor`), `LINK` tasks, `NOTWITH` exclusion pools |
| **Level 4: Advanced Scheduling** | `data/samples/04_advanced_scheduling.esp` | `data/samples/04_scheduling_events.esp` | `GENTIME`, `IFHOLIDAYPLUS`, bi-weekly schedules, cyclic execution |
| **Level 5: Enterprise Production** | `data/samples/05_enterprise_production.esp` | `data/samples/05_enterprise_events.esp` | Full 11-application enterprise estate (>70 tasks) with end-to-end features |

You can also pass your own proprietary `.esp` schedule extracts and events files as arguments.

---

## CLI Commands

### 1. Generate Native Airflow 3 Python DAGs (`dag`)

Emits standalone, runnable Python DAG modules using Airflow 3 `airflow.sdk.DAG`:

```bash
python -m esp2dag dag data/samples/01_basic_batch.esp data/samples/01_basic_events.esp -o out/basic
```

Output:
```text
out/basic/
  dags/
    acct_daily_batch.py
    gl_posting.py
    report_distribution.py
```

### 2. Full Compilation (`compile`)

Emits native Python DAGs, DAG Factory YAML, visual workflow graphs (Mermaid & JSON), and migration/validation reports in a single pass:

```bash
python -m esp2dag compile data/samples/05_enterprise_production.esp data/samples/05_enterprise_events.esp -o out/enterprise
```

### 3. Generate DAG Factory YAML (`yaml`)

Emits DAG Factory-compatible YAML definitions (one YAML per ESP application):

```bash
python -m esp2dag yaml data/samples/02_multi_platform.esp data/samples/02_multi_platform_events.esp -o out/yaml_multi
```

Astronomer profile format (list of `dependencies`):

```bash
python -m esp2dag yaml data/samples/01_basic_batch.esp -o out/yaml_astro --profile astronomer
```

### 4. Generate Workflow Graphs Only (`graph`)

Exports dependency diagrams in Mermaid (`.mmd`), Graphviz DOT (`.dot`), and JSON graph structures:

```bash
python -m esp2dag graph data/samples/03_dependencies_and_triggers.esp -o out/graphs --format mermaid,json,graphviz
```

### 5. Generate Migration Reports Only (`report`)

Generates markdown and JSON audit reports summarizing task types, connections, exclusion pools, unsupported constructs, and validation warnings:

```bash
python -m esp2dag report data/samples/05_enterprise_production.esp data/samples/05_enterprise_events.esp -o out/reports
```

### 6. Extract Applications (`extract`)

Splits a monolithic multi-application schedule into individual application text files:

```bash
python -m esp2dag extract data/samples/05_enterprise_production.esp -o out/extracted_apps
```

---

## Interactive HTML Graph Visualizer

To visualize all compiled workflow graphs in an interactive browser UI with zoom, pan, and search:

```bash
python scripts/generate_html_visualizer.py
```

Open `out/graph_viewer.html` in your browser.

---

## Output Layout

```text
out/<run>/
  dags/*.py            # Native Apache Airflow 3 modules (one app per file)
  yaml/*.yaml          # DAG Factory documents (one file per application)
  graphs/*.mmd         # Mermaid diagrams
  graphs/*.json        # Structured JSON graphs
  reports/             # statistics.md, validation.md, migration.md, dependency.md
```

---

## Dependencies & Graph Mapping

| ESP Statement | Airflow Dependency |
|:---|:---|
| `RELEASE ADD(B)` inside job `A` | `A >> B` |
| `AFTER ADD(A)` inside job `B` | `A >> B` |
| `EXTERNAL APP.JOB` | Upstream `ExternalTaskSensor` |
| `NOTWITH (JOB_B)` | Concurrency pool (`slots = 1`) |

---

## Running Tests

Run the complete test suite (unit tests, golden AST/YAML/DAG tests, and integration suites):

```bash
python -m pytest
```

---

## License & Commercial Use

Public evaluation and learning are welcome. **Commercial and production use requires permission.**  
See [LICENSE](../LICENSE) and contact **amirsohelprowork@gmail.com**.
