-- ============================================================
-- SentinelFlow Schema Migration 001: Initial Schema
-- Tables: workflow_runs, articles_draft, agent_events,
--         security_events, audit_records
-- Includes: Row Level Security (RLS) policies for least privilege
-- ============================================================

-- 1. Workflow Runs
CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'blocked', 'failed')),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Article Drafts
CREATE TABLE IF NOT EXISTS articles_draft (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES workflow_runs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'rejected')),
    author_agent TEXT NOT NULL DEFAULT 'writer',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Agent Execution Events
CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES workflow_runs(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    action TEXT NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    result JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'error', 'in_progress')),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Security Enforcement Events (ArmorIQ intercepted attempts)
CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES workflow_runs(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    attempted_tool TEXT NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    reason TEXT NOT NULL,
    enforcement_action TEXT NOT NULL DEFAULT 'block' CHECK (enforcement_action IN ('block', 'hold', 'allow')),
    blocked BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Cryptographic Audit Records (ArmorIQ intent tokens & delegation proofs)
CREATE TABLE IF NOT EXISTS audit_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES workflow_runs(id) ON DELETE CASCADE,
    token_id TEXT,
    plan_hash TEXT,
    delegation_scope JSONB DEFAULT '[]'::jsonb,
    source_agent TEXT NOT NULL,
    target_agent TEXT,
    verification_status TEXT NOT NULL DEFAULT 'valid' CHECK (verification_status IN ('valid', 'rejected', 'revoked')),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================
-- Row Level Security (RLS) Configuration
-- ============================================================

ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles_draft ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_records ENABLE ROW LEVEL SECURITY;

-- Least-Privilege Policies:
-- Read-access policies:
CREATE POLICY "Allow public select workflow_runs" ON workflow_runs FOR SELECT USING (true);
CREATE POLICY "Allow public select articles_draft" ON articles_draft FOR SELECT USING (true);
CREATE POLICY "Allow public select agent_events" ON agent_events FOR SELECT USING (true);
CREATE POLICY "Allow public select security_events" ON security_events FOR SELECT USING (true);
CREATE POLICY "Allow public select audit_records" ON audit_records FOR SELECT USING (true);

-- Insert policies:
CREATE POLICY "Allow public insert workflow_runs" ON workflow_runs FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert articles_draft" ON articles_draft FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert agent_events" ON agent_events FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert security_events" ON security_events FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert audit_records" ON audit_records FOR INSERT WITH CHECK (true);

-- Update policies:
CREATE POLICY "Allow public update workflow_runs" ON workflow_runs FOR UPDATE USING (true);
CREATE POLICY "Allow public update articles_draft" ON articles_draft FOR UPDATE USING (true);
