from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Finding(BaseModel):
    code: str
    severity: str
    message: str
    evidence_ids: list[str] = []


def calculate_checks(
    claim: dict,
    policy: dict,
    evidence: list[dict],
    duplicates: list[str],
    today: date | None = None,
) -> list[Finding]:
    today = today or date.today()
    findings = []

    def add(code, severity, message, ids=None):
        findings.append(
            Finding(
                code=code, severity=severity, message=message, evidence_ids=ids or []
            )
        )

    rules = {r["code"]: r["parameters"] for r in policy["rules"]}
    amount = Decimal(str(claim["amount"]))
    if (
        not claim["lines"]
        or amount <= 0
        or any(Decimal(str(line["amount"])) <= 0 for line in claim["lines"])
    ):
        add(
            "amount_validity",
            "reject",
            "Amounts must be positive and claim lines must exist.",
        )
    if (
        sum((Decimal(str(line["amount"])) for line in claim["lines"]), Decimal(0))
        != amount
    ):
        add(
            "amount_total",
            "reject",
            "Claim total does not equal the sum of line amounts.",
        )
    if claim["currency"] != policy["currency"]:
        add(
            "currency",
            "investigate",
            "Currency differs from policy; compliant conversion is not established by the supplied records.",
        )
    if amount > Decimal(str(rules["amount_limit"]["maximum"])):
        add("amount_limit", "reject", "Claim exceeds the policy amount limit.")
    allowed = rules["allowed_category"]["categories"]
    for line in claim["lines"]:
        if line["category"] not in allowed:
            add(
                "allowed_category",
                "reject",
                f"Category {line['category']} is not reimbursable.",
            )
        expense_date = date.fromisoformat(line["expense_date"])
        submitted = date.fromisoformat(claim["submitted_date"])
        if expense_date > today or expense_date > submitted or submitted > today:
            add(
                "date_validity",
                "reject",
                "Expense/submission date is in the future or expense follows submission.",
            )
        elif (submitted - expense_date).days > rules["date_validity"][
            "maximum_age_days"
        ]:
            add(
                "date_validity",
                "reject",
                "Expense was submitted after the allowed period.",
            )
        receipts = [
            e
            for e in evidence
            if e["kind"] == "receipt" and e["line_id"] == line["id"] and e["verified"]
        ]
        if rules["receipt_required"]["required"] and not receipts:
            add(
                "receipt_required",
                "investigate",
                f"Verified receipt missing for {line['description']}.",
            )
    if duplicates:
        add(
            "duplicate",
            "investigate",
            "Receipt fingerprint appears on another claim.",
            duplicates,
        )
    if not findings:
        add(
            "compliant",
            "pass",
            "All deterministic policy checks passed.",
            [e["id"] for e in evidence],
        )
    return findings
