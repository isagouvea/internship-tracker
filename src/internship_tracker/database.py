from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .constants import DB_PATH
from .models import Base


def engine_for(path: Path = DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", future=True)


def initialize_database(path: Path = DB_PATH):
    engine = engine_for(path)
    Base.metadata.create_all(engine)
    return engine


def session_factory(path: Path = DB_PATH) -> sessionmaker[Session]:
    return sessionmaker(bind=initialize_database(path), expire_on_commit=False)
