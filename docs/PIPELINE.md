# Compiler Pipeline Contracts

## Orchestrator: `CompilerPipeline`

```python
class CompilerPipeline:
    def run(self, request: CompileRequest) -> CompileResult: ...
```

### `CompileRequest`
| Field | Type |
|---|---|
| schedule_path | `Path` |
| events_path | `Path \| None` |
| output_dir | `Path` |
| options | `CompilerConfig` |

### `CompilerConfig`
| Field | Default | Meaning |
|---|---|---|
| emit_yaml | `True` | |
| emit_airflow | `False` | |
| emit_graph | `True` | |
| emit_reports | `True` | |
| graph_formats | `["mermaid", "json"]` | |
| fail_on_warnings | `False` | |
| continue_on_error | `True` | Always True in v1 philosophy |
| task_id_style | `"sanitize"` | |
| dag_factory_profile | `"default"` | YAML shape profile |

### `CompileResult`
| Field | Type |
|---|---|
| workflows | `list[Workflow]` |
| artifacts | `list[ArtifactRef]` |
| failures | `list[FailedUnit]` |
| diagnostics | `list[Diagnostic]` |
| statistics | `CompileStatistics` |

---

## Stage Protocols

```python
class ApplicationExtractor(Protocol):
    def extract(self, source: SourceFile) -> ExtractResult: ...

class Lexer(Protocol):
    def tokenize(self, application: SourceApplication) -> list[Token]: ...

class Parser(Protocol):
    def parse(self, tokens: list[Token], application: SourceApplication) -> ApplicationNode: ...

class SemanticAnalyzer(Protocol):
    def analyze(self, ast: ApplicationNode) -> SemanticResult: ...

class WorkflowBuilder(Protocol):
    def build(self, ast: ApplicationNode, diagnostics: list[Diagnostic]) -> Workflow: ...

class EventParser(Protocol):
    def parse(self, source: SourceFile) -> EventCatalog: ...

class EventMerger(Protocol):
    def merge(self, workflows: list[Workflow], catalog: EventCatalog) -> list[Workflow]: ...

class WorkflowValidator(Protocol):
    def validate(self, workflow: Workflow) -> list[Diagnostic]: ...

class YamlGenerator(Protocol):
    def generate(self, workflow: Workflow) -> str: ...

class AirflowGenerator(Protocol):
    def generate(self, workflow: Workflow) -> str: ...

class GraphGenerator(Protocol):
    def generate(self, workflow: Workflow, fmt: GraphFormat) -> str: ...

class ReportGenerator(Protocol):
    def generate(self, result: CompileResult) -> list[ArtifactRef]: ...
```

---

## Per-Application Frontend Loop

```
for app in extract_result.applications:
    try:
        tokens = lexer.tokenize(app)
        ast = parser.parse(tokens, app)
        semantic = analyzer.analyze(ast)
        diagnostics.extend(semantic.diagnostics)
        if semantic.has_errors and config.skip_ir_on_semantic_error:
            failures.append(...)
            continue
        workflow = builder.build(ast, semantic.diagnostics)
        workflows.append(workflow)
    except LexerError | ParserError as exc:
        failures.append(FailedUnit.from_exception(app, stage, exc))
        continue
```

---

## CLI → Pipeline Mapping

| Command | Stages executed |
|---|---|
| `esp2dag extract` | 1 → print/write application list |
| `esp2dag validate` | 1–6 + workflow validation (no emit) |
| `esp2dag compile` | 1–10 (full, per config) |
| `esp2dag yaml` | 1–7 |
| `esp2dag dag` | 1–8 |
| `esp2dag graph` | 1–6 + 9 |
| `esp2dag report` | 1–6 + 10 |

Shared: all commands reuse `CompilerPipeline` with feature flags — **no duplicated orchestration logic in CLI**.

---

## Diagnostics

### `Severity`
`INFO` | `WARNING` | `ERROR` | `FATAL`

### `Diagnostic`
| Field | Type |
|---|---|
| code | `str` | e.g. `E001`, `W012` |
| severity | `Severity` |
| message | `str` |
| stage | `str` |
| span | `SourceSpan \| None` |
| application | `str \| None` |
| job | `str \| None` |
| hint | `str \| None` |

Diagnostic codes live in `esp2dag/models/diagnostic_codes.py` (registry).

---

## Testing Expectations Per Stage

| Test kind | Purpose |
|---|---|
| Unit | Stage in isolation with fixtures |
| Integration | Two+ stages wired |
| Golden | Exact token/AST/YAML/graph snapshots |
| Regression | Previously failing ESP snippets |

Golden files stored under `tests/golden/<stage>/`.
