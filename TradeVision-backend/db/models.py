import os
import socket
from datetime import datetime, date
from urllib.parse import urlparse
import uuid
from sqlalchemy import create_engine, Column, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = os.getenv("SUPABASE_DB_URL")

# Supabase URL needs a minor fix if using sqlalchemy and psycopg2
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Supabase requires SSL for all external connections.
if DATABASE_URL and "sslmode" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL += f"{separator}sslmode=require"

# Docker's default bridge network cannot route to IPv6 addresses, but DNS may
# resolve the Supabase hostname to an IPv6 address first. We resolve it to IPv4
# ourselves and pass the IP via psycopg2's `hostaddr`, which bypasses DNS in the
# driver while keeping the hostname in the URL for SSL SNI verification.
_connect_args: dict = {}
if DATABASE_URL:
    try:
        _host = urlparse(DATABASE_URL).hostname
        if _host:
            _ipv4 = socket.getaddrinfo(_host, None, socket.AF_INET)[0][4][0]
            _connect_args = {"hostaddr": _ipv4}
            print(f"[db] Resolved {_host} -> {_ipv4} (forcing IPv4)")
    except (socket.gaierror, IndexError) as e:
        print(f"[db] WARNING: IPv4 resolution failed ({e}), falling back to default DNS")

engine = create_engine(DATABASE_URL, connect_args=_connect_args) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    watchlist_items = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    portfolio_items = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")

class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, nullable=False)
    added_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("Profile", back_populates="watchlist_items")

class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    date_acquired = Column(Date, nullable=False)
    added_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("Profile", back_populates="portfolio_items")

# Auto-create tables if they don't exist yet (checkfirst=True is the default,
# so existing tables are left untouched). This avoids requiring a manual
# Alembic migration step before the first run.
if engine is not None:
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("[db] Tables verified/created successfully.")
    except Exception as e:
        print(f"[db] WARNING: Could not create tables: {e}")

# pyrefly: ignore [missing-import]
from fastapi import HTTPException

def get_db():
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
