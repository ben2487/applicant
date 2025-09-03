"""Database connection management using psycopg2."""

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool


class DatabaseManager:
    """Manages database connections and pooling."""
    
    def __init__(self, database_url: str | None = None):
        """Initialize the database manager.
        
        Args:
            database_url: PostgreSQL connection URL. If None, reads from DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.pool: psycopg2.pool.SimpleConnectionPool | None = None
    
    def initialize(self) -> None:
        """Initialize the connection pool."""
        # Parse connection URL
        if self.database_url.startswith("postgresql://"):
            # Convert to psycopg2 format
            conn_str = self.database_url.replace("postgresql://", "postgresql://")
        else:
            conn_str = self.database_url
        
        self.pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=conn_str
        )
    
    def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            self.pool.closeall()
    
    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Get a database connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple | None = None) -> None:
        """Execute a query without returning results."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
    
    def fetch_one(self, query: str, params: tuple | None = None) -> dict | None:
        """Fetch a single row."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                # Commit if this is an INSERT/UPDATE/DELETE query
                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                return dict(result) if result else None
    
    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]:
        """Fetch all rows."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                # Commit if this is an INSERT/UPDATE/DELETE query
                if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                return [dict(result) for result in results]


# Global database manager instance
db_manager = DatabaseManager()
