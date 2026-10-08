# Enterprise AI Claims Reference Application

**Status:** Frozen for reference implementation  
**Purpose:** Reference application for the Enterprise AI Building Blocks learning program  
**Primary case:** Employee expense claim assessment and approval

---

## 1. Product purpose

Build a small enterprise application that demonstrates how conventional application capabilities, deterministic business logic, AI reasoning, agentic execution, human controls, enterprise memory and evaluation work together.

The system must be simple enough to teach but architecturally representative of a production enterprise AI application.

The application will be developed first as the completed Week 4 reference implementation.

It will later be split into four learner checkpoints.

---

## 2. Business situation

Employees submit expense claims.

Claims must be checked against company policy and available supporting evidence.

Today this type of process can require manual review to:

- understand the claim;
- find the applicable policy;
- verify receipts or evidence;
- calculate policy breaches;
- decide whether the claim can be accepted;
- determine whether it must be rejected;
- identify cases requiring investigation;
- document the reasoning;
- route uncertain cases to an authorized manager.

The application should demonstrate how AI can assist and partially automate this process without removing required business controls.

---

## 3. Primary users

### Employee

Submits a claim and receives its final status.

Employee-facing functionality is not the primary training focus.

### Claims Analyst

Reviews claims, supporting information, policy findings and AI assessments.

### Manager

Reviews claims that cannot be safely processed automatically.

The manager must see the evidence and reasoning required to make the final decision.

### System Administrator / Engineer

Runs the application, evaluates AI behavior and inspects audit and trace information.

---

## 4. Core business objects

The application must contain at minimum:

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

---

## 5. Main experience

The primary experience is:

Claim Queue  
→ Claim Detail  
→ Policy and Evidence  
→ Assessment  
→ Decision  
→ Action  
→ Outcome.

Claims requiring investigation follow:

Claim  
→ Assessment  
→ Investigation  
→ Manager Review Queue  
→ Manager Review Detail  
→ Manager Decision  
→ Outcome.

---

## 6. Application screens

### 6.1 Claim Queue

Display claims with:

- claim ID;
- employee;
- submitted date;
- amount;
- currency;
- claim type;
- current status;
- assessment status;
- recommended action where available.

Support filtering and sorting.

---

### 6.2 Claim Detail

Display:

- employee information;
- claim summary;
- claim lines;
- amounts;
- receipts/evidence;
- applicable policy;
- policy findings;
- assessment;
- processing history.

The screen must clearly separate source facts from calculated findings and AI interpretation.

---

### 6.3 Assessment

Display:

- recommendation;
- confidence;
- deterministic findings;
- explanation;
- supporting evidence;
- unresolved questions.

Allowed recommendations are:

- Accept
- Reject
- Investigate

---

### 6.4 Manager Review Queue

Display:

- Claim
- Employee
- Amount
- Investigation reason
- Assigned role
- Status

Only investigation cases belong in this queue.

---

### 6.5 Manager Review Detail

Display:

- claim facts;
- AI recommendation;
- policy findings;
- applicable policies;
- evidence;
- unresolved questions;
- previous review activity;
- decision history.

Manager actions:

- Accept
- Reject
- Request more information

---

### 6.6 Audit / Processing History

Display important application and AI events.

Examples:

- claim loaded;
- policy selected;
- checks executed;
- AI assessment requested;
- AI assessment validated;
- recommendation produced;
- claim accepted;
- claim rejected;
- investigation task created;
- manager decision recorded.

---

## 7. Deterministic business logic

Not all decisions should be delegated to an LLM.

The application must implement deterministic calculations and policy rules separately.

Examples:

- expense limit;
- receipt required;
- allowed expense category;
- date validity;
- duplicate claim detection;
- amount calculations.

Results must be persisted or represented as policy findings.

---

## 8. AI assessment

AI receives grounded application context.

It may receive:

- claim facts;
- policy findings;
- policy text;
- supporting evidence;
- previous relevant outcomes.

AI produces a structured assessment.

Required output:

- recommendation;
- confidence;
- findings;
- evidence references;
- unresolved questions;
- explanation.

AI output must be validated using Pydantic before it enters the business workflow.

---

## 9. Decision behavior

### Accept

The system must:

1. reload the current claim;
2. ensure the claim has not changed;
3. revalidate necessary policy checks;
4. verify automatic acceptance is allowed;
5. record the acceptance;
6. create an audit event.

Resulting status:

**Accepted**

---

### Reject

The system must:

1. reload the current claim;
2. ensure the claim has not changed;
3. verify an explicit rejection condition;
4. record the rejection;
5. create an audit event.

Resulting status:

**Rejected**

---

### Investigate

The system must:

1. create one manager-review task;
2. include assessment and evidence;
3. include unresolved questions;
4. prevent duplicate active review tasks;
5. create an audit event.

Resulting status:

**Pending manager review**

---

## 10. Agentic behavior

Google ADK is the agent framework.

Agents may:

- retrieve claim information;
- retrieve policy;
- retrieve evidence;
- call deterministic calculations;
- retrieve previous reviewed outcomes;
- prepare assessment context;
- request controlled application actions.

Agents must not have unrestricted database access.

The architecture must be:

Agent  
→ Tool  
→ Application Service  
→ Repository / external capability.

---

## 11. AI provider neutrality

The application must support interchangeable LLM providers.

Required providers:

- Ollama
- Google / Vertex AI
- SAP BTP AI / Generative AI Hub

Application logic must depend on an internal provider contract.

Conceptual architecture:

Application / ADK  
→ LLM Gateway  
→ Provider Adapter  
→ Model.

Provider selection happens through configuration.

Examples:

`LLM_PROVIDER=ollama`

`LLM_PROVIDER=vertex`

`LLM_PROVIDER=btp`

Provider-specific SDKs and authentication must remain inside their adapter/configuration layer.

---

## 12. Local model

Local development uses Ollama.

The model name must be configurable.

Initial configuration target:

`gemma4:e4b-it-q4_K_M`

The application must not depend on that specific model identifier.

---

## 13. Background processing

Redis and ARQ provide background-job execution.

Candidate background activities include:

- batch assessment;
- long-running investigation;
- retries;
- evaluation;
- reviewed-outcome processing.

The teaching architecture should distinguish:

**Request-time work** from **background work**.

---

## 14. Enterprise memory

Enterprise memory means preserving useful historical business outcomes.

It does not mean continuously fine-tuning the language model.

For reviewed claims, store:

- relevant claim context;
- policy findings;
- AI recommendation;
- final human decision;
- reviewer rationale;
- evidence references;
- timestamps.

Agents must be able to retrieve relevant previous outcomes when appropriate.

---

## 15. Evaluation

Evaluation must cover agent and workflow behavior, not only response wording.

Examples:

- Did the correct policy get selected?
- Was the correct claim version used?
- Were the required tools called?
- Was the relevant evidence retrieved?
- Was the recommendation supported by the findings?
- Was uncertainty handled correctly?
- Was manager review used where required?
- Was an unsafe business action prevented?

Maintain a small version-controlled evaluation dataset.

The design should support Google ADK trajectory evaluation.

---

## 16. Auditability

Important business and AI events must be auditable.

Each relevant event should support:

- timestamp;
- event type;
- actor;
- claim ID;
- workflow/run ID where applicable;
- relevant source/evidence identifiers;
- previous and resulting state where applicable.

AI execution records should capture useful metadata without storing credentials.

---

## 17. Observability

Use structured logs and OpenTelemetry.

The application should make it possible to trace:

HTTP request  
→ workflow  
→ agent  
→ model execution  
→ tool execution  
→ application service  
→ persistence  
→ resulting action.

---

## 18. Failure behavior

The system must handle:

- unavailable LLM provider;
- invalid structured AI output;
- model timeout;
- tool failure;
- database failure;
- duplicate review request;
- stale claim version;
- repeated action request;
- Redis/worker unavailability.

Failure must not silently create a business decision.

---

## 19. Local runtime

Local development uses:

- React/Vite on the host;
- FastAPI on the host;
- Ollama on the host;
- PostgreSQL in Docker;
- Redis in Docker.

Target ports:

- frontend: 5173
- backend: 8000
- PostgreSQL: 5432
- Redis: 6379
- Ollama: 11434

---

## 20. Deployment portability

One codebase must support:

### Local

Docker Compose + native application processes.

### SAP BTP

FastAPI application deployable to the Cloud Foundry environment.

SAP BTP AI access occurs through the BTP provider adapter.

### GCP

FastAPI application deployable to Cloud Run.

Google model access occurs through the Vertex/GCP provider adapter.

Application business logic must not contain platform conditionals.

Platform configuration belongs under:

`deploy/local/`

`deploy/btp/`

`deploy/gcp/`

---

## 21. Technology stack

### Frontend

React + TypeScript + Vite

Tailwind CSS + shadcn/ui

TanStack Query

TanStack Table

### Backend

Python 3.12

FastAPI

Pydantic v2

SQLAlchemy 2

Alembic

PostgreSQL

### Agent layer

Google ADK Python

### LLMs

Ollama

Google / Vertex AI

SAP BTP AI / Generative AI Hub

### Background processing

Redis + ARQ

### Testing

pytest

Hypothesis

Vitest

Playwright

### Observability

Structured logs

OpenTelemetry

### Package management

uv

pnpm

---

## 22. Seed scenarios

Provide at least three deterministic examples.

### Scenario A — Accept

Claim complies with the applicable policy.

Required evidence exists.

The system should recommend and safely process acceptance.

### Scenario B — Reject

Claim has an explicit policy condition that permits deterministic rejection.

The system should recommend and safely process rejection.

### Scenario C — Investigate

Evidence is incomplete, contradictory or insufficient for an automatic decision.

The system should create a manager-review task.

---

## 23. Learning-program mapping

The completed reference implementation will later be split into:

### Week 1 — Understand and retrieve

Application, claim, policy, evidence and data foundation.

### Week 2 — Assess and explain

Policy calculations, AI assessment and provider-neutral LLM access.

### Week 3 — Execute with controls

ADK agents, tools, automatic actions and manager review.

### Week 4 — Capture outcomes and improve

Enterprise memory, evaluation, observability and complete autonomous orchestration.

---

## 24. Product principles

The system must follow these principles:

**Ground before reasoning.**

AI must receive evidence and application context.

**Calculate before asking AI to calculate.**

Deterministic rules remain deterministic.

**AI recommends through structured contracts.**

Free-form text does not drive business state directly.

**Tools protect the application.**

Agents do not receive unrestricted system access.

**Autonomy has boundaries.**

Clear cases may be automated. Uncertain cases escalate.

**Human decisions become enterprise knowledge.**

Reviewed outcomes should improve future investigations through retrieval.

**Evaluate behavior, not only language.**

Tool use and workflow correctness matter.

**Cloud platform is an adapter.**

Application architecture must remain portable.

---

## 25. Definition of done

The reference implementation is complete when:

- the complete application runs locally;
- database migrations work;
- seed data can be loaded reproducibly;
- Claim Queue works;
- Claim Detail works;
- policies and evidence are retrievable;
- deterministic checks run;
- AI assessment produces validated structured output;
- Ollama works as a selectable provider;
- cloud-provider adapters follow the same internal contract;
- Accept works safely;
- Reject works safely;
- Investigate creates a manager-review task;
- manager review works;
- duplicate execution is controlled;
- audit events are persisted;
- prior reviewed outcomes can be retrieved;
- evaluation cases execute;
- automated tests pass;
- local setup is documented;
- no secrets are stored in source control;
- provider-specific logic remains isolated;
- core application logic remains portable between local, BTP and GCP.