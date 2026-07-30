"""ESP recursive descent parser — Phase 3.

Converts lexer tokens into an ``ApplicationNode`` AST. Never emits Airflow or YAML.
Unknown constructs are parked as ``UnsupportedStatementNode`` with diagnostics.
"""

from __future__ import annotations

import logging

from esp2dag.compiler.ast.nodes import (
    ApplicationNode,
    CommandNode,
    ConditionNode,
    DependencyNode,
    EventReferenceNode,
    JobNode,
    MetadataNode,
    NotificationNode,
    ResourceNode,
    ResourceRefNode,
    RetryNode,
    ScheduleNode,
    UnsupportedStatementNode,
    VariableNode,
)
from esp2dag.compiler.lexer.token import Token
from esp2dag.compiler.lexer.token_types import TokenType
from esp2dag.compiler.parser.errors import ParseError, ParseResult
from esp2dag.compiler.parser.token_stream import TokenStream
from esp2dag.models.diagnostics import Diagnostic, DiagnosticCode, Severity
from esp2dag.models.source import SourceApplication, SourceSpan

logger = logging.getLogger(__name__)

STAGE = "parser"

# Mid-header modifiers on ``JOB name TASK …`` — not a new workload object.
_HEADER_JOB_TYPE_MODIFIERS = frozenset({"TASK"})

# Free-form job attributes (SAP / DSTRIG / APPLEND / …). Used as statement
# boundaries because newlines are not emitted by the default lexer.
_JOB_ATTR_KEYWORDS = frozenset(
    {
        "ABAPNAME",
        "ARCMODE",
        "BANNER",
        "COLUMNS",
        "CREATE",
        "DOCMEM",
        "DSNAME",
        "ESPNOMSG",
        "EXPIRATION",
        "FILENAME",
        "LANGUAGE",
        "LINES",
        "NOTEXIST",
        "PRINTCOPIES",
        "PRINTDEST",
        "PRINTFORMAT",
        "PRINTIMMED",
        "PRINTNEWSPOOL",
        "PRINTREL",
        "PRINTSPOOLNAME",
        "RECIPIENT",
        "RELDELAY",
        "SAPJOBCLASS",
        "SAPJOBNAME",
        "STARTMODE",
        "STEPUSER",
        "VARIANT",
    }
)

_APP_SYNC = (
    TokenType.JOB,
    TokenType.JOB_TYPE,
    TokenType.DATA_OBJECT,
    TokenType.NOTIFY,
    TokenType.AMNOTIFY,
    TokenType.TAG,
    TokenType.INVOKE,
    TokenType.SETVAR,
    TokenType.RESOURCE,
    TokenType.IF,
    TokenType.OPTIONS,
    TokenType.ENDAPPL,
    TokenType.EOF,
)

_JOB_BODY_KEYWORDS = (
    TokenType.RUN,
    TokenType.RELEASE,
    TokenType.RESOURCE,
    TokenType.COMMAND,
    TokenType.CMDNAME,
    TokenType.SCRIPTNAME,
    TokenType.AGENT,
    TokenType.USER,
    TokenType.ARGS,
    TokenType.JOBQ,
    TokenType.NOTIFY,
    TokenType.AMNOTIFY,
    TokenType.IF,
    TokenType.SETVAR,
    TokenType.NOTWITH,
    TokenType.DELAYSUB,
    TokenType.EARLYSUB,
    TokenType.RETRY,
    TokenType.CCCHK,
    TokenType.DUEOUT,
)

_JOB_SYNC = (
    TokenType.ENDJOB,
    TokenType.JOB,
    TokenType.JOB_TYPE,
    TokenType.DATA_OBJECT,
    TokenType.EOF,
    *_JOB_BODY_KEYWORDS,
)


class EspParser:
    """Recursive descent parser for one ESP application token stream."""

    def parse(
        self,
        tokens: list[Token],
        application: SourceApplication,
    ) -> ApplicationNode:
        """Parse tokens into an application AST (protocol entrypoint)."""
        return self.parse_with_diagnostics(tokens, application).ast

    def parse_with_diagnostics(
        self,
        tokens: list[Token],
        application: SourceApplication,
    ) -> ParseResult:
        """Parse and return AST plus structured diagnostics."""
        logger.info(
            "Parsing application %s (%s:%s-%s)",
            application.name,
            application.source_file,
            application.start_line,
            application.end_line,
        )
        stream = TokenStream(tokens)
        diagnostics: list[Diagnostic] = []
        ast = self._parse_application(stream, application, diagnostics)
        logger.info(
            "Parsed %s: %d job(s), %d diagnostic(s)",
            ast.name,
            len(ast.jobs),
            len(diagnostics),
        )
        return ParseResult(ast=ast, diagnostics=diagnostics)

    def _parse_application(
        self,
        stream: TokenStream,
        application: SourceApplication,
        diagnostics: list[Diagnostic],
    ) -> ApplicationNode:
        return self._parse_application_body(
            stream,
            application,
            application.name,
            diagnostics,
        )

    def _parse_application_body(
        self,
        stream: TokenStream,
        application: SourceApplication,
        name: str,
        diagnostics: list[Diagnostic],
    ) -> ApplicationNode:
        # If header was partially consumed, continue from current position.
        # Full header parse when still at APPL:
        metadata: list[MetadataNode] = []
        if stream.check(TokenType.APPL, TokenType.APPLICATION):
            appl_tok = stream.advance()
            name_tok = stream.match(TokenType.IDENTIFIER)
            if name_tok is not None:
                name = name_tok.value
            # Only consume APPL options on the same source line (e.g. WAIT).
            while (
                not stream.at_end()
                and stream.current.line == appl_tok.line
                and not stream.check(*_APP_SYNC)
            ):
                opt = stream.advance()
                metadata.append(
                    MetadataNode(span=_span(opt), key="appl_option", value=opt.value)
                )

        jobs: list[JobNode] = []
        notifications: list[NotificationNode] = []
        variables: list[VariableNode] = []
        resources: list[ResourceNode] = []
        unsupported: list[UnsupportedStatementNode] = []

        while not stream.at_end() and not stream.check(TokenType.ENDAPPL):
            try:
                self._parse_app_statement(
                    stream,
                    name,
                    jobs,
                    notifications,
                    variables,
                    resources,
                    metadata,
                    unsupported,
                    diagnostics,
                )
            except ParseError as exc:
                diagnostics.append(
                    _error(
                        DiagnosticCode.E_PARSE_UNEXPECTED_TOKEN,
                        exc.message,
                        _span(exc.token) if exc.token else _span(stream.current),
                        application=name,
                    )
                )
                stream.consume_until(*_APP_SYNC)

        stream.match(TokenType.ENDAPPL)
        return ApplicationNode(
            span=SourceSpan(
                file=application.source_file,
                start_line=application.start_line,
                start_column=1,
                end_line=application.end_line,
                end_column=1,
                text=application.header_line,
            ),
            name=name,
            jobs=jobs,
            resources=resources,
            variables=variables,
            notifications=notifications,
            metadata=metadata,
            raw_header=application.header_line,
            unsupported=unsupported,
        )

    def _parse_app_statement(
        self,
        stream: TokenStream,
        appl_name: str,
        jobs: list[JobNode],
        notifications: list[NotificationNode],
        variables: list[VariableNode],
        resources: list[ResourceNode],
        metadata: list[MetadataNode],
        unsupported: list[UnsupportedStatementNode],
        diagnostics: list[Diagnostic],
    ) -> None:
        if stream.check(TokenType.JOB, TokenType.JOB_TYPE, TokenType.DATA_OBJECT):
            jobs.append(self._parse_job(stream, diagnostics))
            return
        if stream.check(TokenType.NOTIFY, TokenType.AMNOTIFY):
            notifications.append(self._parse_notification(stream))
            return
        if stream.check(TokenType.TAG):
            metadata.append(self._parse_tag(stream))
            return
        if stream.check(TokenType.INVOKE):
            metadata.append(self._parse_invoke(stream))
            return
        if stream.check(TokenType.SETVAR):
            variables.append(self._parse_setvar(stream, scope="appl"))
            return
        if stream.check(TokenType.RESOURCE):
            resources.append(self._parse_app_resource(stream))
            return
        if stream.check(TokenType.OPTIONS):
            metadata.append(self._parse_rest_meta(stream, "options"))
            return
        parked = self._park_statement(
            stream,
            reason="Unrecognized or unsupported application-level statement",
            sync=_APP_SYNC,
        )
        unsupported.append(parked)
        diagnostics.append(
            _warn(
                DiagnosticCode.W_PARSE_UNSUPPORTED,
                f"Unsupported statement '{parked.keyword}' parked.",
                parked.span,
                application=appl_name,
            )
        )

    def _parse_job(self, stream: TokenStream, diagnostics: list[Diagnostic]) -> JobNode:
        start = stream.current
        job_type: str | None = None
        if stream.match(TokenType.DATA_OBJECT):
            job_type = "DATA_OBJECT"
        elif stream.check(TokenType.JOB_TYPE):
            job_type = stream.advance().value
        else:
            stream.expect(TokenType.JOB)

        name_tok = stream.expect(TokenType.IDENTIFIER, message="Expected job name")
        name = name_tok.value
        metadata: list[MetadataNode] = []
        event_refs: list[EventReferenceNode] = []
        self._parse_job_header(stream, metadata, event_refs)

        dependencies: list[DependencyNode] = []
        conditions: list[ConditionNode] = []
        resources: list[ResourceRefNode] = []
        notifications: list[NotificationNode] = []
        variables: list[VariableNode] = []
        unsupported: list[UnsupportedStatementNode] = []
        command: CommandNode | None = None
        schedule: ScheduleNode | None = None
        retry: RetryNode | None = None
        end_line = name_tok.line

        while not stream.at_end() and not stream.check(TokenType.ENDJOB):
            if stream.check(TokenType.JOB, TokenType.JOB_TYPE, TokenType.DATA_OBJECT):
                diagnostics.append(
                    _error(
                        DiagnosticCode.E_PARSE_MISSING_TOKEN,
                        f"Missing ENDJOB before next job while parsing '{name}'.",
                        _span(stream.current),
                        job=name,
                    )
                )
                break
            try:
                (
                    command,
                    schedule,
                    retry,
                    end_line,
                ) = self._parse_job_body_statement(
                    stream,
                    name,
                    dependencies,
                    conditions,
                    resources,
                    notifications,
                    variables,
                    metadata,
                    unsupported,
                    diagnostics,
                    command,
                    schedule,
                    retry,
                    end_line,
                )
            except ParseError as exc:
                diagnostics.append(
                    _error(
                        DiagnosticCode.E_PARSE_UNEXPECTED_TOKEN,
                        exc.message,
                        _span(exc.token) if exc.token else _span(stream.current),
                        job=name,
                    )
                )
                stream.consume_until(*_JOB_SYNC)

        end_tok = stream.match(TokenType.ENDJOB)
        if end_tok is None:
            diagnostics.append(
                _error(
                    DiagnosticCode.E_PARSE_MISSING_TOKEN,
                    f"Expected ENDJOB for job '{name}'.",
                    _span(stream.current),
                    job=name,
                )
            )
        else:
            end_line = end_tok.line

        return JobNode(
            span=SourceSpan(
                file=start.source_file,
                start_line=start.line,
                start_column=start.column,
                end_line=end_line,
                end_column=1,
                text=f"{job_type or 'JOB'} {name}",
            ),
            name=name,
            job_type=job_type,
            command=command,
            dependencies=dependencies,
            conditions=conditions,
            resources=resources,
            retry=retry,
            notifications=notifications,
            event_refs=event_refs,
            schedule=schedule,
            variables=variables,
            metadata=metadata,
            unsupported=unsupported,
        )

    def _parse_job_header(
        self,
        stream: TokenStream,
        metadata: list[MetadataNode],
        event_refs: list[EventReferenceNode],
    ) -> None:
        while not stream.at_end():
            if stream.check(TokenType.ENDJOB, *_JOB_BODY_KEYWORDS):
                return
            if stream.check(TokenType.JOB, TokenType.DATA_OBJECT):
                return
            if stream.check(TokenType.JOB_TYPE):
                # Header modifiers like TASK stay on this job; other JOB_TYPEs
                # (AS400_JOB, APPLEND, …) mean the previous job lacked ENDJOB.
                upper = stream.current.value.upper()
                if upper in _HEADER_JOB_TYPE_MODIFIERS:
                    tok = stream.advance()
                    metadata.append(
                        MetadataNode(span=_span(tok), key=upper.lower(), value=upper)
                    )
                    continue
                return
            if stream.check(TokenType.LINK):
                link = stream.advance()
                metadata.append(MetadataNode(span=_span(link), key="link", value="LINK"))
                proc = stream.match(TokenType.PROCESS)
                if proc is not None:
                    metadata.append(
                        MetadataNode(span=_span(proc), key="process", value="PROCESS")
                    )
                continue
            if stream.check(TokenType.EXTERNAL):
                ext = stream.advance()
                metadata.append(
                    MetadataNode(span=_span(ext), key="external", value="EXTERNAL")
                )
                continue
            if stream.check(TokenType.APPLID):
                stream.advance()
                event_refs.append(self._parse_applid(stream))
                continue
            if stream.check(TokenType.IDENTIFIER) and stream.check_value("CONDITIONAL"):
                tok = stream.advance()
                metadata.append(
                    MetadataNode(span=_span(tok), key="conditional", value=tok.value)
                )
                continue
            if (
                stream.check(TokenType.IDENTIFIER)
                and stream.current.value.upper() in _JOB_ATTR_KEYWORDS
            ):
                # Body attributes (DSNAME, ABAPNAME, …) — leave for job body parser.
                return
            if stream.check(TokenType.IDENTIFIER) and stream.peek(1).type == TokenType.LPAREN:
                # e.g. DOCMEM(VERFILES) on TASK jobs
                meta = self._parse_rest_meta(stream, stream.current.value.lower())
                metadata.append(meta)
                continue
            if stream.check(*_APP_SYNC) and not stream.check(*_JOB_BODY_KEYWORDS):
                return
            tok = stream.advance()
            metadata.append(MetadataNode(span=_span(tok), key="header_attr", value=tok.value))

    def _parse_job_body_statement(
        self,
        stream: TokenStream,
        name: str,
        dependencies: list[DependencyNode],
        conditions: list[ConditionNode],
        resources: list[ResourceRefNode],
        notifications: list[NotificationNode],
        variables: list[VariableNode],
        metadata: list[MetadataNode],
        unsupported: list[UnsupportedStatementNode],
        diagnostics: list[Diagnostic],
        command: CommandNode | None,
        schedule: ScheduleNode | None,
        retry: RetryNode | None,
        end_line: int,
    ) -> tuple[CommandNode | None, ScheduleNode | None, RetryNode | None, int]:
        if stream.check(TokenType.RUN):
            schedule = self._parse_run(stream)
            return command, schedule, retry, schedule.span.end_line
        if stream.check(TokenType.RELEASE):
            dep = self._parse_release(stream)
            dependencies.append(dep)
            return command, schedule, retry, dep.span.end_line
        if stream.check(TokenType.RESOURCE):
            ref = self._parse_resource_ref(stream)
            resources.append(ref)
            return command, schedule, retry, ref.span.end_line
        if stream.check(TokenType.COMMAND, TokenType.CMDNAME, TokenType.SCRIPTNAME):
            command = self._parse_command(stream, existing=command)
            return command, schedule, retry, command.span.end_line
        if stream.check(TokenType.AGENT):
            meta = self._parse_simple_meta(stream, "agent")
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.USER):
            meta = self._parse_simple_meta(stream, "user")
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.JOBQ):
            meta = self._parse_simple_meta(stream, "jobq")
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.ARGS):
            meta = self._parse_args(stream)
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.NOTIFY, TokenType.AMNOTIFY):
            note = self._parse_notification(stream)
            notifications.append(note)
            return command, schedule, retry, note.span.end_line
        if stream.check(TokenType.IF):
            cond = self._parse_if(stream)
            conditions.append(cond)
            return command, schedule, retry, cond.span.end_line
        if stream.check(TokenType.SETVAR):
            var = self._parse_setvar(stream, scope="job")
            variables.append(var)
            return command, schedule, retry, var.span.end_line
        if stream.check(TokenType.NOTWITH):
            meta = self._parse_simple_meta(stream, "notwith")
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.DELAYSUB, TokenType.EARLYSUB):
            meta = self._parse_rest_meta(stream, stream.current.value.lower())
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.RETRY):
            retry = self._parse_retry(stream)
            return command, schedule, retry, retry.span.end_line
        if stream.check(TokenType.CCCHK):
            meta = self._parse_rest_meta(stream, "ccchk")
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.DUEOUT):
            meta = self._parse_rest_meta(stream, "dueout")
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line
        if stream.check(TokenType.IDENTIFIER) and stream.peek(1).type == TokenType.EQUALS:
            var = self._parse_assignment(stream, scope="job")
            variables.append(var)
            return command, schedule, retry, var.span.end_line
        # Capture free-form attributes (SAP ABAPNAME/VARIANT, DSNAME, RELDELAY, …)
        # instead of parking them as unsupported — needed for operator field mapping.
        if stream.check(TokenType.IDENTIFIER):
            meta = self._parse_rest_meta(stream, stream.current.value.lower())
            metadata.append(meta)
            return command, schedule, retry, meta.span.end_line

        parked = self._park_statement(
            stream,
            reason="Unrecognized job-level statement",
            sync=_JOB_SYNC,
        )
        unsupported.append(parked)
        diagnostics.append(
            _warn(
                DiagnosticCode.W_PARSE_UNSUPPORTED,
                f"Unsupported job statement '{parked.keyword}' in '{name}'.",
                parked.span,
                job=name,
            )
        )
        return command, schedule, retry, parked.span.end_line

    def _parse_applid(self, stream: TokenStream) -> EventReferenceNode:
        start = stream.current
        stream.expect(TokenType.LPAREN)
        name_tok = stream.expect(TokenType.IDENTIFIER, TokenType.STRING)
        stream.expect(TokenType.RPAREN)
        return EventReferenceNode(
            span=_span(start, name_tok),
            event_name=name_tok.value,
            event_kind="APPLID",
        )

    def _parse_run(self, stream: TokenStream) -> ScheduleNode:
        start = stream.advance()  # RUN
        parts = self._collect_until_boundary(stream)
        expression = " ".join(parts) if parts else "DAILY"
        end = stream.peek(-1) if parts else start
        return ScheduleNode(span=_span(start, end), expression=expression)

    def _parse_release(self, stream: TokenStream) -> DependencyNode:
        start = stream.advance()  # RELEASE
        stream.match(TokenType.ADD)
        target = self._parse_paren_or_name(stream)
        return DependencyNode(
            span=_span(start),
            predecessor=target,
            dependency_type="RELEASE",
        )

    def _parse_resource_ref(self, stream: TokenStream) -> ResourceRefNode:
        start = stream.advance()  # RESOURCE
        stream.match(TokenType.ADD)
        quantity: int | None = None
        name = "UNKNOWN"
        if stream.match(TokenType.LPAREN):
            if stream.check(TokenType.NUMBER):
                quantity = int(stream.advance().value)
                stream.match(TokenType.COMMA)
            if stream.check(TokenType.IDENTIFIER, TokenType.STRING):
                name = stream.advance().value
            stream.match(TokenType.RPAREN)
        elif stream.check(TokenType.IDENTIFIER):
            name = stream.advance().value
        return ResourceRefNode(span=_span(start), name=name, quantity=quantity)

    def _parse_app_resource(self, stream: TokenStream) -> ResourceNode:
        ref = self._parse_resource_ref(stream)
        return ResourceNode(
            span=ref.span,
            name=ref.name,
            quantity=ref.quantity,
            attributes=ref.attributes,
        )

    def _parse_command(
        self,
        stream: TokenStream,
        *,
        existing: CommandNode | None,
    ) -> CommandNode:
        start = stream.advance()  # COMMAND / CMDNAME / SCRIPTNAME
        kind = start.value.upper()
        parts = self._collect_until_boundary(stream)
        text = " ".join(parts)
        if existing is not None and existing.text:
            text = f"{existing.text} | {text}"
        return CommandNode(
            span=_span(start),
            text=text,
            interpreter=kind,
            attributes={"kind": kind},
        )

    def _parse_notification(self, stream: TokenStream) -> NotificationNode:
        start = stream.advance()  # NOTIFY / AMNOTIFY
        parts = self._collect_until_boundary(stream)
        on_event = parts[0] if parts else None
        channel = None
        recipients: list[str] = []
        joined = " ".join(parts)
        for part in parts:
            upper = part.upper()
            if upper in {"ALERT", "MAILBOX"}:
                channel = upper
            elif channel and not recipients:
                recipients.append(part.strip("()"))
        # Prefer parenthesized recipient if present in joined text.
        if "(" in joined and ")" in joined:
            inner = joined[joined.find("(") + 1 : joined.rfind(")")]
            if inner:
                recipients = [inner]
        return NotificationNode(
            span=_span(start),
            channel=channel or start.value.upper(),
            recipients=recipients,
            on_event=on_event,
            message=joined,
        )

    def _parse_tag(self, stream: TokenStream) -> MetadataNode:
        start = stream.advance()
        value = stream.advance().value if stream.check(TokenType.IDENTIFIER) else ""
        return MetadataNode(span=_span(start), key="tag", value=value)

    def _parse_invoke(self, stream: TokenStream) -> MetadataNode:
        start = stream.advance()
        value = ""
        if stream.check(TokenType.STRING, TokenType.IDENTIFIER):
            value = stream.advance().value
        return MetadataNode(span=_span(start), key="invoke", value=value)

    def _parse_setvar(self, stream: TokenStream, *, scope: str) -> VariableNode:
        start = stream.advance()
        name_tok = stream.expect(TokenType.IDENTIFIER, message="Expected variable name")
        stream.match(TokenType.EQUALS)
        value = ""
        if stream.check(TokenType.STRING, TokenType.IDENTIFIER, TokenType.NUMBER):
            value = stream.advance().value
        return VariableNode(span=_span(start, name_tok), name=name_tok.value, value=value, scope=scope)

    def _parse_assignment(self, stream: TokenStream, *, scope: str) -> VariableNode:
        name_tok = stream.advance()
        stream.expect(TokenType.EQUALS)
        parts = self._collect_until_boundary(stream)
        return VariableNode(
            span=_span(name_tok),
            name=name_tok.value,
            value=" ".join(parts),
            scope=scope,
        )

    def _parse_if(self, stream: TokenStream) -> ConditionNode:
        start = stream.advance()
        parts = self._collect_until_boundary(stream)
        return ConditionNode(
            span=_span(start),
            expression=" ".join(parts),
            kind="IF",
        )

    def _parse_retry(self, stream: TokenStream) -> RetryNode:
        start = stream.advance()
        parts = self._collect_until_boundary(stream)
        max_attempts = None
        if parts and parts[0].isdigit():
            max_attempts = int(parts[0])
        return RetryNode(
            span=_span(start),
            max_attempts=max_attempts,
            interval=parts[1] if len(parts) > 1 else None,
            attributes={"raw": " ".join(parts)},
        )

    def _parse_simple_meta(self, stream: TokenStream, key: str) -> MetadataNode:
        start = stream.advance()
        value = ""
        if not stream.check(*_JOB_BODY_KEYWORDS, TokenType.ENDJOB, *_APP_SYNC):
            if not stream.at_end():
                value = stream.advance().value
        return MetadataNode(span=_span(start), key=key, value=value)

    def _parse_args(self, stream: TokenStream) -> MetadataNode:
        start = stream.advance()
        parts = self._collect_until_boundary(stream)
        return MetadataNode(span=_span(start), key="args", value=" ".join(parts))

    def _parse_rest_meta(self, stream: TokenStream, key: str) -> MetadataNode:
        start = stream.advance()
        parts = self._collect_until_boundary(stream)
        return MetadataNode(span=_span(start), key=key, value=" ".join(parts))

    def _parse_paren_or_name(self, stream: TokenStream) -> str:
        if stream.match(TokenType.LPAREN):
            parts: list[str] = []
            depth = 1
            while not stream.at_end() and depth > 0:
                tok = stream.advance()
                if tok.type == TokenType.LPAREN:
                    depth += 1
                    parts.append(tok.value)
                elif tok.type == TokenType.RPAREN:
                    depth -= 1
                    if depth > 0:
                        parts.append(tok.value)
                else:
                    parts.append(tok.value)
            return "".join(parts)
        if stream.check(TokenType.IDENTIFIER, TokenType.STRING):
            return stream.advance().value
        raise ParseError("Expected job name or (name) after RELEASE", stream.current)

    def _collect_until_boundary(self, stream: TokenStream) -> list[str]:
        """Collect token values until the next statement boundary."""
        parts: list[str] = []
        while not stream.at_end():
            if stream.check(TokenType.ENDJOB, *_JOB_BODY_KEYWORDS):
                break
            if stream.check(TokenType.JOB, TokenType.JOB_TYPE, TokenType.DATA_OBJECT):
                break
            if stream.check(
                TokenType.NOTIFY,
                TokenType.AMNOTIFY,
                TokenType.TAG,
                TokenType.INVOKE,
                TokenType.OPTIONS,
                TokenType.ENDAPPL,
            ):
                # Only break on app-level if we are not mid-expression with EQUALS etc.
                # For job body, NOTIFY is a body keyword already listed.
                break
            if (
                stream.check(TokenType.IDENTIFIER)
                and stream.current.value.upper() in _JOB_ATTR_KEYWORDS
            ):
                break
            # Keep parenthesized tails with the statement.
            if stream.check(TokenType.LPAREN):
                parts.append(self._consume_balanced(stream))
                continue
            tok = stream.advance()
            parts.append(tok.value)
            # Stop after a completed ALERT(x)/MAILBOX(x)-style already handled via LPAREN.
        return parts

    def _consume_balanced(self, stream: TokenStream) -> str:
        stream.expect(TokenType.LPAREN)
        parts = ["("]
        depth = 1
        while not stream.at_end() and depth > 0:
            tok = stream.advance()
            parts.append(tok.value)
            if tok.type == TokenType.LPAREN:
                depth += 1
            elif tok.type == TokenType.RPAREN:
                depth -= 1
        return "".join(parts)

    def _park_statement(
        self,
        stream: TokenStream,
        *,
        reason: str,
        sync: tuple[TokenType, ...],
    ) -> UnsupportedStatementNode:
        start = stream.current
        keyword = start.value
        raw_parts = [stream.advance().value]
        while not stream.at_end() and not stream.check(*sync):
            raw_parts.append(stream.advance().value)
        raw = " ".join(raw_parts)
        return UnsupportedStatementNode(
            span=_span(start),
            keyword=keyword,
            raw=raw,
            reason=reason,
        )


def _span(start: Token, end: Token | None = None) -> SourceSpan:
    end = end or start
    return SourceSpan(
        file=start.source_file,
        start_line=start.line,
        start_column=start.column,
        end_line=end.line,
        end_column=end.column,
        text=start.value if end is start else None,
    )


def _warn(
    code: str,
    message: str,
    span: SourceSpan,
    *,
    application: str | None = None,
    job: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.WARNING,
        message=message,
        stage=STAGE,
        span=span,
        application=application,
        job=job,
    )


def _error(
    code: str,
    message: str,
    span: SourceSpan,
    *,
    application: str | None = None,
    job: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        stage=STAGE,
        span=span,
        application=application,
        job=job,
    )
