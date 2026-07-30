# Intermediate Workflow Model (IR)

Scheduler-independent representation. After `WorkflowBuilder`, **no stage may import AST or ESP token types**.

---

## Aggregate Root: `Workflow`

One Workflow ≈ one ESP Application ≈ one Airflow DAG (default mapping).

| Field | Type | Description |
|---|---|---|
| id | `str` | Stable workflow id (sanitized application name) |
| name | `str` | Display / original application name |
| metadata | `WorkflowMetadata` | |
| tasks | `list[Task]` | Ordered deterministically |
| dependencies | `list[Dependency]` | Explicit edges |
| schedule | `ScheduleSpec \| None` | |
| variables | `list[Variable]` | |
| resources | `list[Resource]` | |
| events | `list[WorkflowEvent]` | Merged from events file + schedule refs |
| retry_policies | `list[RetryPolicy]` | Named or default policies |
| notifications | `list[Notification]` | |
| diagnostics | `list[Diagnostic]` | Attached during build/merge (optional copy) |

---

## `WorkflowMetadata`

| Field | Type |
|---|---|
| source_scheduler | `Literal["ESP"]` |
| source_application | `str` |
| source_file | `str` |
| source_span | `SourceSpan` |
| description | `str \| None` |
| tags | `list[str]` |
| conversion_version | `str` | Compiler version for provenance |

---

## `Task`

| Field | Type | Description |
|---|---|---|
| task_id | `str` | Airflow-safe, deterministic |
| name | `str` | Original job name |
| task_type | `TaskType` | Enum — see below |
| command | `str \| None` | |
| pool | `str \| None` | |
| priority_weight | `int \| None` | |
| retry_policy_id | `str \| None` | |
| trigger_rule | `str \| None` | Set by event merger / mapping |
| sla | `str \| None` | |
| sensor | `SensorSpec \| None` | File/time/external |
| branch | `BranchSpec \| None` | |
| group_id | `str \| None` | TaskGroup membership |
| params | `dict[str, str]` | Free-form mapped params |
| trace | `SourceTrace` | **Mandatory** |
| unsupported_features | `list[str]` | Manual review flags |

### `TaskType` (enum)
`EMPTY` | `BASH` | `PYTHON` | `BRANCH_PYTHON` | `SENSOR_FILE` | `SENSOR_EXTERNAL` | `TASK_GROUP` | `UNKNOWN`

Default mapping from ESP JOB without richer type info: `BASH` if command present, else `EMPTY`.

---

## `Dependency`

| Field | Type |
|---|---|
| upstream_task_id | `str` |
| downstream_task_id | `str` |
| kind | `DependencyKind` | `SUCCESS` \| `COMPLETION` \| `CUSTOM` |
| condition | `str \| None` |
| trace | `SourceTrace \| None` |

---

## `ScheduleSpec`

| Field | Type |
|---|---|
| raw_expression | `str` | Original ESP |
| cron | `str \| None` | If mappable |
| timetable | `str \| None` | Future |
| calendar_ref | `str \| None` |
| start_date | `str \| None` | ISO date if known |
| catchup | `bool \| None` | Default false for migrations |
| mapping_status | `MappingStatus` | `MAPPED` \| `PARTIAL` \| `UNSUPPORTED` |

---

## `Variable` / `Resource` / `RetryPolicy` / `Notification`

Standard named value objects with optional `SourceTrace`.

---

## `WorkflowEvent`

| Field | Type |
|---|---|
| event_id | `str` |
| kind | `EventKind` | `FILE` \| `TIME` \| `TRIGGER` \| `APPLICATION` \| `RESOURCE` \| `UNKNOWN` |
| target_task_id | `str \| None` | |
| payload | `dict[str, str]` | Path, pattern, appl name, etc. |
| mapped_as | `EventMapping` | How merger applied it |
| trace | `SourceTrace` | |

### `EventMapping`
`FILE_SENSOR` | `SCHEDULE` | `DEPENDENCY` | `TRIGGER_RULE` | `EXTERNAL_SENSOR` | `UNMAPPED`

---

## `SensorSpec`

| Field | Type |
|---|---|
| sensor_type | `Literal["file", "external_task", "time"]` |
| filepath | `str \| None` |
| external_dag_id | `str \| None` |
| external_task_id | `str \| None` |
| poke_interval | `int \| None` |
| timeout | `int \| None` |
| mode | `str \| None` |

---

## Mapping Principles

1. **IR is complete enough for YAML** — generators should not re-interpret ESP.
2. **Unknown → flagged, not dropped silently** — `unsupported_features` + diagnostics.
3. **Events enrich, they don't replace** schedule-derived dependencies unless explicitly modeled as overrides (documented in merger).
4. **Deterministic task_id**: `sanitize(job_name)` with collision suffix `_2`, `_3`, … based on declaration order.

---

## Relationship to DAG Factory YAML

```
Workflow.id          → dag.dag_id
Workflow.schedule    → dag.schedule / start_date / catchup
Workflow.tasks[]     → tasks.<task_id>
Dependency edges     → tasks.<id>.depends_on
Task.trace           → tasks.<id>.metadata.source_*
Task.sensor          → sensor operator fields
```

Exact YAML schema alignment will be confirmed against the user's existing DAG Factory project in Phase 7 (adapter profile / template).
