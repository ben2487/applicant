-- Database schema for job application automation system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Companies table
CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_domain TEXT UNIQUE NOT NULL,
    website_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job postings table
CREATE TABLE job_postings (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    official_identifier TEXT UNIQUE NOT NULL,
    work_mode TEXT,
    compensation JSONB,
    raw_extracted JSONB,
    source_aggregator_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profiles table
CREATE TABLE user_profiles (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Applications table (user-job relationships)
CREATE TABLE applications (
    id BIGSERIAL PRIMARY KEY,
    user_profile_id BIGINT REFERENCES user_profiles(id) ON DELETE CASCADE,
    job_posting_id BIGINT REFERENCES job_postings(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    last_run_id BIGINT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_profile_id, job_posting_id)
);

-- Runs table (each automation attempt)
CREATE TABLE runs (
    id BIGSERIAL PRIMARY KEY,
    application_id BIGINT REFERENCES applications(id) ON DELETE CASCADE,
    initial_url TEXT NOT NULL,
    headless BOOLEAN DEFAULT true,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    result_status TEXT,
    summary TEXT,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Artifacts table (file references)
CREATE TABLE artifacts (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES runs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Run events table (structured events for triage)
CREATE TABLE run_events (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES runs(id) ON DELETE CASCADE,
    ts TIMESTAMPTZ DEFAULT NOW(),
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    code TEXT,
    message TEXT,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_companies_normalized_domain ON companies(normalized_domain);
CREATE INDEX idx_job_postings_company_id ON job_postings(company_id);
CREATE INDEX idx_job_postings_official_identifier ON job_postings(official_identifier);
CREATE INDEX idx_applications_user_profile_id ON applications(user_profile_id);
CREATE INDEX idx_applications_job_posting_id ON applications(job_posting_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_runs_application_id ON runs(application_id);
CREATE INDEX idx_runs_started_at ON runs(started_at DESC);
CREATE INDEX idx_runs_result_status ON runs(result_status);
CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX idx_run_events_run_id ON run_events(run_id);
CREATE INDEX idx_run_events_category_code ON run_events(category, code);
CREATE INDEX idx_run_events_level ON run_events(level);

-- Update triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_postings_updated_at BEFORE UPDATE ON job_postings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
