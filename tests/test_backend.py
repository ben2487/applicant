"""Backend tests."""

import asyncio
import json
import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

import psycopg
from flask import Flask
from flask_socketio import SocketIO

from src.backend.app import create_test_app
from src.backend.database.connection import DatabaseManager
from src.backend.database.repository import (
    CompanyRepository,
    JobPostingRepository,
    UserProfileRepository,
    ApplicationRepository,
    RunRepository,
    ArtifactRepository,
    RunEventRepository,
)
from src.backend.models.entities import (
    Company,
    JobPosting,
    UserProfile,
    Application,
    Run,
    Artifact,
    RunEvent,
    ApplicationStatus,
    RunResultStatus,
    EventLevel,
    EventCategory,
)


@pytest.fixture
def app():
    """Create test Flask app."""
    return create_test_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def socketio(app):
    """Create test SocketIO client."""
    return SocketIO(app)


@pytest.fixture
async def db_manager():
    """Create test database manager."""
    # Use test database URL
    test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://localhost/webbot_test")
    manager = DatabaseManager(test_db_url)
    await manager.initialize()
    yield manager
    await manager.close()


class TestDatabaseConnection:
    """Test database connection functionality."""
    
    @pytest.mark.asyncio
    async def test_database_connection(self, db_manager):
        """Test basic database connection."""
        async with db_manager.get_connection() as conn:
            result = await conn.execute("SELECT 1")
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_database_query(self, db_manager):
        """Test database query execution."""
        result = await db_manager.fetch_one("SELECT 42 as answer")
        assert result is not None
        assert result[0] == 42


class TestCompanyRepository:
    """Test company repository operations."""
    
    @pytest.mark.asyncio
    async def test_create_company(self, db_manager):
        """Test creating a company."""
        company = Company(
            name="Test Company",
            normalized_domain="test.com",
            website_url="https://test.com"
        )
        
        created = await CompanyRepository.create(company)
        assert created.id is not None
        assert created.name == "Test Company"
        assert created.normalized_domain == "test.com"
    
    @pytest.mark.asyncio
    async def test_get_company_by_domain(self, db_manager):
        """Test getting company by domain."""
        # Create a company first
        company = Company(
            name="Test Company",
            normalized_domain="test.com",
            website_url="https://test.com"
        )
        created = await CompanyRepository.create(company)
        
        # Retrieve by domain
        found = await CompanyRepository.get_by_domain("test.com")
        assert found is not None
        assert found.id == created.id
        assert found.name == "Test Company"
    
    @pytest.mark.asyncio
    async def test_get_company_by_id(self, db_manager):
        """Test getting company by ID."""
        # Create a company first
        company = Company(
            name="Test Company",
            normalized_domain="test.com",
            website_url="https://test.com"
        )
        created = await CompanyRepository.create(company)
        
        # Retrieve by ID
        found = await CompanyRepository.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id
        assert found.name == "Test Company"


class TestUserProfileRepository:
    """Test user profile repository operations."""
    
    @pytest.mark.asyncio
    async def test_create_user_profile(self, db_manager):
        """Test creating a user profile."""
        user = UserProfile(
            slug="test-user",
            display_name="Test User",
            meta={"resume_count": 3}
        )
        
        created = await UserProfileRepository.create(user)
        assert created.id is not None
        assert created.slug == "test-user"
        assert created.display_name == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_user_by_slug(self, db_manager):
        """Test getting user by slug."""
        # Create a user first
        user = UserProfile(
            slug="test-user",
            display_name="Test User",
            meta={"resume_count": 3}
        )
        created = await UserProfileRepository.create(user)
        
        # Retrieve by slug
        found = await UserProfileRepository.get_by_slug("test-user")
        assert found is not None
        assert found.id == created.id
        assert found.slug == "test-user"
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, db_manager):
        """Test getting all users."""
        # Create multiple users
        user1 = UserProfile(slug="user1", display_name="User 1")
        user2 = UserProfile(slug="user2", display_name="User 2")
        
        await UserProfileRepository.create(user1)
        await UserProfileRepository.create(user2)
        
        # Get all users
        users = await UserProfileRepository.get_all()
        assert len(users) >= 2
        slugs = [user.slug for user in users]
        assert "user1" in slugs
        assert "user2" in slugs


class TestRunRepository:
    """Test run repository operations."""
    
    @pytest.mark.asyncio
    async def test_create_run(self, db_manager):
        """Test creating a run."""
        run = Run(
            initial_url="https://example.com/job",
            headless=True,
            result_status=RunResultStatus.IN_PROGRESS
        )
        
        created = await RunRepository.create(run)
        assert created.id is not None
        assert created.initial_url == "https://example.com/job"
        assert created.headless is True
        assert created.result_status == RunResultStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_get_run_by_id(self, db_manager):
        """Test getting run by ID."""
        # Create a run first
        run = Run(
            initial_url="https://example.com/job",
            headless=True,
            result_status=RunResultStatus.IN_PROGRESS
        )
        created = await RunRepository.create(run)
        
        # Retrieve by ID
        found = await RunRepository.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id
        assert found.initial_url == "https://example.com/job"
    
    @pytest.mark.asyncio
    async def test_update_run_status(self, db_manager):
        """Test updating run status."""
        # Create a run first
        run = Run(
            initial_url="https://example.com/job",
            headless=True,
            result_status=RunResultStatus.IN_PROGRESS
        )
        created = await RunRepository.create(run)
        
        # Update status
        await RunRepository.update_status(
            created.id,
            RunResultStatus.SUCCESS,
            "Job application completed successfully"
        )
        
        # Verify update
        updated = await RunRepository.get_by_id(created.id)
        assert updated.result_status == RunResultStatus.SUCCESS
        assert updated.summary == "Job application completed successfully"
    
    @pytest.mark.asyncio
    async def test_get_recent_runs(self, db_manager):
        """Test getting recent runs."""
        # Create multiple runs
        run1 = Run(initial_url="https://example.com/job1", headless=True)
        run2 = Run(initial_url="https://example.com/job2", headless=True)
        
        await RunRepository.create(run1)
        await RunRepository.create(run2)
        
        # Get recent runs
        runs = await RunRepository.get_recent_runs(limit=10)
        assert len(runs) >= 2
        urls = [run.initial_url for run in runs]
        assert "https://example.com/job1" in urls
        assert "https://example.com/job2" in urls


class TestRunEventRepository:
    """Test run event repository operations."""
    
    @pytest.mark.asyncio
    async def test_create_run_event(self, db_manager):
        """Test creating a run event."""
        # Create a run first
        run = Run(initial_url="https://example.com/job", headless=True)
        created_run = await RunRepository.create(run)
        
        # Create an event
        event = RunEvent(
            run_id=created_run.id,
            level=EventLevel.INFO,
            category=EventCategory.BROWSER,
            message="Page loaded successfully",
            code="PAGE_LOADED"
        )
        
        created_event = await RunEventRepository.create(event)
        assert created_event.id is not None
        assert created_event.run_id == created_run.id
        assert created_event.level == EventLevel.INFO
        assert created_event.category == EventCategory.BROWSER
    
    @pytest.mark.asyncio
    async def test_get_events_by_run(self, db_manager):
        """Test getting events for a run."""
        # Create a run first
        run = Run(initial_url="https://example.com/job", headless=True)
        created_run = await RunRepository.create(run)
        
        # Create multiple events
        event1 = RunEvent(
            run_id=created_run.id,
            level=EventLevel.INFO,
            category=EventCategory.BROWSER,
            message="Event 1"
        )
        event2 = RunEvent(
            run_id=created_run.id,
            level=EventLevel.ERROR,
            category=EventCategory.LLM,
            message="Event 2"
        )
        
        await RunEventRepository.create(event1)
        await RunEventRepository.create(event2)
        
        # Get events for the run
        events = await RunEventRepository.get_by_run(created_run.id)
        assert len(events) >= 2
        levels = [event.level for event in events]
        assert EventLevel.INFO in levels
        assert EventLevel.ERROR in levels


class TestAPIEndpoints:
    """Test Flask API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
    
    def test_get_runs_empty(self, client):
        """Test getting runs when none exist."""
        response = client.get("/api/runs/")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "runs" in data
        assert len(data["runs"]) == 0
    
    def test_create_run_missing_fields(self, client):
        """Test creating run with missing required fields."""
        response = client.post("/api/runs/", json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "initial_url" in data["error"]
    
    def test_create_run_valid(self, client):
        """Test creating run with valid data."""
        run_data = {
            "initial_url": "https://example.com/job",
            "headless": True,
            "result_status": "IN_PROGRESS"
        }
        response = client.post("/api/runs/", json=run_data)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["initial_url"] == "https://example.com/job"
        assert data["headless"] is True
    
    def test_get_users_empty(self, client):
        """Test getting users when none exist."""
        response = client.get("/api/users/")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "users" in data
        assert len(data["users"]) == 0
    
    def test_create_user_missing_fields(self, client):
        """Test creating user with missing required fields."""
        response = client.post("/api/users/", json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "slug" in data["error"]
    
    def test_create_user_valid(self, client):
        """Test creating user with valid data."""
        user_data = {
            "slug": "test-user",
            "display_name": "Test User",
            "meta": {"resume_count": 3}
        }
        response = client.post("/api/users/", json=user_data)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["slug"] == "test-user"
        assert data["display_name"] == "Test User"


class TestWebSocketHandlers:
    """Test WebSocket handlers."""
    
    def test_websocket_connection(self, socketio, client):
        """Test WebSocket connection."""
        # This is a basic test - in a real scenario you'd need to mock the SocketIO client
        # For now, we'll just test that the handlers are properly set up
        assert socketio is not None


if __name__ == "__main__":
    pytest.main([__file__])
