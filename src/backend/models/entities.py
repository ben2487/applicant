"""Pydantic models for database entities."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Company(BaseModel):
    """Company entity model."""
    
    id: Optional[int] = None
    name: str = Field(..., description="Company display name")
    normalized_domain: str = Field(..., description="Normalized domain (e.g., acme.com)")
    website_url: Optional[str] = Field(None, description="Company website URL")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobPosting(BaseModel):
    """Job posting entity model."""
    
    id: Optional[int] = None
    company_id: Optional[int] = None
    title: str = Field(..., description="Job title")
    official_identifier: str = Field(..., description="Unique job identifier (ATS URL or company job URL)")
    work_mode: Optional[str] = Field(None, description="Remote/hybrid/onsite")
    compensation: Optional[Dict[str, Any]] = Field(None, description="Compensation details")
    raw_extracted: Optional[Dict[str, Any]] = Field(None, description="Raw extracted data from aggregator")
    source_aggregator_url: Optional[str] = Field(None, description="Original aggregator URL")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserProfile(BaseModel):
    """User profile entity model."""
    
    id: Optional[int] = None
    slug: str = Field(..., description="Unique profile slug (maps to filesystem)")
    display_name: str = Field(..., description="Human-readable display name")
    meta: Optional[Dict[str, Any]] = Field(None, description="Profile metadata (resume variants, etc.)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Application(BaseModel):
    """Application entity model (user-job relationship)."""
    
    id: Optional[int] = None
    user_profile_id: int = Field(..., description="User profile ID")
    job_posting_id: int = Field(..., description="Job posting ID")
    status: str = Field(..., description="Application status")
    last_run_id: Optional[int] = Field(None, description="ID of the last run for this application")
    notes: Optional[str] = Field(None, description="Application notes")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Run(BaseModel):
    """Run entity model (each automation attempt)."""
    
    id: Optional[int] = None
    application_id: Optional[int] = None
    initial_url: str = Field(..., description="Starting URL for the automation")
    headless: bool = Field(True, description="Whether browser ran in headless mode")
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result_status: Optional[str] = Field(None, description="Final result status")
    summary: Optional[str] = Field(None, description="Human-readable summary")
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw run data (parameters, timing, etc.)")
    created_at: Optional[datetime] = None


class Artifact(BaseModel):
    """Artifact entity model (file references)."""
    
    id: Optional[int] = None
    run_id: int = Field(..., description="Run ID this artifact belongs to")
    kind: str = Field(..., description="Artifact type (html_trace, jsonl_log, screenshot, etc.)")
    path: str = Field(..., description="Filesystem path to the artifact")
    sha256: Optional[str] = Field(None, description="SHA256 hash for integrity")
    created_at: Optional[datetime] = None


class RunEvent(BaseModel):
    """Run event entity model (structured events for triage)."""
    
    id: Optional[int] = None
    run_id: int = Field(..., description="Run ID this event belongs to")
    ts: Optional[datetime] = None
    level: str = Field(..., description="Log level (TRACE, DEBUG, INFO, WARN, ERROR)")
    category: str = Field(..., description="Event category (FIND_APPLY, LLM, BROWSER, FORMS, etc.)")
    code: Optional[str] = Field(None, description="Stable error/marker code")
    message: Optional[str] = Field(None, description="Event message")
    data: Optional[Dict[str, Any]] = Field(None, description="Event data")
    created_at: Optional[datetime] = None


# Status enums
class ApplicationStatus(str):
    """Application status values."""
    
    FOUND_APPLICATION_AND_FILLED = "FOUND_APPLICATION_AND_FILLED"
    FOUND_APPLICATION_BUT_FILL_FAILED = "FOUND_APPLICATION_BUT_FILL_FAILED"
    FOUND_CAREERS_BUT_NO_MATCHING_POSTING = "FOUND_CAREERS_BUT_NO_MATCHING_POSTING"
    FOUND_SITE_BUT_NO_CAREERS = "FOUND_SITE_BUT_NO_CAREERS"
    OFFICIAL_SITE_NOT_FOUND = "OFFICIAL_SITE_NOT_FOUND"
    BLOCKED_BY_LOGIN_OR_GATING = "BLOCKED_BY_LOGIN_OR_GATING"
    RATE_LIMIT_OR_CAPTCHA = "RATE_LIMIT_OR_CAPTCHA"
    ERROR_TRANSIENT_RETRYABLE = "ERROR_TRANSIENT_RETRYABLE"
    ERROR_PERMANENT = "ERROR_PERMANENT"


class RunResultStatus(str):
    """Run result status values."""
    
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class EventLevel(str):
    """Event level values."""
    
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class EventCategory(str):
    """Event category values."""
    
    FIND_APPLY = "FIND_APPLY"
    LLM = "LLM"
    BROWSER = "BROWSER"
    FORMS = "FORMS"
    CONSOLE = "CONSOLE"
    EXTRACT = "EXTRACT"
