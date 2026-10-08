from datetime import date, timedelta
from decimal import Decimal

from app.db import models as m
from app.db.repositories.claims import ClaimRepository
from app.db.session import SessionLocal


def seed(session):
    repo = ClaimRepository(session)
    existing_policy = bool(repo.get(m.Policy, "expense-policy"))
    if not existing_policy:
        repo.add(
            m.Employee(
                id="employee-1",
                name="Alex Morgan",
                email="alex@example.test",
                department="Customer Success",
            )
        )
        repo.add(
            m.Policy(
                id="expense-policy",
                name="Employee expenses — manager approval",
                text="USD expenses up to $500. Meals, travel and supplies only. A verified receipt is required for every line. Submit within 90 days. Duplicates require review.",
                currency="USD",
                auto_accept=False,
                auto_reject=False,
            )
        )
        repo.flush()
        for code, params in [
            ("amount_limit", {"maximum": "500.00"}),
            ("receipt_required", {"required": True}),
            ("allowed_category", {"categories": ["meals", "travel", "supplies"]}),
            ("date_validity", {"maximum_age_days": 90}),
        ]:
            repo.add(
                m.PolicyRule(
                    id=code, policy_id="expense-policy", code=code, parameters=params
                )
            )
    else:
        policy = repo.get(m.Policy, "expense-policy")
        policy.auto_accept = False
        policy.auto_reject = False
    for claim_id, title, amount, category, receipt in [
        ("CLM-001", "Client lunch", "84.50", "meals", True),
        ("CLM-002", "Personal entertainment", "125.00", "entertainment", True),
        ("CLM-003", "Airport taxi — receipt missing", "62.00", "travel", False),
        ("CLM-004", "Office stationery", "48.25", "supplies", True),
        ("CLM-005", "Conference rail ticket", "186.00", "travel", True),
        ("CLM-006", "Hotel stay above allowance", "680.00", "travel", True),
        ("CLM-007", "Team lunch — receipt missing", "115.00", "meals", False),
    ]:
        if repo.get(m.Claim, claim_id):
            continue
        repo.add(
            m.Claim(
                id=claim_id,
                employee_id="employee-1",
                policy_id="expense-policy",
                title=title,
                amount=Decimal(amount),
                submitted_date=date.today(),
                currency="USD",
                status="submitted",
            )
        )
        repo.flush()
        repo.add(
            m.ClaimLine(
                id=claim_id + "-line",
                claim_id=claim_id,
                category=category,
                description=title,
                expense_date=date.today() - timedelta(days=2),
                amount=Decimal(amount),
            )
        )
        repo.flush()
        if receipt:
            repo.add(
                m.Evidence(
                    id=claim_id + "-receipt",
                    claim_id=claim_id,
                    line_id=claim_id + "-line",
                    kind="receipt",
                    filename=claim_id + ".txt",
                    content=f"Receipt supporting {title}: USD {amount}.",
                    fingerprint=claim_id + "-fingerprint",
                    verified=True,
                )
            )
    repo.commit()


def main():
    with SessionLocal() as session:
        seed(session)
    print(
        "Seven sample claims ready: CLM-001 through CLM-007 (existing decisions preserved)"
    )


if __name__ == "__main__":
    main()
