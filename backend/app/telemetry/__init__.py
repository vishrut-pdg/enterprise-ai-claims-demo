import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

correlation_id = ContextVar("correlation_id", default="")
log = structlog.get_logger()


def configure(settings):
    logging.basicConfig(level=settings.log_level)
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )
    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint.rstrip("/")
                    + "/v1/traces"
                )
            )
        )
    trace.set_tracer_provider(provider)


@contextmanager
def span(name, run_id=""):
    with trace.get_tracer("claims").start_as_current_span(name) as current:
        current.set_attribute("claims.correlation_id", run_id or correlation_id.get())
        yield current


def instrument_database(engine):
    """Trace SQL execution without logging statements, parameters or connection URLs."""
    from sqlalchemy import event

    def before_execute(conn, cursor, statement, parameters, context, executemany):
        active = trace.get_tracer("claims").start_span("database.execute")
        active.set_attribute("claims.correlation_id", correlation_id.get())
        conn.info["_claims_db_span"] = active

    def finish(conn):
        active = conn.info.pop("_claims_db_span", None)
        if active:
            active.end()

    def after_execute(conn, cursor, statement, parameters, context, executemany):
        finish(conn)

    def failed(context):
        if context.connection is not None:
            finish(context.connection)

    event.listen(engine, "before_cursor_execute", before_execute)
    event.listen(engine, "after_cursor_execute", after_execute)
    event.listen(engine, "handle_error", failed)


@contextmanager
def correlated(run_id):
    token = correlation_id.set(run_id)
    try:
        yield
    finally:
        correlation_id.reset(token)
