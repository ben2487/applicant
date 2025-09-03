"""Database repository layer for data access."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg2.extras

from ..models.entities import (
    Application,
    ApplicationStatus,
    Artifact,
    Company,
    EventCategory,
    EventLevel,
    JobPosting,
    Run,
    RunEvent,
    RunResultStatus,
    UserProfile,
)
from .connection import db_manager


class CompanyRepository:
    """Repository for company operations."""
    
    @staticmethod
    def create(company: Company) -> Company:
        """Create a new company."""
        query = """
            INSERT INTO companies (name, normalized_domain, website_url)
            VALUES (%s, %s, %s)
            RETURNING id, name, normalized_domain, website_url, created_at, updated_at
        """
        result = db_manager.fetch_one(
            query, (company.name, company.normalized_domain, company.website_url)
        )
        return Company(**result)
    
    @staticmethod
    def get_by_domain(normalized_domain: str) -> Optional[Company]:
        """Get company by normalized domain."""
        query = """
            SELECT id, name, normalized_domain, website_url, created_at, updated_at
            FROM companies
            WHERE normalized_domain = %s
        """
        result = db_manager.fetch_one(query, (normalized_domain,))
        return Company(**result) if result else None
    
    @staticmethod
    def get_by_id(company_id: int) -> Optional[Company]:
        """Get company by ID."""
        query = """
            SELECT id, name, normalized_domain, website_url, created_at, updated_at
            FROM companies
            WHERE id = %s
        """
        result = db_manager.fetch_one(query, (company_id,))
        return Company(**result) if result else None


class JobPostingRepository:
    """Repository for job posting operations."""
    
    @staticmethod
    def create(job_posting: JobPosting) -> JobPosting:
        """Create a new job posting."""
        query = """
            INSERT INTO job_postings (company_id, title, official_identifier, work_mode, compensation, raw_extracted, source_aggregator_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, company_id, title, official_identifier, work_mode, compensation, raw_extracted, source_aggregator_url, created_at, updated_at
        """
        result = db_manager.fetch_one(
            query,
            (
                job_posting.company_id,
                job_posting.title,
                job_posting.official_identifier,
                job_posting.work_mode,
                json.dumps(job_posting.compensation) if job_posting.compensation else None,
                json.dumps(job_posting.raw_extracted) if job_posting.raw_extracted else None,
                job_posting.source_aggregator_url,
            ),
        )
        return JobPosting(**result)
    
    @staticmethod
    def get_by_identifier(official_identifier: str) -> Optional[JobPosting]:
        """Get job posting by official identifier."""
        query = """
            SELECT id, company_id, title, official_identifier, work_mode, compensation, raw_extracted, source_aggregator_url, created_at, updated_at
            FROM job_postings
            WHERE official_identifier = %s
        """
        result = db_manager.fetch_one(query, (official_identifier,))
        return JobPosting(**result) if result else None
    
    @staticmethod
    def get_by_id(job_id: int) -> Optional[JobPosting]:
        """Get job posting by ID."""
        query = """
            SELECT id, company_id, title, official_identifier, work_mode, compensation, raw_extracted, source_aggregator_url, created_at, updated_at
            FROM job_postings
            WHERE id = %s
        """
        result = db_manager.fetch_one(query, (job_id,))
        return JobPosting(**result) if result else None


class UserProfileRepository:
    """Repository for user profile operations."""
    
    @staticmethod
    def create(user_profile: UserProfile) -> UserProfile:
        """Create a new user profile."""
        query = """
            INSERT INTO user_profiles (slug, display_name, meta)
            VALUES (%s, %s, %s)
            RETURNING id, slug, display_name, meta, created_at, updated_at
        """
        result = db_manager.fetch_one(
            query,
            (
                user_profile.slug,
                user_profile.display_name,
                json.dumps(user_profile.meta) if user_profile.meta else None,
            ),
        )
        return UserProfile(**result)
    
    @staticmethod
    def get_by_slug(slug: str) -> Optional[UserProfile]:
        """Get user profile by slug."""
        query = """
            SELECT id, slug, display_name, meta, created_at, updated_at
            FROM user_profiles
            WHERE slug = %s
        """
        result = db_manager.fetch_one(query, (slug,))
        return UserProfile(**result) if result else None
    
    @staticmethod
    def get_all() -> List[UserProfile]:
        """Get all user profiles."""
        query = """
            SELECT id, slug, display_name, meta, created_at, updated_at
            FROM user_profiles
            ORDER BY display_name
        """
        results = db_manager.fetch_all(query)
        return [UserProfile(**result) for result in results]


class ApplicationRepository:
    """Repository for application operations."""
    
    @staticmethod
    def create(application: Application) -> Application:
        """Create a new application."""
        query = """
            INSERT INTO applications (user_profile_id, job_posting_id, status, last_run_id, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_profile_id, job_posting_id, status, last_run_id, notes, created_at, updated_at
        """
        result = db_manager.fetch_one(
            query,
            (
                application.user_profile_id,
                application.job_posting_id,
                application.status,
                application.last_run_id,
                application.notes,
            ),
        )
        return Application(**result)
    
    @staticmethod
    def get_by_user_and_job(user_profile_id: int, job_posting_id: int) -> Optional[Application]:
        """Get application by user and job."""
        query = """
            SELECT id, user_profile_id, job_posting_id, status, last_run_id, notes, created_at, updated_at
            FROM applications
            WHERE user_profile_id = %s AND job_posting_id = %s
        """
        result = db_manager.fetch_one(query, (user_profile_id, job_posting_id))
        return Application(**result) if result else None
    
    @staticmethod
    def update_status(application_id: int, status: str, last_run_id: Optional[int] = None) -> None:
        """Update application status."""
        query = """
            UPDATE applications
            SET status = %s, last_run_id = %s, updated_at = NOW()
            WHERE id = %s
        """
        db_manager.execute_query(query, (status, last_run_id, application_id))
    
    @staticmethod
    def get_by_user(user_profile_id: int) -> List[Application]:
        """Get all applications for a user."""
        query = """
            SELECT id, user_profile_id, job_posting_id, status, last_run_id, notes, created_at, updated_at
            FROM applications
            WHERE user_profile_id = %s
            ORDER BY updated_at DESC
        """
        results = db_manager.fetch_all(query, (user_profile_id,))
        return [Application(**result) for result in results]


class RunRepository:
    """Repository for run operations."""
    
    @staticmethod
    def create(run: Run) -> Run:
        """Create a new run."""
        query = """
            INSERT INTO runs (application_id, initial_url, headless, started_at, ended_at, result_status, summary, raw)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, application_id, initial_url, headless, started_at, ended_at, result_status, summary, raw, created_at
        """
        result = db_manager.fetch_one(
            query,
            (
                run.application_id,
                run.initial_url,
                run.headless,
                run.started_at or datetime.now(),
                run.ended_at,
                run.result_status,
                run.summary,
                json.dumps(run.raw) if run.raw else None,
            ),
        )
        return Run(**result)
    
    @staticmethod
    def get_by_id(run_id: int) -> Optional[Run]:
        """Get run by ID."""
        query = """
            SELECT id, application_id, initial_url, headless, started_at, ended_at, result_status, summary, raw, created_at
            FROM runs
            WHERE id = %s
        """
        result = db_manager.fetch_one(query, (run_id,))
        return Run(**result) if result else None
    
    @staticmethod
    def update_status(run_id: int, result_status: str, summary: Optional[str] = None, ended_at: Optional[datetime] = None) -> None:
        """Update run status."""
        query = """
            UPDATE runs
            SET result_status = %s, summary = %s, ended_at = %s
            WHERE id = %s
        """
        db_manager.execute_query(query, (result_status, summary, ended_at or datetime.now(), run_id))
    
    @staticmethod
    def get_recent_runs(limit: int = 50) -> List[Run]:
        """Get recent runs ordered by start time."""
        query = """
            SELECT id, application_id, initial_url, headless, started_at, ended_at, result_status, summary, raw, created_at
            FROM runs
            ORDER BY started_at DESC
            LIMIT %s
        """
        results = db_manager.fetch_all(query, (limit,))
        return [Run(**result) for result in results]


class ArtifactRepository:
    """Repository for artifact operations."""
    
    @staticmethod
    def create(artifact: Artifact) -> Artifact:
        """Create a new artifact."""
        query = """
            INSERT INTO artifacts (run_id, kind, path, sha256)
            VALUES (%s, %s, %s, %s)
            RETURNING id, run_id, kind, path, sha256, created_at
        """
        result = db_manager.fetch_one(
            query, (artifact.run_id, artifact.kind, artifact.path, artifact.sha256)
        )
        return Artifact(**result)
    
    @staticmethod
    def get_by_run(run_id: int) -> List[Artifact]:
        """Get all artifacts for a run."""
        query = """
            SELECT id, run_id, kind, path, sha256, created_at
            FROM artifacts
            WHERE run_id = %s
            ORDER BY created_at
        """
        results = db_manager.fetch_all(query, (run_id,))
        return [Artifact(**result) for result in results]


class RunEventRepository:
    """Repository for run event operations."""
    
    @staticmethod
    def create(event: RunEvent) -> RunEvent:
        """Create a new run event."""
        query = """
            INSERT INTO run_events (run_id, ts, level, category, code, message, data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, run_id, ts, level, category, code, message, data, created_at
        """
        result = db_manager.fetch_one(
            query,
            (
                event.run_id,
                event.ts or datetime.now(),
                event.level,
                event.category,
                event.code,
                event.message,
                json.dumps(event.data) if event.data else None,
            ),
        )
        return RunEvent(**result)
    
    @staticmethod
    def get_by_run(run_id: int, limit: int = 1000) -> List[RunEvent]:
        """Get events for a run."""
        query = """
            SELECT id, run_id, ts, level, category, code, message, data, created_at
            FROM run_events
            WHERE run_id = %s
            ORDER BY ts DESC
            LIMIT %s
        """
        results = db_manager.fetch_all(query, (run_id, limit))
        return [RunEvent(**result) for result in results]
    
    @staticmethod
    def get_error_summary() -> List[Tuple[str, int]]:
        """Get summary of error codes for triage."""
        query = """
            SELECT code, COUNT(*) as count
            FROM run_events
            WHERE level = 'ERROR' AND code IS NOT NULL
            GROUP BY code
            ORDER BY count DESC
            LIMIT 20
        """
        results = db_manager.fetch_all(query)
        return [(row['code'], row['count']) for row in results]

