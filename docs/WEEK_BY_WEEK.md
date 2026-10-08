# What changes from Week 1 to Week 4

The progression is **facts → advice → controlled automation → autonomous investigation and decision**. The [teaching guide](TEACHING_GUIDE.md) explains the shared code, memory, agent and RAG in detail.

This comparison is based on the actual branch implementations: Week 1 `6673c47`, Week 2 `c712cf3`, Week 3 `40315ba`, and Week 4 `11b0472`. Later documentation-only commits do not change these behavior snapshots.

## Behavior at a glance

| Capability | Week 1 | Week 2 | Week 3 | Week 4 |
| --- | --- | --- | --- | --- |
| Main AI output | Factual summary | Accept/Reject recommendation | Accept/Reject/Investigate recommendation | Investigation report then binary assessment |
| Can AI recommend a decision? | No | Yes | Yes | Yes, during autonomous stages |
| Can the application finalize without a manager? | No | No | Yes, eligible clear cases | Yes, normal autonomous operation |
| Who investigates uncertainty? | Manager chooses Investigate | No investigation action; manager decides binary | Manager after escalation | AI examines supplied records |
| Manager actions | Accept, Reject, Investigate | Accept, Reject | Accept, Reject, Request information on reviews | Human-decision API disabled in autonomous mode |
| Missing receipt | State missing fact; manager chooses | Recommend Reject; manager chooses | Pending manager review | Reject under supplied autonomous policy |
| Start processing | Run summary batch | Run recommendation batch | Run assessment batch | Worker discovers automatically |
| Review creation | Every valid summary | Every valid recommendation | Cases outside automatic execution controls | No new human review |
| Dashboard | Queue + manager review | Queue + manager review | Queue + manager review | Autonomous monitor + decision history |
| Model calls per normal claim run | One summary | One recommendation | One assessment | Investigation + assessment |
| Chatbot | Facts/clarifying questions, no decision advice | Explain facts and advice | Explain assessments/escalations | Explain investigation/decision |
| Chatbot can execute actions | No | No | No | No |
| Outcome memory retrieval | Latest five manager-reviewed same-category outcomes | Same | Same; automatic outcomes excluded | Includes prior AI outcomes in autonomous mode |
| Policy vector RAG | Available from inherited code | Available from inherited code | Available | Available; autonomous policy v2 |

RAG defaults to disabled in checked-in configuration; local `.env` can enable it. The table says available, not necessarily running for every demo.

## The same seven claims through all four weeks

| Claim/scenario | Week 1 after summary | Week 2 AI advice / status | Week 3 supplied-policy result | Week 4 supplied-policy result |
| --- | --- | --- | --- | --- |
| CLM-001: $84.50 client lunch, receipt | Pending manager; no advice | Accept / pending manager | Accepted | Accepted |
| CLM-002: $125 personal entertainment | Pending manager; no advice | Reject / pending manager | Rejected | Rejected |
| CLM-003: $62 taxi, receipt missing | Pending manager; no advice | Reject / pending manager | Pending manager review | Rejected |
| CLM-004: $48.25 stationery, receipt | Pending manager; no advice | Accept / pending manager | Accepted | Accepted |
| CLM-005: $186 rail ticket, receipt | Pending manager; no advice | Accept / pending manager | Accepted | Accepted |
| CLM-006: $680 hotel above limit | Pending manager; no advice | Reject / pending manager | Rejected | Rejected |
| CLM-007: $115 team lunch, receipt missing | Pending manager; no advice | Reject / pending manager | Pending manager review | Rejected |

Week 1/2 final outcomes are not preset by the table: the manager can accept or reject regardless of the facts/advice. Week 1 can first Investigate. The Week 2 advice entries describe mock behavior; real model quality is evaluated separately. Week 3/4 outcomes assume the supplied policy, valid grounded output and functioning infrastructure.

## Week 1 → Week 2: facts become advice

### AI output

Week 1's structured summary has `summary`, factual confidence, finding codes, evidence IDs and missing information, with no recommendation. Week 2 replaces the narrative field with `explanation` and adds a binary `recommendation: accept|reject`.

The gateway prompt changes from summarization/no-decision-advice to decision support. Week 2's mock recommends Reject for a breach or unverified requirement and Accept for a compliant case. Neither branch lets the service automatically finalize.

### Manager flow

Week 1 supports a persistent `under_investigation` state. Investigate records an action/rationale, keeps the review open, increments version and creates no final outcome. The manager later Accepts/Rejects.

Week 2 removes that action. Every valid AI recommendation still creates `pending_manager_review`; the manager has exactly Accept/Reject. The manager can disagree with advice. Role, rationale, version and closed-review controls remain.

### Code to compare

```sh
git diff week-1 week-2 -- \
  backend/app/schemas/assessment.py \
  backend/app/ai/gateway.py \
  backend/app/ai/providers/mock.py \
  backend/app/assessment/service.py \
  frontend/src/features/reviews/Reviews.tsx
```

The rule severity changes from Week 1's neutral `issue` labels to Week 2's `reject` labels that inform advice; missing information stays `unverified`. The business decision still belongs to the manager.

## Week 2 → Week 3: advice can become a controlled action

Week 3 restores a third AI recommendation, Investigate, and allows the service to execute eligible clear Accept/Reject recommendations. The model still does not choose arbitrary tools or write SQL.

Automatic Accept requires:

- Recommendation Accept.
- Confidence at least 0.90, no unresolved questions.
- All deterministic findings pass.
- Policy permits automatic acceptance.
- Referenced evidence equals the supplied evidence set.
- Current version, unchanged claim/policy/evidence/checks and valid source IDs.

Automatic Reject requires:

- Recommendation Reject.
- Confidence at least 0.90, no unresolved questions.
- A deterministic reject-severity finding exists and is referenced by the assessment.
- Policy permits automatic rejection.
- Current source/version/reference controls.

Anything else creates manager review. Missing receipts, duplicate evidence or uncertain currency are investigate-severity findings rather than proof of an automatic rejection. The manager can Accept, Reject or Request information. Request information keeps the review open as `information_requested`; it is not the same action name as Week 1's Investigate.

`capture_outcome()` now also stores automatic outcomes with `reviewed=false`. Default enterprise-memory retrieval still requires `reviewed=true`, so automatic outcomes are visible as records but do not enter the reviewed-memory context.

Important code: [Week 3 ClaimService](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-3/backend/app/assessment/service.py), [gateway](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-3/backend/app/ai/gateway.py), [policy checks](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-3/backend/app/domain/policy.py).

## Week 3 → Week 4: AI investigates supplied records and owns the normal final decision

### A new investigation stage

ClaimAgent calls `gateway.investigate()` before `gateway.assess()`. Its strict Investigation output covers all current check codes, evidence references, conclusion, confidence, summary and limitations. It is separately recorded in audit. The assessment gets the investigation as context.

This is another stage inside the bounded agent, not a second independently orchestrated agent. It does not collect new receipts, perform web research, contact employees or resolve missing evidence through external systems.

### A binary autonomous service gate

The final autonomous schema permits only Accept/Reject. Acceptance requires both stages to support Accept at confidence >=0.90, no current rule issues, no limitations/unresolved questions, complete evidence references and policy permission. Otherwise the supplied autonomous policy rejects with reasons. A provider outage/invalid response/stale state remains a failed run, not a business rejection.

New human reviews are removed. Existing active Week 3-style reviews can close as `closed_by_ai`, with an AI decision/rationale. `DECISION_MODE=autonomous` is the default and human decisions are disabled in that mode. Historical `human_review` paths remain explicitly available for regression coverage on Week 4, not as its normal UI.

### Automatic scheduling and dashboard

Worker startup plus a five-second scan discovers undecided claims. Stable queue/claim/version job IDs deduplicate scheduling; failed result TTL cooldown permits automatic recovery. The dashboard no longer exposes Run or Manager review. It shows processing, waiting/retry, final decision history and per-claim investigation reports.

### Memory and policy

Autonomous memory includes prior AI outcomes instead of requiring human-reviewed records. The policy README/seed describes autonomous evidence-based outcomes, and passage IDs use v2. RAG's section chunking, embedding dimensions and retrieval algorithm remain the same.

Key code: [Week 4 agent](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-4/backend/app/agents/claim_agent.py), [service](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-4/backend/app/assessment/service.py), [worker](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-4/backend/app/jobs/worker.py), [autonomous evals](https://github.com/vishrut-pdg/enterprise-ai-claims-demo/blob/week-4/backend/app/evaluation/autonomous.py).

## What stays shared

All branches retain the layered API/service/repository design, sample expense data, Decimal arithmetic and deterministic checks, restricted ADK trajectory, provider gateway/adapters, grounding/schema controls, recorded manager or AI outcomes, audit/telemetry, optional policy RAG and read-only chatbot.

The meaningful progression is not “Week 1 has no database” or “Week 2 has no RAG.” These stripped branches have inherited infrastructure. Their allowed AI roles and final-decision paths are what differs.

## Branch history versus lesson sequence

The lesson sequence is Week 1 → 2 → 3 → 4. The Git authoring sequence was different:

```text
initial baseline
└── Week 3 completion (40315ba)
    ├── Week 2 stripped scope (c712cf3)
    │   └── Week 1 stripped scope (6673c47)
    └── Week 4 autonomous scope (11b0472)
```

Week 4 was built on Week 3. Week 2 was fast-forwarded to Week 3 before stripping; Week 1 was fast-forwarded to Week 2 before stripping. These are separate teaching snapshots, not a request to merge their later narrowed scopes back into Week 4.

Documentation added after these commits can exist on one branch without changing the others. To inspect another week's implementation use `git show branch:path`, its GitHub branch, or a dedicated worktree. Switching Git branches does not automatically switch the ignored `.env`, cached settings or already-running servers.
