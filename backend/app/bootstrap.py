"""Create the separate local Week 4 database without touching Week 3 data."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import get_settings


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    if url.get_backend_name() != "postgresql":
        return
    if settings.decision_mode == "autonomous" and url.database == "claims":
        raise ValueError("Week 4 must use a separate database, such as claims_week4")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname=:name"),
                {"name": url.database},
            )
            if not exists:
                name = connection.dialect.identifier_preparer.quote_identifier(
                    url.database
                )
                connection.execute(text("CREATE DATABASE " + name))
        print("Week 4 database ready")
    finally:
        admin.dispose()


if __name__ == "__main__":
    main()
