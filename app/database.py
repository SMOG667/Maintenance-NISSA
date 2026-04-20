import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

logger = logging.getLogger("nissa.database")

# Support SQLite (local) et PostgreSQL (Supabase)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    connect_args = {"sslmode": "require"}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    try:
        from app.models import User, Question, CheckSession, Answer  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Base de donnees initialisee")
    except Exception as e:
        logger.error(f"Erreur initialisation DB: {e}")
