# Enterprise AI Claims Reference Application — Architecture

**Status:** Frozen baseline  
**Goal:** Local-first, provider-neutral, deployable to local, SAP BTP, and GCP without changing core application logic.

---

## 1. Architecture principles

The system must follow these rules:

1. Frontend and backend remain separate.
2. Deterministic business logic stays separate from LLM reasoning.
3. Agents do not access the database directly.
4. Agents interact with application capabilities through tools.
5. LLM providers sit behind one internal gateway.
6. Business logic must not know whether it runs on local, BTP, or GCP.
7. Important business and AI state must be persisted.
8. AI output must be validated before affecting business state.
9. Human review must remain an explicit control path.
10. Local development is the primary reference environment.

---

## 2. High-level architecture

```text
                 React + TypeScript + Vite
                           |
                           v
                        FastAPI
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
 Application Services   Workflows          Agents
        |                  |                  |
        |                  |             Google ADK
        |                  |                  |
        +------------------+------------------+
                           |
                           v
                         Tools
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
 Deterministic Services                LLM Gateway
          |                                 |
          |                     +-----------+-----------+
          |                     |           |           |
          |                     v           v           v
          |                   Ollama     Vertex AI    BTP AI
          |
          +-----------------------+
                                  |
                                  v
                              PostgreSQL

                   Background processing
                           |
                           v
                      Redis + ARQ
```

---

## 3. Repository structure

```text
enterprise-ai-claims/
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── claims/
│   │   │   ├── assessments/
│   │   │   └── reviews/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── types/
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── domain/
│   │   ├── schemas/
│   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── session.py
│   │   ├── assessment/
│   │   ├── ai/
│   │   │   ├── gateway.py
│   │   │   ├── factory.py
│   │   │   ├── models.py
│   │   │   └── providers/
│   │   │       ├── base.py
│   │   │       ├── mock.py
│   │   │       ├── ollama.py
│   │   │       ├── vertex.py
│   │   │       └── btp_ai.py
│   │   ├── prompts/
│   │   ├── agents/
│   │   ├── tools/
│   │   ├── workflows/
│   │   ├── orchestration/
│   │   ├── jobs/
│   │   ├── memory/
│   │   ├── evaluation/
│   │   ├── governance/
│   │   ├── telemetry/
│   │   ├── config.py
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
│
├── seed/
│
├── config/
│
├── deploy/
│   ├── local/
│   ├── btp/
│   └── gcp/
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── IMPLEMENTATION_PLAN.md
│
├── Dockerfile
├── deployment.yaml
├── .env.example
└── README.md
```

---

## 4. Frontend architecture

### Stack

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack Query
- TanStack Table

### Responsibilities

Frontend handles:

- Claim Queue
- Claim Detail
- Assessment
- Manager Review Queue
- Manager Review Detail
- Audit / Processing History
- loading and error states
- mutations and refresh
- filters and tables

Frontend must not contain decision logic.

Example:

```text
React Page
   |
   v
TanStack Query
   |
   v
FastAPI endpoint
```

---

## 5. Backend architecture

### Stack

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL

Backend layers:

```text
API
 |
 v
Application Service
 |
 +--> Deterministic Logic
 |
 +--> Workflow
 |
 +--> Repository
 |
 +--> Agent / AI capability
```

FastAPI endpoints should remain thin.

Do not place business logic directly inside route functions.

---

## 6. Domain layer

Core entities:

- Employee
- Claim
- ClaimLine
- Policy
- PolicyRule
- Evidence
- PolicyFinding
- ClaimAssessment
- ReviewTask
- ReviewDecision
- AuditEvent
- AIExecution
- OutcomeRecord

The domain layer must not import:

- FastAPI request objects
- Ollama SDK
- Google model SDK
- SAP AI SDK
- Redis
- ARQ

---

## 7. Persistence layer

Use:

```text
Application Service
        |
        v
Repository
        |
        v
SQLAlchemy
        |
        v
PostgreSQL
```

Repositories expose operations such as:

- `get_claim`
- `list_claims`
- `save_assessment`
- `create_review_task`
- `record_review_decision`
- `append_audit_event`
- `find_previous_outcomes`

Agents do not receive SQLAlchemy sessions.

---

## 8. Deterministic assessment

Deterministic checks run before AI interpretation.

Examples:

- expense limit
- receipt required
- category allowed
- duplicate claim
- date validity
- amount calculation

Flow:

```text
Claim
  +
Policy
  +
Evidence
  |
  v
Deterministic checks
  |
  v
Policy findings
  |
  v
AI assessment
```

AI should not be asked to calculate something the application can calculate deterministically.

---

## 9. AI provider abstraction

The application uses a provider-neutral LLM layer.

```text
Agent / Application
        |
        v
    LLM Gateway
        |
   +----+----+----+
   |         |    |
   v         v    v
Ollama    Vertex  BTP AI
```

### Provider contract

Create an internal interface:

```python
class LLMProvider(Protocol):

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        ...

    async def health(self) -> bool:
        ...
```

All provider adapters must return the same internal `LLMResponse`.

Provider-specific SDK objects must not escape the adapter.

---

## 10. Provider selection

Provider selection is configuration-driven.

```text
LLM_PROVIDER=ollama
LLM_PROVIDER=vertex
LLM_PROVIDER=btp
```

Model name is separate:

```text
LLM_MODEL=<model-name>
```

Examples:

```text
Local
LLM_PROVIDER=ollama
```

```text
GCP
LLM_PROVIDER=vertex
```

```text
SAP BTP
LLM_PROVIDER=btp
```

No agent or workflow code should change.

---

## 11. Structured AI output

LLM responses must be converted to Pydantic schemas.

Example:

```python
class ClaimAssessment(BaseModel):
    recommendation: Literal[
        "accept",
        "reject",
        "investigate",
    ]

    confidence: float
    findings: list[str]
    evidence_ids: list[str]
    unresolved_questions: list[str]
    explanation: str
```

Flow:

```text
LLM
 |
 v
Provider adapter
 |
 v
Normalized response
 |
 v
Pydantic validation
 |
 v
Application workflow
```

Invalid output must fail safely.

---

## 12. Agent architecture

Google ADK provides agent orchestration.

An agent consists of:

```text
Model
+
Context
+
Tools
+
Session
+
Workflow
+
Controls
```

Agents must not directly:

- mutate database rows;
- execute arbitrary SQL;
- change claim status;
- bypass application validation.

Instead:

```text
Agent
 |
 v
Tool
 |
 v
Application Service
 |
 v
Repository / controlled action
```

---

## 13. Tools

Example tools:

- `get_claim`
- `get_policy`
- `get_evidence`
- `calculate_policy_checks`
- `get_previous_outcomes`
- `accept_claim`
- `reject_claim`
- `create_review_task`

Tool inputs and outputs must use explicit Pydantic schemas.

Tools should remain narrow.

Example:

```text
create_review_task
```

should create a review task.

It should not also:

- send notifications;
- rewrite claims;
- update policies;
- modify model configuration.

---

## 14. Claim processing workflow

```text
Claim submitted
      |
      v
Load claim
      |
      v
Retrieve policy
      |
      v
Retrieve evidence
      |
      v
Run deterministic checks
      |
      v
Create grounded AI context
      |
      v
AI assessment
      |
 +----+-------------+
 |          |       |
 v          v       v
Accept    Reject  Investigate
 |          |       |
 v          v       v
Revalidate Revalidate Create review
 |          |       |
 v          v       v
Accept     Reject   Manager
                     |
                     v
                  Decision
                     |
                     v
                   Outcome
```

---

## 15. Human control

Autonomy is bounded.

### Accept

Automatic acceptance requires:

- current claim version;
- required evidence;
- successful policy checks;
- valid structured recommendation;
- automatic action allowed by policy.

### Reject

Automatic rejection requires:

- current claim version;
- explicit rejection condition;
- validated recommendation;
- automatic action allowed by policy.

### Investigate

Uncertain cases must create manager review.

Manager can:

- Accept
- Reject
- Request more information

---

## 16. Background processing

Use Redis + ARQ.

Examples:

- batch assessments;
- long-running investigations;
- retries;
- evaluations;
- outcome processing.

Architecture:

```text
FastAPI
  |
  +--> immediate request
  |
  +--> enqueue ARQ job
            |
            v
          Redis
            |
            v
         Worker
```

The application should remain usable for basic synchronous flows when the worker is unavailable where practical.

---

## 17. Enterprise memory

Enterprise memory means stored business outcomes.

Do not implement automatic fine-tuning.

Store:

- claim context;
- findings;
- AI recommendation;
- human decision;
- reviewer rationale;
- evidence references;
- timestamp.

Expose memory through a controlled service/tool.

```text
Previous reviewed outcome
          |
          v
Memory service
          |
          v
Agent tool
          |
          v
Current investigation
```

---

## 18. Evaluation

Evaluation must test workflow behavior.

Examples:

- correct policy selected;
- correct claim version used;
- evidence retrieved;
- correct tools called;
- recommendation supported;
- human boundary respected;
- unsafe action prevented.

Structure:

```text
evaluation/
├── datasets/
├── evaluators/
├── trajectory/
└── regression/
```

Support ADK trajectory evaluation.

---

## 19. Observability

Use:

- structured logging
- OpenTelemetry

Trace:

```text
HTTP request
   |
   v
Workflow
   |
   v
Agent
   |
   v
Model call
   |
   v
Tool call
   |
   v
Service
   |
   v
Database
   |
   v
Decision
```

Carry correlation / trace identifiers through the flow.

Do not log:

- credentials;
- tokens;
- secrets;
- connection passwords.

---

## 20. Local runtime

Local development:

```text
Host machine
│
├── React / Vite        :5173
├── FastAPI             :8000
├── Ollama              :11434
│
└── Docker Compose
    ├── PostgreSQL      :5432
    └── Redis           :6379
```

Ollama runs natively on macOS.

PostgreSQL and Redis run in Docker.

---

## 21. Deployment portability

Core application code must remain unchanged.

```text
                  Application
                      |
              runtime configuration
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
        Local        BTP         GCP
```

### Local

- Docker Compose
- native FastAPI
- native Vite
- Ollama

### SAP BTP

- Cloud Foundry app
- environment/service bindings
- BTP AI adapter

### GCP

- Cloud Run
- environment configuration
- Vertex AI adapter

Platform-specific content belongs only under:

```text
deploy/
├── local/
├── btp/
└── gcp/
```

---

## 22. Configuration

Use environment-driven configuration.

Minimum configuration:

```text
APP_ENV

DATABASE_URL
REDIS_URL

LLM_PROVIDER
LLM_MODEL

OLLAMA_BASE_URL

GCP_PROJECT_ID
GCP_LOCATION

BTP_AI_DEPLOYMENT_ID

LOG_LEVEL
OTEL_SERVICE_NAME
```

Secrets must never be committed.

---

## 23. Testing architecture

### Backend

- pytest
- Hypothesis

Test:

- domain rules;
- assessment logic;
- repositories;
- tools;
- workflows;
- provider contracts;
- Pydantic validation;
- failure paths.

### Frontend

- Vitest
- Testing Library

Test:

- key components;
- loading states;
- claim detail;
- manager review.

### E2E

- Playwright

Minimum E2E path:

```text
Open claim
→ assessment
→ investigate
→ manager review
→ manager accept
→ outcome visible
```

Cloud credentials must not be required to run the normal test suite.

Use mock providers.

---

## 24. Seed data

Create at least three reproducible claims.

### Accept case

Fully compliant claim.

### Reject case

Explicit policy violation.

### Investigate case

Incomplete or contradictory evidence.

These scenarios must be deterministic enough for teaching and tests.

---

## 25. Learning progression

The final application will later be sliced into:

```text
Week 1
Application + Data

Week 2
Application + Data
+ Assessment
+ LLM Gateway

Week 3
+ ADK
+ Tools
+ Execution
+ Manager Review

Week 4
+ Memory
+ Evaluation
+ Observability
+ Autonomous orchestration
```

The Week 4 implementation is built first.

---

## 26. Architecture constraints

Do not:

- put provider code inside business services;
- let agents run SQL directly;
- let free-form LLM output change claim state;
- use AI for deterministic arithmetic;
- hardcode one cloud provider;
- place cloud checks throughout application code;
- duplicate business rules in frontend and backend;
- store secrets in Git;
- make the UI depend on Ollama, Vertex, or BTP-specific response formats.

---

## 27. Target architecture quality

The implementation should optimize for:

- clarity;
- teachability;
- explicit boundaries;
- provider portability;
- testability;
- traceability;
- controlled autonomy;
- reproducible local setup.

Avoid unnecessary framework layers and premature abstraction.