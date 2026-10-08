import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.service import ClaimService
from app.config import Settings
from app.db.models import Base
from app.db.repositories.claims import ClaimRepository
from app.seed import seed


@pytest.fixture
def service():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        seed(session)
        yield ClaimService(ClaimRepository(session))
    engine.dispose()


@pytest.fixture
def settings():
    return Settings(llm_provider="mock", llm_model="reference-mock", _env_file=None)
