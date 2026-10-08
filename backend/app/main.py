from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.assessment.service import DomainError
from app.config import get_settings
from app.telemetry import configure, correlation_id, span

settings = get_settings()
configure(settings)
app = FastAPI(title="Enterprise AI Claims", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Role", "X-Actor", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)
app.include_router(router)
FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message})


@app.middleware("http")
async def correlate(request: Request, call_next):
    raw = request.headers.get("X-Correlation-ID", "")
    try:
        run_id = str(__import__("uuid").UUID(raw))
    except ValueError:
        run_id = str(uuid4())
    token = correlation_id.set(run_id)
    try:
        with span("http.request", run_id):
            response = await call_next(request)
        response.headers["X-Correlation-ID"] = run_id
        return response
    finally:
        correlation_id.reset(token)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    # No driver details, SQL parameters or connection credentials in the response.
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable; no new decision could be confirmed. Refresh before retrying."
        },
    )
