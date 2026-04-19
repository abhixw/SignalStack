from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Assuming running from 'backend' directory
# Get database URL from environment or fallback to sqlite
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/sql_app_v3.db")

# Fixed for Render Postgres if necessary (Postgresql:// vs Postgres://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
