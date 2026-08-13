from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base

# Defaults (pool_size=5, max_overflow=10 -> 15 max connections) were never enough for this app's
# real request shape: get_db()'s session stays open for the FULL request lifetime, including the
# CPU-bound face/object-detection inference in between the DB read and the final commit - so each
# request holds a connection for its whole duration (up to multiple seconds under load), not just
# the brief moments of actual DB I/O. Confirmed empirically, not guessed: a 50-concurrent-user load
# test (backend/loadtest/) hit real `QueuePool limit ... connection timed out` 500s at the default
# size. Raised to give real headroom for a class-sized concurrent exam session; still bounded (not
# unlimited) since Postgres itself has its own max_connections ceiling.
engine = create_engine(settings.DATABASE_URL, pool_size=20, max_overflow=30)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()