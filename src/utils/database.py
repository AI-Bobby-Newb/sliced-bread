"""Database connection and utilities."""

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from src.models.database import Base


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self, database_url: str = None):
        """Initialize database manager."""
        if database_url is None:
            # Default to SQLite for development
            database_url = os.getenv("DATABASE_URL", "sqlite:///sliced-bread.db")
        
        # Special handling for SQLite
        if database_url.startswith("sqlite"):
            self.engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
            )
        else:
            self.engine = create_engine(
                database_url,
                echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get database session (manual cleanup required)."""
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    with db_manager.get_session() as session:
        yield session


def init_database():
    """Initialize database with tables."""
    db_manager.create_tables()
    print("Database initialized successfully!")


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()