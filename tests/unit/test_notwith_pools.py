"""Tests for ESP NOTWITH → shared Airflow exclusion pools."""

from __future__ import annotations

import yaml

from esp2dag.compiler.lexer import EspLexer
from esp2dag.compiler.parser import EspParser
from esp2dag.compiler.semantic import EspSemanticAnalyzer
from esp2dag.compiler.workflow import EspWorkflowBuilder, assign_notwith_pools
from esp2dag.models.source import SourceApplication
from esp2dag.yaml_generator import DagFactoryYamlGenerator


def _wf(content: str, *, name: str = "APP"):
    app = SourceApplication(
        name=name,
        source_file="t.esp",
        start_line=1,
        end_line=max(1, content.count("\n")),
        content=content,
        header_line=content.splitlines()[0] if content.strip() else None,
    )
    ast = EspParser().parse(EspLexer().tokenize(app), app)
    return EspWorkflowBuilder().build(ast, EspSemanticAnalyzer().analyze(ast).diagnostics)


def test_different_names_share_one_pool() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "NT_JOB ALPHA\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\A.bat\n"
        "  NOTWITH BETA\n"
        "  NOTWITH GAMMA\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB BETA\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\B.bat\n"
        "  NOTWITH ALPHA\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB GAMMA\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\C.bat\n"
        "  NOTWITH ALPHA\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    doc = yaml.safe_load(DagFactoryYamlGenerator().generate(_wf(content, name="DEMO")))
    tasks = doc["demo"]["tasks"]
    pools = {
        tasks["alpha"]["pool"],
        tasks["beta"]["pool"],
        tasks["gamma"]["pool"],
    }
    assert len(pools) == 1
    assert next(iter(pools)).startswith("nw_")


def test_onesided_notwith_still_groups() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "NT_JOB ALPHA\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\A.bat\n"
        "  NOTWITH BETA\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB BETA\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\B.bat\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wfs = assign_notwith_pools([_wf(content, name="DEMO")])
    by_name = {t.name: t for t in wfs[0].tasks}
    assert by_name["ALPHA"].pool == by_name["BETA"].pool
    assert by_name["ALPHA"].params["notwith_pool"].startswith("nw_")


def test_cross_application_same_pool() -> None:
    a = _wf(
        "APPL APP_A WAIT\n"
        "NT_JOB JOB_A\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\A.bat\n"
        "  NOTWITH JOB_B\n"
        "  RUN DAILY\n"
        "ENDJOB\n",
        name="APP_A",
    )
    b = _wf(
        "APPL APP_B WAIT\n"
        "NT_JOB JOB_B\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\SCRIPTS\\B.bat\n"
        "  NOTWITH JOB_A\n"
        "  RUN DAILY\n"
        "ENDJOB\n",
        name="APP_B",
    )
    a2, b2 = assign_notwith_pools([a, b])
    pool_a = a2.tasks[0].pool
    pool_b = b2.tasks[0].pool
    assert pool_a == pool_b
    assert pool_a.startswith("nw_")


def test_chain_collapses_to_one_group() -> None:
    """A–B and B–C ⇒ A,B,C share one pool (conservative connected component)."""
    content = (
        "APPL DEMO WAIT\n"
        "NT_JOB A\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\A.bat\n"
        "  NOTWITH B\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB B\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\B.bat\n"
        "  NOTWITH A\n"
        "  NOTWITH C\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB C\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\C.bat\n"
        "  NOTWITH B\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wfs = assign_notwith_pools([_wf(content, name="DEMO")])
    pools = {t.pool for t in wfs[0].tasks}
    assert len(pools) == 1


def test_collects_all_notwith_peers_in_params() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "NT_JOB A\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\A.bat\n"
        "  NOTWITH X\n"
        "  NOTWITH Y\n"
        "  NOTWITH Z\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wf = _wf(content, name="DEMO")
    peers = wf.tasks[0].params["notwith_peers"].split(",")
    assert peers == ["X", "Y", "Z"]


def test_two_disjoint_groups_get_different_pools() -> None:
    content = (
        "APPL DEMO WAIT\n"
        "NT_JOB A1\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\A1.bat\n"
        "  NOTWITH A2\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB A2\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\A2.bat\n"
        "  NOTWITH A1\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB B1\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\B1.bat\n"
        "  NOTWITH B2\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
        "NT_JOB B2\n"
        "  AGENT W1\n"
        "  CMDNAME D:\\B2.bat\n"
        "  NOTWITH B1\n"
        "  RUN DAILY\n"
        "ENDJOB\n"
    )
    wfs = assign_notwith_pools([_wf(content, name="DEMO")])
    by = {t.name: t.pool for t in wfs[0].tasks}
    assert by["A1"] == by["A2"]
    assert by["B1"] == by["B2"]
    assert by["A1"] != by["B1"]
