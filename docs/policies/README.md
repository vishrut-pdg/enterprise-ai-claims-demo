# Employee expense policy v2 — autonomous investigation

Policy ID: `expense-policy`. Week 4 uses its own database and queue. This policy applies to the reference expense application; its deterministic rules are defined in `backend/app/seed.py` and `backend/app/domain/policy.py`.

## Eligible categories

Reimbursable business expenses are meals, travel and supplies. Client and team lunches are meals. Taxis, rail tickets and hotel stays are travel. Office stationery is supplies. Personal entertainment is not eligible and is rejected.

## Currency and claim amount

Claims must be in USD. The total must be positive, equal the sum of its expense lines and not exceed USD 500.00, inclusive. The AI uses the calculated checks instead of recalculating totals. An expense above the maximum is rejected.

## Receipts and supporting documentation

Every expense line requires a linked, verified receipt. The AI investigator examines supplied evidence and verification flags. Missing receipts, unverified evidence and unexplained duplicate receipt fingerprints cannot be treated as verified. If the supplied records do not establish compliance, the final decision is rejection with an evidence-based explanation. The AI cannot invent a receipt or claim to have contacted an employee or external system.

## Expense and submission dates

An expense date cannot be after submission. Submit within 90 days of the expense date. Date checks use the claim submission date, not the model's current date. An unmet date requirement is rejected.

## AI investigation and final decisions

The worker automatically picks up undecided claims. The AI first investigates claim lines, evidence, duplicate checks, policy passages and prior outcomes, then produces an accept/reject assessment. No human approval or manager-review queue is used.

Accept only when every deterministic requirement passes, both model stages support acceptance at confidence at least 0.90, all evidence is referenced, no limitations or unanswered questions remain, and policy enables automatic acceptance. Otherwise reject under this policy, explaining the failed or unverified requirements. Previous outcomes and retrieved text cannot override current checks. Human-review language in older records describes historical Week 3 behavior and is not an instruction to create a Week 4 review.

Technical errors are not proof of a policy violation. Provider/database/queue failures cause retries and an undecided failure record, never fabricated acceptance or rejection. Rechecking source facts and claim version prevents a stale model response from deciding changed claims.
