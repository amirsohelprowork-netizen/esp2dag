"""Typer CLI entrypoint."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from esp2dag import __version__
from esp2dag.compiler.factory import build_pipeline
from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.lexer.serialize import tokens_as_dicts, tokens_compact
from esp2dag.compiler.loader import infer_base_line, load_applications
from esp2dag.compiler.parser import EspParser, application_summary
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder, workflow_summary
from esp2dag.event_parser import EspEventMerger, EspEventParser
from esp2dag.extractor import ApplicationExtractor
from esp2dag.extractor.writer import write_extract_artifacts
from esp2dag.models.config import CompileRequest, CompilerConfig, GraphFormat
from esp2dag.models.diagnostics import DiagnosticCode, Severity
from esp2dag.models.source import SourceApplication, SourceFile
from esp2dag.utils import configure_logging

app = typer.Typer(
    name="esp2dag",
    help="ESP Workload Automation to DAG Factory YAML compiler.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(stderr=True)

_DESIGN_NOTE = (
    "[yellow]Phase 8 (native Airflow .py DAGs) is deferred.[/yellow] "
    "Phases 1–7 (YAML), 9 (graphs), and 10 (reports) are available. "
    "See docs/ARCHITECTURE.md."
)


def _not_ready(command: str) -> None:
    console.print(_DESIGN_NOTE)
    console.print(f"Command [bold]{command}[/bold] is not in scope for this migration.")
    raise typer.Exit(code=2)


@app.callback()
def _root(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """ESP to Airflow DAG Factory Builder."""
    configure_logging(logging.DEBUG if verbose else logging.INFO)


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command("extract")
def extract_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True, help="ESP schedule file."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Directory for extracted units + manifest.json."
    ),
) -> None:
    """Phase 1: discover applications in a schedule file."""
    content = schedule.read_text(encoding="utf-8", errors="replace")
    source = SourceFile(path=schedule.resolve(), content=content)
    result = ApplicationExtractor().extract(source)

    table = Table(title="Extracted ESP Applications")
    table.add_column("#", justify="right")
    table.add_column("Name")
    table.add_column("Start", justify="right")
    table.add_column("End", justify="right")
    table.add_column("Lines", justify="right")
    for index, app_unit in enumerate(result.applications, start=1):
        table.add_row(
            str(index),
            app_unit.name,
            str(app_unit.start_line),
            str(app_unit.end_line),
            str(app_unit.end_line - app_unit.start_line + 1),
        )
    console.print(table)
    console.print(
        f"Applications: {len(result.applications)} | "
        f"Diagnostics: {len(result.diagnostics)}"
    )
    for diagnostic in result.diagnostics:
        style = "red" if diagnostic.severity in {Severity.ERROR, Severity.FATAL} else "yellow"
        loc = ""
        if diagnostic.span is not None:
            loc = f"{diagnostic.span.file}:{diagnostic.span.start_line}: "
        console.print(
            f"[{style}]{diagnostic.severity} {diagnostic.code}[/{style}] {loc}{diagnostic.message}"
        )

    if output is not None:
        written = write_extract_artifacts(result, output)
        console.print(f"Wrote {len(written)} artifact(s) under {output}")

    has_errors = any(d.severity in {Severity.ERROR, Severity.FATAL} for d in result.diagnostics)
    if has_errors or not result.applications:
        raise typer.Exit(code=1)


def _infer_base_line(filename: str) -> int | None:
    """Parse ``NAME__L2377.esp`` extract artifact filenames."""
    return infer_base_line(filename)


def _load_applications(
    path: Path,
    *,
    base_line: int | None = None,
) -> list[SourceApplication]:
    """Load one or more applications from a unit or schedule file."""
    return load_applications(path, base_line=base_line)


def _run_pipeline(
    schedule: Path,
    events: Path | None,
    output: Path,
    *,
    limit: int = 0,
    profile: str = "default",
    emit_yaml: bool = False,
    emit_graph: bool = False,
    emit_reports: bool = False,
    graph_formats: list[GraphFormat] | None = None,
) -> None:
    """Shared CLI entry into CompilerPipeline."""
    formats = graph_formats or [GraphFormat.MERMAID, GraphFormat.JSON]
    request = CompileRequest(
        schedule_path=schedule,
        events_path=events,
        output_dir=output,
        options=CompilerConfig(
            emit_yaml=emit_yaml,
            emit_airflow=False,
            emit_graph=emit_graph,
            emit_reports=emit_reports,
            graph_formats=formats,
            dag_factory_profile=profile,
            max_applications=limit,
        ),
    )
    result = build_pipeline(profile=profile).run(request)

    yaml_n = sum(1 for a in result.artifacts if a.kind.value == "yaml")
    graph_n = sum(1 for a in result.artifacts if a.kind.value == "graph")
    report_n = sum(1 for a in result.artifacts if a.kind.value == "report")
    console.print(
        f"Workflows: {len(result.workflows)} | Failures: {len(result.failures)} | "
        f"YAML: {yaml_n} | Graphs: {graph_n} | Reports: {report_n}"
    )
    for artifact in result.artifacts:
        if artifact.path is not None:
            console.print(f"Wrote {artifact.path}")

    if not result.ok:
        raise typer.Exit(code=1)

@app.command("lex")
def lex_cmd(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Extracted application .esp or full schedule file.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Optional JSON file for token dump."
    ),
    limit: int = typer.Option(
        1,
        "--limit",
        "-n",
        help="Max applications to lex when input is a multi-app schedule.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Print TYPE:value lines instead of a table.",
    ),
    base_line: Optional[int] = typer.Option(
        None,
        "--base-line",
        help="Override absolute start line (default: parse __L<n> from filename).",
    ),
) -> None:
    """Phase 2: tokenize application unit(s)."""
    extracted = _load_applications(path, base_line=base_line)
    lexer = EspLexer()
    payload: list[dict[str, object]] = []
    for app_unit in extracted[: max(1, limit)]:
        tokens = lexer.tokenize(app_unit)
        payload.append(
            {
                "application": app_unit.name,
                "source_file": app_unit.source_file,
                "start_line": app_unit.start_line,
                "end_line": app_unit.end_line,
                "token_count": len(tokens),
                "tokens": tokens_as_dicts(tokens),
            }
        )
        console.print(
            f"[bold]{app_unit.name}[/bold] "
            f"({app_unit.start_line}-{app_unit.end_line}): {len(tokens)} tokens"
        )
        if compact:
            for line in tokens_compact(tokens):
                typer.echo(line)
        else:
            table = Table(title=f"Tokens — {app_unit.name}")
            table.add_column("Type")
            table.add_column("Value")
            table.add_column("Line", justify="right")
            table.add_column("Col", justify="right")
            for token in tokens[:50]:
                table.add_row(token.type.value, token.value, str(token.line), str(token.column))
            if len(tokens) > 50:
                table.add_row("...", f"({len(tokens) - 50} more)", "", "")
            console.print(table)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        console.print(f"Wrote {output}")


@app.command("parse")
def parse_cmd(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Extracted application .esp or full schedule file.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Optional JSON file for AST summary."
    ),
    limit: int = typer.Option(
        1,
        "--limit",
        "-n",
        help="Max applications to parse when input is a multi-app schedule.",
    ),
    base_line: Optional[int] = typer.Option(
        None,
        "--base-line",
        help="Override absolute start line (default: parse __L<n> from filename).",
    ),
) -> None:
    """Phase 3: parse application unit(s) into AST."""
    extracted = _load_applications(path, base_line=base_line)
    lexer = EspLexer()
    parser = EspParser()
    payload: list[dict[str, object]] = []
    exit_error = False

    for app_unit in extracted[: max(1, limit)]:
        tokens = lexer.tokenize(app_unit)
        result = parser.parse_with_diagnostics(tokens, app_unit)
        summary = application_summary(result.ast)
        payload.append(
            {
                "application": app_unit.name,
                "start_line": app_unit.start_line,
                "end_line": app_unit.end_line,
                "summary": summary,
                "diagnostics": [d.model_dump(mode="json") for d in result.diagnostics],
            }
        )
        console.print(
            f"[bold]{app_unit.name}[/bold]: {summary['job_count']} job(s), "
            f"{len(result.diagnostics)} diagnostic(s)"
        )
        table = Table(title=f"Jobs — {app_unit.name}")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Run")
        table.add_column("Deps")
        for job in result.ast.jobs:
            deps = ", ".join(
                f"{d.dependency_type}:{d.predecessor}" for d in job.dependencies
            )
            table.add_row(
                job.name,
                job.job_type or "JOB",
                job.schedule.expression if job.schedule else "",
                deps,
            )
        console.print(table)
        for diagnostic in result.diagnostics:
            style = "red" if diagnostic.severity in {Severity.ERROR, Severity.FATAL} else "yellow"
            console.print(
                f"[{style}]{diagnostic.severity} {diagnostic.code}[/{style}] {diagnostic.message}"
            )
        if result.has_errors:
            exit_error = True

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        console.print(f"Wrote {output}")

    if exit_error:
        raise typer.Exit(code=1)


@app.command("events")
def events_cmd(
    events: Path = typer.Argument(..., exists=True, readable=True, help="ESP events file."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Optional JSON catalog dump."
    ),
) -> None:
    """Phase 6a: parse ESP events file into a catalog."""
    source = SourceFile(
        path=events.resolve(),
        content=events.read_text(encoding="utf-8", errors="replace"),
    )
    result = EspEventParser().parse_with_diagnostics(source)
    console.print(
        f"Events: {len(result.catalog.events)} | Bindings: {len(result.catalog.bindings)} | "
        f"Diagnostics: {len(result.diagnostics)}"
    )
    table = Table(title="ESP Events (first 30)")
    table.add_column("ID")
    table.add_column("Kind")
    table.add_column("Application")
    table.add_column("Schedule")
    for event in result.catalog.events[:30]:
        table.add_row(
            event.name,
            event.kind.value,
            event.attributes.get("invoke_application", ""),
            (event.attributes.get("schedule", "") or "")[:40],
        )
    console.print(table)
    for diagnostic in result.diagnostics[:20]:
        style = "red" if diagnostic.severity in {Severity.ERROR, Severity.FATAL} else "yellow"
        console.print(
            f"[{style}]{diagnostic.severity} {diagnostic.code}[/{style}] {diagnostic.message}"
        )
    if output is not None:
        payload = {
            "source_file": result.catalog.source_file,
            "event_count": len(result.catalog.events),
            "binding_count": len(result.catalog.bindings),
            "events": [
                {
                    "name": e.name,
                    "kind": e.kind.value,
                    "attributes": e.attributes,
                    "start_line": e.span.start_line,
                    "end_line": e.span.end_line,
                }
                for e in result.catalog.events
            ],
            "diagnostics": [d.model_dump(mode="json") for d in result.diagnostics],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        console.print(f"Wrote {output}")
    if any(d.severity in {Severity.ERROR, Severity.FATAL} for d in result.diagnostics):
        raise typer.Exit(code=1)


@app.command("ir")
def ir_cmd(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Extracted application .esp or full schedule file.",
    ),
    events: Optional[Path] = typer.Option(
        None,
        "--events",
        "-e",
        exists=True,
        readable=True,
        help="Optional ESP events file to merge into IR.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Optional JSON file for workflow IR summary."
    ),
    limit: int = typer.Option(
        1,
        "--limit",
        "-n",
        help="Max applications to lower to IR when input is a multi-app schedule.",
    ),
    base_line: Optional[int] = typer.Option(
        None,
        "--base-line",
        help="Override absolute start line (default: parse __L<n> from filename).",
    ),
) -> None:
    """Phase 5–6: lower AST(s) to Workflow IR (optional event merge)."""
    extracted = _load_applications(path, base_line=base_line)
    lexer = EspLexer()
    parser = EspParser()
    analyzer = EspSemanticAnalyzer()
    builder = EspWorkflowBuilder()
    workflows = []
    payload: list[dict[str, object]] = []

    for app_unit in extracted[: max(1, limit)]:
        tokens = lexer.tokenize(app_unit)
        parse_result = parser.parse_with_diagnostics(tokens, app_unit)
        semantic = analyzer.analyze(parse_result.ast)
        diagnostics = list(parse_result.diagnostics) + list(semantic.diagnostics)
        workflows.append(builder.build(parse_result.ast, diagnostics))

    merge_diags = []
    if events is not None:
        event_source = SourceFile(
            path=events.resolve(),
            content=events.read_text(encoding="utf-8", errors="replace"),
        )
        catalog = EspEventParser().parse(event_source)
        merge_result = EspEventMerger().merge_with_diagnostics(workflows, catalog)
        workflows = merge_result.workflows
        merge_diags = list(merge_result.diagnostics)

    for workflow in workflows:
        summary = workflow_summary(workflow)
        payload.append(
            {
                "application": workflow.name,
                "workflow": summary,
                "event_count": len(workflow.events),
            }
        )
        console.print(
            f"[bold]{workflow.id}[/bold] ({workflow.name}): "
            f"{summary['task_count']} tasks, {summary['dependency_count']} edges, "
            f"{len(workflow.events)} event(s)"
        )
        if workflow.schedule:
            console.print(f"Schedule: {workflow.schedule.raw_expression}")
        table = Table(title=f"Workflow IR — {workflow.name}")
        table.add_column("task_id")
        table.add_column("type")
        table.add_column("line", justify="right")
        table.add_column("command")
        for task in workflow.tasks:
            cmd = (task.command or "")[:40]
            table.add_row(task.task_id, task.task_type.value, str(task.trace.source_line), cmd)
        console.print(table)
        if workflow.dependencies:
            console.print(
                "Edges: "
                + ", ".join(
                    f"{d.upstream_task_id}->{d.downstream_task_id}"
                    for d in workflow.dependencies[:12]
                )
                + (" ..." if len(workflow.dependencies) > 12 else "")
            )

    for diagnostic in merge_diags:
        if diagnostic.code == DiagnosticCode.W_EVENT_ORPHAN:
            continue
        console.print(
            f"[yellow]{diagnostic.severity} {diagnostic.code}[/yellow] {diagnostic.message}"
        )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        console.print(f"Wrote {output}")


@app.command("analyze")
def analyze_cmd(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Extracted application .esp or full schedule file.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Optional JSON file for diagnostics."
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        "-n",
        help="Max applications to analyze (0 = all).",
    ),
    base_line: Optional[int] = typer.Option(
        None,
        "--base-line",
        help="Override absolute start line (default: parse __L<n> from filename).",
    ),
) -> None:
    """Phase 4: semantic analysis of application AST(s)."""
    extracted = _load_applications(path, base_line=base_line)
    units = extracted if limit <= 0 else extracted[:limit]
    lexer = EspLexer()
    parser = EspParser()
    analyzer = EspSemanticAnalyzer()
    asts = []
    per_app: list[dict[str, object]] = []
    exit_error = False

    for app_unit in units:
        tokens = lexer.tokenize(app_unit)
        parse_result = parser.parse_with_diagnostics(tokens, app_unit)
        semantic = analyzer.analyze(parse_result.ast)
        asts.append(parse_result.ast)
        combined = list(parse_result.diagnostics) + list(semantic.diagnostics)
        per_app.append(
            {
                "application": app_unit.name,
                "start_line": app_unit.start_line,
                "job_count": len(parse_result.ast.jobs),
                "diagnostics": [d.model_dump(mode="json") for d in combined],
            }
        )
        errors = sum(1 for d in combined if d.severity in {Severity.ERROR, Severity.FATAL})
        warnings = sum(1 for d in combined if d.severity == Severity.WARNING)
        console.print(
            f"[bold]{app_unit.name}[/bold]: "
            f"{len(parse_result.ast.jobs)} jobs, {errors} error(s), {warnings} warning(s)"
        )
        for diagnostic in combined:
            style = "red" if diagnostic.severity in {Severity.ERROR, Severity.FATAL} else "yellow"
            console.print(
                f"[{style}]{diagnostic.severity} {diagnostic.code}[/{style}] {diagnostic.message}"
            )
        if errors:
            exit_error = True

    cross_dupes = (
        analyzer.cross_application_diagnostics(asts) if len(asts) > 1 else []
    )
    for diagnostic in cross_dupes:
        console.print(f"[red]{diagnostic.severity} {diagnostic.code}[/red] {diagnostic.message}")
        exit_error = True
        per_app.append({"application": diagnostic.application, "diagnostics": [diagnostic.model_dump(mode="json")]})

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(per_app, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        console.print(f"Wrote {output}")

    if exit_error:
        raise typer.Exit(code=1)


@app.command("validate")
def validate_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True),
    events: Optional[Path] = typer.Argument(None, exists=True, readable=True),
) -> None:
    """Run extract → lex → parse → semantic validation (use ``ir -e`` for event merge)."""
    _ = events
    analyze_cmd(path=schedule, output=None, limit=0, base_line=None)


@app.command("compile")
def compile_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True),
    events: Optional[Path] = typer.Argument(None, exists=True, readable=True),
    output: Path = typer.Option(Path("out"), "--output", "-o"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max apps (0=all)."),
    profile: str = typer.Option("default", "--profile", help="YAML profile: default|astronomer"),
) -> None:
    """Full compile: YAML + graphs + reports (Airflow .py deferred)."""
    _run_pipeline(
        schedule,
        events,
        output,
        limit=limit,
        profile=profile,
        emit_yaml=True,
        emit_graph=True,
        emit_reports=True,
        graph_formats=[GraphFormat.MERMAID, GraphFormat.JSON],
    )


@app.command("yaml")
def yaml_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True),
    events: Optional[Path] = typer.Argument(None, exists=True, readable=True),
    output: Path = typer.Option(Path("out"), "--output", "-o"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max apps (0=all)."),
    profile: str = typer.Option("default", "--profile", help="YAML profile: default|astronomer"),
) -> None:
    """Generate DAG Factory YAML from schedule (+ optional events)."""
    _run_pipeline(
        schedule,
        events,
        output,
        limit=limit,
        profile=profile,
        emit_yaml=True,
        emit_graph=False,
        emit_reports=False,
    )


@app.command("dag")
def dag_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True),
    events: Optional[Path] = typer.Argument(None, exists=True, readable=True),
    output: Path = typer.Option(Path("out"), "--output", "-o"),
) -> None:
    """Optional Airflow DAG Python generation (deferred — YAML is the deliverable)."""
    _ = (schedule, events, output)
    _not_ready("dag")


@app.command("graph")
def graph_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True),
    events: Optional[Path] = typer.Argument(None, exists=True, readable=True),
    output: Path = typer.Option(Path("out"), "--output", "-o"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max apps (0=all)."),
    fmt: str = typer.Option(
        "mermaid,json",
        "--format",
        "-f",
        help="Comma-separated formats: mermaid,json,graphviz",
    ),
) -> None:
    """Generate dependency graphs (Mermaid / JSON / Graphviz DOT)."""
    formats: list[GraphFormat] = []
    for part in fmt.split(","):
        part = part.strip().lower()
        if not part:
            continue
        formats.append(GraphFormat(part))
    if not formats:
        formats = [GraphFormat.MERMAID, GraphFormat.JSON]
    _run_pipeline(
        schedule,
        events,
        output,
        limit=limit,
        emit_yaml=False,
        emit_graph=True,
        emit_reports=False,
        graph_formats=formats,
    )


@app.command("report")
def report_cmd(
    schedule: Path = typer.Argument(..., exists=True, readable=True),
    events: Optional[Path] = typer.Argument(None, exists=True, readable=True),
    output: Path = typer.Option(Path("out"), "--output", "-o"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max apps (0=all)."),
) -> None:
    """Generate migration / validation / statistics reports."""
    _run_pipeline(
        schedule,
        events,
        output,
        limit=limit,
        emit_yaml=False,
        emit_graph=False,
        emit_reports=True,
    )

def main() -> None:
    """Console script entry."""
    app()


if __name__ == "__main__":
    main()
