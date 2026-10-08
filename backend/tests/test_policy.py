from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.domain.policy import calculate_checks


def test_seed_checks(service):
    assert service.calculate_policy_checks("CLM-001")[0]["code"] == "compliant"
    assert service.calculate_policy_checks("CLM-002")[0]["severity"] == "issue"
    assert service.calculate_policy_checks("CLM-003")[0]["code"] == "receipt_required"


def test_duplicate(service):
    from app.db.models import Evidence

    evidence = service.repo.get(Evidence, "CLM-002-receipt")
    evidence.fingerprint = "CLM-001-fingerprint"
    service.repo.commit()
    assert any(
        f["code"] == "duplicate" for f in service.calculate_policy_checks("CLM-001")
    )


def test_date_and_amount_total(service):
    from datetime import date, timedelta

    from app.db.models import ClaimLine

    line = service.repo.get(ClaimLine, "CLM-001-line")
    line.expense_date = date.today() + timedelta(days=1)
    line.amount = Decimal(1)
    service.repo.commit()
    codes = {f["code"] for f in service.calculate_policy_checks("CLM-001")}
    assert {"date_validity", "amount_total"} <= codes


@given(
    st.decimals(
        min_value="0.01",
        max_value="1000",
        places=2,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_amount_limit_exact(amount):
    claim = {
        "amount": str(amount),
        "currency": "USD",
        "submitted_date": "2026-01-02",
        "lines": [
            {
                "id": "l",
                "category": "meals",
                "expense_date": "2026-01-01",
                "amount": str(amount),
                "description": "Lunch",
            }
        ],
    }
    policy = {
        "currency": "USD",
        "rules": [
            {"code": "amount_limit", "parameters": {"maximum": "500"}},
            {"code": "allowed_category", "parameters": {"categories": ["meals"]}},
            {"code": "receipt_required", "parameters": {"required": False}},
            {"code": "date_validity", "parameters": {"maximum_age_days": 90}},
        ],
    }
    checks = calculate_checks(claim, policy, [], [])
    assert any(f.code == "amount_limit" for f in checks) == (amount > Decimal(500))
