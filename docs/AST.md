# AST Node Reference

The Abstract Syntax Tree is the **ESP-native** representation produced by the parser.
It retains ESP vocabulary and structure. It must **never** be consumed by YAML or Airflow generators.

All nodes inherit `AstNode` and carry a `SourceSpan`.

---

## Base

### `SourceSpan`
| Field | Type | Description |
|---|---|---|
| file | `str` | Absolute or normalized source path |
| start_line | `int` | 1-based |
| start_column | `int` | 1-based |
| end_line | `int` | 1-based |
| end_column | `int` | 1-based |
| text | `str \| None` | Optional original statement snippet |

### `AstNode` (abstract)
| Field | Type |
|---|---|
| span | `SourceSpan` |
| node_type | `str` (discriminator) |

Supports `accept(visitor: AstVisitor) -> T`.

---

## Structural Nodes

### `ApplicationNode`
| Field | Type | Notes |
|---|---|---|
| name | `str` | APPLICATION id |
| jobs | `list[JobNode]` | Ordered as in source |
| calendars | `list[CalendarNode]` | |
| schedules | `list[ScheduleNode]` | |
| resources | `list[ResourceNode]` | |
| variables | `list[VariableNode]` | |
| notifications | `list[NotificationNode]` | App-level |
| metadata | `list[MetadataNode]` | Free-form ESP attributes |
| raw_header | `str \| None` | Preserved APPLICATION line |

### `JobNode`
| Field | Type | Notes |
|---|---|---|
| name | `str` | |
| job_type | `str \| None` | JOB / LINK / etc. if distinguished |
| command | `CommandNode \| None` | |
| dependencies | `list[DependencyNode]` | Predecessors |
| conditions | `list[ConditionNode]` | |
| resources | `list[ResourceRefNode]` | |
| retry | `RetryNode \| None` | |
| notifications | `list[NotificationNode]` | |
| event_refs | `list[EventReferenceNode]` | From schedule side |
| schedule | `ScheduleNode \| None` | Job-level schedule override |
| variables | `list[VariableNode]` | |
| metadata | `list[MetadataNode]` | |
| unsupported | `list[UnsupportedStatementNode]` | Parked for diagnostics |

---

## Relationship & Constraint Nodes

### `DependencyNode`
| Field | Type |
|---|---|
| predecessor | `str` |
| dependency_type | `str \| None` | e.g. AFTER, RELEASE |
| condition | `ConditionNode \| None` |

### `ConditionNode`
| Field | Type |
|---|---|
| expression | `str` |
| kind | `str \| None` | IF / WHEN / etc. |

### `ResourceNode` / `ResourceRefNode`
| Field | Type |
|---|---|
| name | `str` |
| quantity | `int \| None` |
| attributes | `dict[str, str]` |

### `CalendarNode`
| Field | Type |
|---|---|
| name | `str` |
| definition | `str` | Opaque ESP calendar body for v1 |
| attributes | `dict[str, str]` |

### `ScheduleNode`
| Field | Type |
|---|---|
| expression | `str` | ESP schedule text |
| calendar_ref | `str \| None` |
| attributes | `dict[str, str]` |

### `VariableNode`
| Field | Type |
|---|---|
| name | `str` |
| value | `str` |
| scope | `str \| None` | appl / job |

### `EventReferenceNode`
| Field | Type |
|---|---|
| event_name | `str` |
| event_kind | `str \| None` |
| attributes | `dict[str, str]` |

### `NotificationNode`
| Field | Type |
|---|---|
| channel | `str \| None` |
| recipients | `list[str]` |
| on_event | `str \| None` | success/failure/etc. |
| message | `str \| None` |

### `RetryNode`
| Field | Type |
|---|---|
| max_attempts | `int \| None` |
| interval | `str \| None` |
| attributes | `dict[str, str]` |

### `CommandNode`
| Field | Type |
|---|---|
| text | `str` |
| interpreter | `str \| None` |
| attributes | `dict[str, str]` |

### `MetadataNode`
| Field | Type |
|---|---|
| key | `str` |
| value | `str` |

### `UnsupportedStatementNode`
| Field | Type |
|---|---|
| keyword | `str` |
| raw | `str` |
| reason | `str` |

---

## Design Notes

1. **Opaque strings for v1 schedules/calendars** — full ESP calendar algebra is deferred; semantic analysis flags what cannot be mapped.
2. **`UnsupportedStatementNode`** — parser recovery parks unknown constructs instead of aborting the job.
3. **No Airflow types in AST** — sensors, operators, pools live only in Workflow IR / generators.
4. **Visitor pattern** — semantic rules and IR builder use `AstVisitor` to avoid giant match statements in one God class (rules may still pattern-match node types locally).
