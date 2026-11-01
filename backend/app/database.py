from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
pool_args = {"poolclass": StaticPool} if settings.database_url in {"sqlite://", "sqlite:///:memory:"} else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True, **pool_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
