from time import perf_counter

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import PrivateAttr

from app.telemetry import span
from app.tools.claims import ClaimInput


class ClaimAgent(BaseAgent):
    """Bounded ADK agent: retrieves facts through tools, then invokes our gateway.

    A fixed trajectory teaches controls without handing action authority to a model.
    ADK owns session/events; the provider-neutral gateway owns model inference.
    """

    _tools: object = PrivateAttr()
    _gateway: object = PrivateAttr()

    def __init__(self, tools, gateway):
        super().__init__(
            name="claim_processor",
            description="Ground, assess, then execute with application controls",
        )
        self._tools, self._gateway = tools, gateway

    async def _run_async_impl(self, ctx):
        claim_id, version = (
            ctx.session.state["claim_id"],
            ctx.session.state["expected_version"],
        )
        request = ClaimInput(claim_id=claim_id)
        context = {}
        with span("agent.claim_processor", self._tools.run_id):
            for name, key in [
                ("get_claim", "claim"),
                ("get_policy", "policy"),
                ("get_evidence", "evidence"),
                ("calculate_policy_checks", "checks"),
                ("get_previous_outcomes", "previous_outcomes"),
            ]:
                result = self._tools.call(name, request)
                context[key] = result.data
                yield Event(
                    author=self.name,
                    custom_metadata={"tool": name, "claim_id": claim_id},
                )
            if self._gateway.settings.rag_enabled:
                context["policy_passages"] = await self._tools.retrieve_policy(
                    context, self._gateway.settings
                )
                self._tools.trajectory.append("retrieve_policy_passages")
            self._tools.record_context(claim_id, version, context)
            started = perf_counter()
            if self._tools.autonomous:
                investigation, investigation_response = await self._gateway.investigate(
                    context, self._tools.run_id
                )
                context["investigation"] = investigation.model_dump()
                context["investigation_usage"] = investigation_response.usage
                self._tools.trajectory.append("investigate_claim")
                self._tools.record_investigation(claim_id, version, context)
                yield Event(
                    author=self.name,
                    custom_metadata={"tool": "investigate_claim", "claim_id": claim_id},
                )
            assessment, response = await self._gateway.assess(
                context, self._tools.run_id
            )
            self._tools.trajectory.append("assess")
            result = self._tools.execute(
                claim_id,
                version,
                assessment,
                response,
                int((perf_counter() - started) * 1000),
                context,
            )
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"result": result}),
                custom_metadata={"recommendation": assessment.recommendation},
            )
