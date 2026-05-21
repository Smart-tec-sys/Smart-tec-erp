# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.settings import settings

if "sqlite" in settings.DB_URL:
    engine = create_engine(
        settings.DB_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(settings.DB_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
