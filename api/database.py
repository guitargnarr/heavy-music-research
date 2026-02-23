"""
Database configuration for Metalcore Index API.
Supports PostgreSQL (Render) and SQLite (local dev).
Pattern from: client-cms/api/database.py
"""
import os
import re
import ssl

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Handle Render postgres:// vs postgresql:// URL format
# Use pg8000 driver (pure Python, no compilation needed)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+pg8000" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

# Remove sslmode from URL (pg8000 handles SSL differently)
if "sslmode=" in DATABASE_URL:
    DATABASE_URL = re.sub(r"[\?&]sslmode=[^&]*", "", DATABASE_URL)
    DATABASE_URL = DATABASE_URL.replace("?&", "?").rstrip("?")

# SQLite for local development
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./metalcore_index.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    engine = create_engine(DATABASE_URL, connect_args={"ssl_context": ssl_context})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
