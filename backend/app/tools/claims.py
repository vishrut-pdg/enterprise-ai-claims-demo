from pydantic import BaseModel, Field

from app.telemetry import span


class ClaimInput(BaseModel):
    claim_id: str = Field(min_length=1)


class ToolResult(BaseModel):
    name: str
    data: dict | list


class ClaimTools:
    """Agent-facing surface: application service only, no persistence/session access."""

    def __init__(self, service, run_id, autonomous=False):
        self._service, self.run_id, self.trajectory = service, run_id, []
        self.autonomous = autonomous

    def call(self, name: str, request: ClaimInput) -> ToolResult:
        if name not in (
            "get_claim",
            "get_policy",
            "get_evidence",
            "calculate_policy_checks",
            "get_previous_outcomes",
        ):
            raise ValueError("Unknown retrieval tool")
        with span("tool." + name, self.run_id):
            data = (
                self._service.get_previous_outcomes(
                    request.claim_id, autonomous=self.autonomous
                )
                if name == "get_previous_outcomes"
                else getattr(self._service, name)(request.claim_id)
            )
            self.trajectory.append(name)
            return ToolResult(name=name, data=data)

    async def retrieve_policy(self, context, settings):
        return await self._service.retrieve_policy(context, settings)

    def record_context(self, claim_id, version, context):
        self._service.record_context(claim_id, version, context, self.run_id)

    def record_investigation(self, claim_id, version, context):
        self._service.record_investigation(claim_id, version, context, self.run_id)

    def execute(self, claim_id, version, assessment, response, duration, context):
        # The service selects/revalidates the action; model text cannot choose arbitrary calls.
        with span("tool.controlled_execution", self.run_id):
            return self._service.finish(
                claim_id,
                version,
                assessment,
                response,
                self.run_id,
                duration,
                self.trajectory,
                context,
                autonomous=self.autonomous,
            )
