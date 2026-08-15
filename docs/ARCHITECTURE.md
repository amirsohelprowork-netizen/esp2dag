# ESP to Airflow DAG Factory Builder — Architecture

**Project:** `esp2dag`  
**Nature:** Compiler (not a text converter)  
**Target:** ESP Workload Automation → native Apache Airflow 3 DAGs (plus optional DAG Factory YAML)  
**Status:** Native Airflow 3 DAG and DAG Factory YAML backends implemented

---

## 1. Design Philosophy

This project is a **multi-stage compiler**, not a string rewriter.

| Compiler concept | ESP → Airflow mapping |
|---|---|
| Source language | ESP schedule + events syntax |
| Frontend | Extractor → Lexer → Parser → AST |
| Middle-end | Semantic analysis → Intermediate Workflow Model (IR) → Event merge |
| Backend | YAML generator, Airflow generator, graphs, reports |
| Diagnostics | Structured errors/warnings that never halt the whole compile |

**Hard invariant:** Nothing after Intermediate Representation (IR) understands ESP syntax.  
ESP knowledge stops at the AST → Workflow boundary. Downstream stages consume only the Workflow Model.

**Hard invariant:** Every emitted task retains full source traceability (file, application, job, line, statement).

**Hard invariant:** Application-level fault isolation — one failed application never aborts the batch.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI (Typer)                                │
│  extract | validate | compile | yaml | dag | graph | report             │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CompilerPipeline                                │
│  Orchestrates stages; collects Diagnostics; never fails-fast globally   │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────────┐
│ Schedule File │        │  Events File  │        │  Config / Options │
└───────┬───────┘        └───────┬───────┘        └───────────────────┘
        │                        │
        ▼                        │
┌───────────────────┐            │
│ Application       │            │
│ Extractor         │            │
│ (Phase 1)         │            │
└─────────┬─────────┘            │
          │ List[SourceApplication]
          ▼
┌───────────────────┐            │
│ Per-Application   │            │
│ Frontend          │            │
│ Lexer → Parser    │            │
│ → AST             │            │
│ (Phases 2–3)      │            │
└─────────┬─────────┘            │
          │ List[ApplicationAST | FailedUnit]
          ▼
┌───────────────────┐            │
│ Semantic Analyzer │            │
│ (Phase 4)         │            │
└─────────┬─────────┘            │
          │ Validated AST + Diagnostics
          ▼
┌───────────────────┐            │
│ IR Builder        │            │
│ AST → Workflow    │            │
│ (Phase 5)         │            │
└─────────┬─────────┘            │
          │ Workflow              │
          ▼                       ▼
┌──────────────────────────────────────────┐
│ Event Parser + Event Merger (Phase 6)    │
│ Enrich Workflow with sensors/triggers    │
└────────────────────┬─────────────────────┘
                     │ Enriched Workflow
                     ▼
┌──────────────────────────────────────────┐
│ Workflow Validators                      │
└────────────────────┬─────────────────────┘
                     │
     ┌───────────────┼───────────────┬──────────────┐
     ▼               ▼               ▼              ▼
 YAML Gen      Airflow Gen      Graph Gen      Report Gen
 (Phase 7)     (Phase 8)       (Phase 9)     (Phase 10)
```

---

## 3. Package Layout

```
esp2dag/
├── pyproject.toml
├── README.md
├── docs/
│   ├── ARCHITECTURE.md          # this document
│   ├── AST.md                   # AST node reference
│   ├── WORKFLOW_MODEL.md        # IR reference
│   └── PIPELINE.md              # stage contracts & data flow
├── src/esp2dag/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py               # Typer entry
│   │   └── commands/            # one module per command
│   ├── compiler/
│   │   ├── __init__.py
│   │   ├── pipeline.py          # CompilerPipeline orchestrator
│   │   ├── context.py           # CompileContext (shared state)
│   │   ├── lexer/
│   │   │   ├── __init__.py
│   │   │   ├── token.py
│   │   │   ├── token_types.py
│   │   │   └── lexer.py
│   │   ├── parser/
│   │   │   ├── __init__.py
│   │   │   └── parser.py
│   │   ├── ast/
│   │   │   ├── __init__.py
│   │   │   ├── nodes.py         # AST node types
│   │   │   └── visitor.py       # ASTVisitor base
│   │   ├── semantic/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py
│   │   │   └── rules/           # one rule class per check
│   │   └── workflow/
│   │       ├── __init__.py
│   │       └── builder.py       # AST → Workflow IR
│   ├── extractor/
│   │   ├── __init__.py
│   │   └── application_extractor.py
│   ├── event_parser/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── merger.py
│   ├── yaml_generator/
│   │   ├── __init__.py
│   │   └── dag_factory_yaml.py
│   ├── airflow_generator/
│   │   ├── __init__.py
│   │   └── dag_writer.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── mermaid.py
│   │   ├── graphviz.py
│   │   └── json_graph.py
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── migration.py
│   │   ├── validation.py
│   │   ├── dependency.py
│   │   └── statistics.py
│   ├── validators/
│   │   ├── __init__.py
│   │   └── workflow_validator.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── source.py            # SourceLocation, SourceApplication
│   │   ├── diagnostics.py       # Diagnostic, Severity
│   │   ├── events.py            # Event domain models
│   │   ├── workflow.py          # Intermediate Workflow Model
│   │   ├── compile_result.py    # CompileResult aggregate
│   │   └── config.py            # CompilerConfig
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       ├── ids.py
│       └── determinism.py
└── tests/
    ├── unit/
    ├── integration/
    ├── golden/
    └── fixtures/
        ├── schedules/
        └── events/
```

---

## 4. Domain Boundaries (SOLID)

### Single Responsibility
Each stage is a class with one public method (e.g. `extract()`, `tokenize()`, `parse()`, `analyze()`, `build()`, `merge()`, `generate()`).

### Open/Closed
Semantic rules and YAML task mappers are registered plugins/lists — add a rule without editing the analyzer core.

### Liskov
All AST nodes inherit `AstNode`; visitors treat them uniformly via `accept()`.

### Interface Segregation
Generators depend only on `Workflow`, not on lexer/parser types.

### Dependency Inversion
`CompilerPipeline` depends on stage *protocols* (`Extractor`, `Lexer`, `Parser`, …), not concrete classes. Concrete classes are wired in composition root / CLI.

---

## 5. Stage Contracts (Summary)

See `docs/PIPELINE.md` for full I/O contracts.

| Phase | Component | Input | Output |
|------|-----------|-------|--------|
| 1 | `ApplicationExtractor` | schedule path + text | `list[SourceApplication]` |
| 2 | `Lexer` | `SourceApplication` | `list[Token]` |
| 3 | `Parser` | `list[Token]` | `ApplicationNode` (AST) |
| 4 | `SemanticAnalyzer` | `ApplicationNode` | AST + `list[Diagnostic]` |
| 5 | `WorkflowBuilder` | validated AST | `Workflow` |
| 6 | `EventParser` + `EventMerger` | events file + `Workflow`s | enriched `Workflow`s |
| 7 | `DagFactoryYamlGenerator` | `Workflow` | deterministic YAML string/path |
| 8 | `AirflowDagGenerator` | YAML or `Workflow` | Python DAG module(s) |
| 9 | `GraphGenerator` | `Workflow` | Mermaid / Graphviz / JSON |
| 10 | `ReportGenerator` | `CompileResult` | Markdown/JSON reports |

---

## 6. Error Handling Strategy

```
CompileResult
├── successes: list[WorkflowArtifact]
├── failures: list[FailedUnit]      # per-application or per-stage
└── diagnostics: list[Diagnostic]   # global + per-unit
```

Rules:
1. Extractor always returns what it can; malformed boundaries produce diagnostics + partial units when possible.
2. Frontend (lex/parse/semantic) runs **per application** inside try/except (or Result monads).
3. Failures are recorded as `FailedUnit(application_id, stage, diagnostics, source_span)`.
4. Downstream stages skip failed units.
5. Exit codes:
   - `0` — success, no errors (warnings OK)
   - `1` — one or more application errors
   - `2` — fatal I/O / config error (cannot start)

---

## 7. Determinism

Identical inputs → identical outputs.

Mechanisms:
- Sorted maps/keys when emitting YAML (`sort_keys=True`, stable key order in models).
- Stable task ID generation from ESP job names (sanitized, documented rules).
- No timestamps in generated YAML unless sourced from ESP.
- Ordered collections in Pydantic models (`list` not `set` for emitted fields).
- Canonical newline (`\n`) and UTF-8 encoding.
- Graph edge order: topological then lexical by task_id.

Utility: `esp2dag.utils.determinism.canonical_dumps()`.

---

## 8. Traceability Model

Every IR task embeds:

```python
class SourceTrace(BaseModel):
    source_file: str
    source_application: str
    source_job: str | None
    source_line: int
    source_column: int | None
    source_statement: str | None
```

Propagated into DAG Factory YAML under `metadata:` and into Airflow DAG comments / `params` / `doc_md` as configured.

---

## 9. Event Mapping Strategy

| ESP event kind | Workflow enrichment | Typical Airflow / DAG Factory mapping |
|---|---|---|
| File event | `FileEvent` on task or workflow | `FileSensor` (or sensor task upstream) |
| Time event | schedule / timetable hint | DAG `schedule` / timetable |
| Trigger / appl event | inter-task or external dependency | `depends_on` / `ExternalTaskSensor` / trigger rule |
| Resource event | resource constraint | pool / slot |

Event merger is **pure enrichment**: it mutates/copies Workflow IR only; it does not re-parse ESP job bodies.

---

## 10. Trade-offs & Decisions

### Why recursive descent (not PEG / ANTLR)?
- ESP dialect varies by site; hand-written RD parser is easier to extend with recovery.
- Full control over error messages and source spans.
- No generated-parser build step in Poetry consumers.
- Trade-off: more manual grammar maintenance.

### Why Application Extractor before Lexer?
- Schedule files can be huge multi-app blobs.
- Fault isolation requires application boundaries *before* deep parse.
- Enables parallel frontend later without changing IR.
- Trade-off: extractor must be resilient to nested/odd `APPLICATION`/`ENDAPPL` patterns.

### Why Pydantic v2 for AST and IR?
- Validation + serialization for free.
- Clear contracts for golden tests.
- Trade-off: slightly heavier than dataclasses; acceptable for compiler IR.

### Why Workflow IR before YAML?
- Prevents ESP leakage into generators.
- Enables multiple backends (DAG Factory, native Airflow, graphs) without N parsers.
- Trade-off: mapping layer maintenance.

### Why not stop on first error?
- Migration of hundreds of apps requires partial success.
- Matches enterprise migration tooling expectations.

### Why Poetry + Python 3.12?
- Lockfile reproducibility; modern typing (`list | None`, `type` aliases).

---

## Phase 1 notes (from real ESP inputs)

Akron/Bandag schedule extracts use:

```text
APPL APPNAME [WAIT|JOB_ANCESTOR_WAIT|...]
  ... jobs / controls ...
APPL NEXTAPP ...
```

There is typically **no** `ENDAPPL`. The extractor treats the next `APPL`/`APPLICATION`
statement (first keyword on a line, comments stripped) as the boundary.
`APPLICATION`/`ENDAPPL` remain supported for legacy/simple fixtures.

Do **not** treat `APPL(...)` inside expressions (e.g. `COMPLETE APPL(FOO.0)`) or
comment text as application starts.


Approved sequence — **one stage at a time**, each with unit + golden tests before the next:

1. Models + diagnostics + `SourceApplication` (foundation)
2. Phase 1 — Application Extractor
3. Phase 2 — Lexer
4. Phase 3 — Parser + AST
5. Phase 4 — Semantic Analyzer
6. Phase 5 — Workflow Builder (IR)
7. Phase 6 — Event Parser + Merger
8. Phase 7 — DAG Factory YAML Generator
9. Phase 8 — Airflow Generator (native Python DAG backend)
10. Phase 9 — Graphs
11. Phase 10 — Reports
12. CLI wiring + integration/e2e tests

Phase 8 emits deterministic Airflow 3 modules using `airflow.sdk.DAG` and the same Workflow IR used by the YAML backend.

Phase 7 emits deterministic DAG Factory YAML (`default` dict/`depends_on` profile,
or `--profile astronomer` list/`dependencies`) with mandatory ESP source metadata.

---

## 12. Non-Goals (v1)

- Full ESP feature parity (unsupported constructs → diagnostics + manual-review flags)
- Live ESP server connectivity
- Bidirectional Airflow → ESP
- GUI
- Auto-remediation of circular dependencies (detect + report only)
