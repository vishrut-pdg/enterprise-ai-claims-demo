from time import perf_counter
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agents.claim_agent import ClaimAgent
from app.ai.factory import create_provider
from app.ai.gateway import LLMGateway
from app.assessment.service import DomainError
from app.telemetry import correlated, span
from app.tools.claims import ClaimTools


async def process_claim(
    service, claim_id, expected_version, settings, run_id=None, provider=None
):
    run_id = run_id or str(uuid4())
    with correlated(run_id):
        return await _process_claim(
            service, claim_id, expected_version, settings, run_id, provider
        )


async def _process_claim(
    service, claim_id, expected_version, settings, run_id, provider
):
    autonomous = settings.decision_mode == "autonomous"
    service.prepare(claim_id, expected_version, run_id, autonomous=autonomous)
    tools = ClaimTools(service, run_id, autonomous=autonomous)
    gateway = LLMGateway(provider or create_provider(settings), settings)
    agent = ClaimAgent(tools, gateway)
    sessions = InMemorySessionService()
    session = await sessions.create_session(
        app_name="claims",
        user_id="analyst",
        session_id=run_id,
        state={"claim_id": claim_id, "expected_version": expected_version},
    )
    runner = Runner(agent=agent, app_name="claims", session_service=sessions)
    started = perf_counter()
    try:
        with span("workflow.process_claim", run_id):
            async for _ in runner.run_async(
                user_id="analyst", session_id=session.id, new_message=None
            ):
                pass
        saved = await sessions.get_session(
            app_name="claims", user_id="analyst", session_id=session.id
        )
        return saved.state["result"]
    except Exception as exc:
        service.failure(
            claim_id,
            run_id,
            settings,
            int((perf_counter() - started) * 1000),
            exc,
            tools.trajectory,
        )
        if isinstance(exc, DomainError):
            raise
        raise DomainError(
            "Assessment failed safely; no decision was made. Check processing history.",
            502,
        ) from exc
