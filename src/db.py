"""
Database abstraction layer
Support SQLite (dev) et PostgreSQL (prod) via DATABASE_URL
"""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text, Table, Column, String, Integer, Float, MetaData, ForeignKey
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optionnel

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")

# Default to SQLite if no DATABASE_URL
if not DATABASE_URL:
    DB_PATH = DATA_DIR / "dms.sqlite3"
    DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True if "postgresql" in DATABASE_URL else False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata = MetaData()

# Table definitions (SQLAlchemy Core)
cases_table = Table(
    'cases', metadata,
    Column('id', String, primary_key=True),
    Column('case_type', String, nullable=False),
    Column('title', String, nullable=False),
    Column('lot', String),
    Column('created_at', String, nullable=False),
    Column('status', String, nullable=False)
)

artifacts_table = Table(
    'artifacts', metadata,
    Column('id', String, primary_key=True),
    Column('case_id', String, ForeignKey('cases.id'), nullable=False),
    Column('kind', String, nullable=False),
    Column('filename', String, nullable=False),
    Column('path', String, nullable=False),
    Column('uploaded_at', String, nullable=False),
    Column('meta_json', String)
)

memory_entries_table = Table(
    'memory_entries', metadata,
    Column('id', String, primary_key=True),
    Column('case_id', String, ForeignKey('cases.id'), nullable=False),
    Column('entry_type', String, nullable=False),
    Column('content_json', String, nullable=False),
    Column('created_at', String, nullable=False)
)

dao_criteria_table = Table(
    'dao_criteria', metadata,
    Column('id', String, primary_key=True),
    Column('case_id', String, ForeignKey('cases.id'), nullable=False),
    Column('categorie', String, nullable=False),
    Column('critere_nom', String, nullable=False),
    Column('description', String),
    Column('ponderation', Float, nullable=False),
    Column('type_reponse', String, nullable=False),
    Column('seuil_elimination', Float),
    Column('ordre_affichage', Integer, default=0),
    Column('created_at', String, nullable=False)
)

cba_template_schemas_table = Table(
    'cba_template_schemas', metadata,
    Column('id', String, primary_key=True),
    Column('case_id', String, ForeignKey('cases.id'), nullable=False),
    Column('template_name', String, nullable=False),
    Column('structure_json', String, nullable=False),
    Column('created_at', String, nullable=False),
    Column('reused_count', Integer, default=0)
)

offer_extractions_table = Table(
    'offer_extractions', metadata,
    Column('id', String, primary_key=True),
    Column('case_id', String, ForeignKey('cases.id'), nullable=False),
    Column('artifact_id', String, ForeignKey('artifacts.id'), nullable=False),
    Column('supplier_name', String, nullable=False),
    Column('extracted_data_json', String, nullable=False),
    Column('missing_fields_json', String),
    Column('created_at', String, nullable=False)
)


def init_db() -> None:
    """Create all tables (SQLite + PostgreSQL compatible)"""
    metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get database session (context manager)"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_engine() -> Engine:
    """Get SQLAlchemy engine"""
    return engine
