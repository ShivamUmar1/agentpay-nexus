-- AgentPay Nexus - Production Database Schema (Supabase / PostgreSQL)
-- Multi-Agent Marketplace & PayPal Settlement Platform

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table (aligned with Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- 2. Agents Table (Marketplace Catalog)
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,
    capabilities TEXT NOT NULL, -- JSON serialized array
    supported_tasks TEXT NOT NULL, -- JSON serialized array
    pricing_model VARCHAR(32) DEFAULT 'fixed_per_task',
    price NUMERIC(10, 2) DEFAULT 0.00,
    currency VARCHAR(8) DEFAULT 'USD',
    availability VARCHAR(32) DEFAULT 'available',
    rating NUMERIC(3, 2) DEFAULT 5.00,
    completed_tasks INTEGER DEFAULT 0,
    icon VARCHAR(64) DEFAULT 'Bot',
    estimated_time VARCHAR(64) DEFAULT '1-2 min',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_agents_category ON agents(category);
CREATE INDEX IF NOT EXISTS idx_agents_rating ON agents(rating DESC);

-- 3. Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    budget NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(8) DEFAULT 'USD',
    status VARCHAR(32) DEFAULT 'planning',
    current_step VARCHAR(64) DEFAULT 'planning',
    execution_plan TEXT,
    final_output TEXT,
    total_cost NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- 4. Task Steps Table (Stateful Graph Workflow Nodes)
CREATE TABLE IF NOT EXISTS task_steps (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_name VARCHAR(64) NOT NULL,
    assigned_agent_id VARCHAR(64) REFERENCES agents(id),
    dependencies TEXT, -- JSON array of dependent step names
    input_data TEXT,
    output_data TEXT,
    status VARCHAR(32) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_task_steps_task_id ON task_steps(task_id);

-- 5. Agent Runs Table (Audit Trail)
CREATE TABLE IF NOT EXISTS agent_runs (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(id),
    status VARCHAR(32) DEFAULT 'running',
    input_data TEXT,
    output_data TEXT,
    execution_metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_task ON agent_runs(task_id);

-- 6. Transactions Table (PayPal Settlement & Invoices)
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    paypal_order_id VARCHAR(128),
    paypal_capture_id VARCHAR(128),
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(8) DEFAULT 'USD',
    payment_status VARCHAR(32) DEFAULT 'pending',
    provider VARCHAR(32) DEFAULT 'paypal_sandbox',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_transactions_task ON transactions(task_id);
CREATE INDEX IF NOT EXISTS idx_transactions_order ON transactions(paypal_order_id);

-- 7. Activity Logs Table (Real-Time Observability)
CREATE TABLE IF NOT EXISTS activity_logs (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id VARCHAR(64),
    event_type VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_task ON activity_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- Allow public read of agents marketplace
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public agents view" ON agents FOR SELECT USING (true);

-- Seed Initial Specialized Agents
INSERT INTO agents (id, name, description, category, capabilities, supported_tasks, pricing_model, price, currency, availability, rating, completed_tasks, icon, estimated_time)
VALUES
('agent_orchestrator_00', 'Nexus Orchestrator', 'Master coordination agent that analyzes high-level user objectives, crafts optimal multi-agent execution graphs, and manages end-to-end task lifecycles.', 'Orchestration', '["Task Decomposition", "Multi-Agent Workflow Planning", "Dependency Resolution"]', '["market_research", "strategic_planning"]', 'internal', 0.00, 'USD', 'available', 5.00, 312, 'Cpu', 'Instant'),
('agent_research_01', 'Deep Research Agent', 'Autonomous market research specialist. Gathers authoritative domain data, industry statistics, market sizing, growth drivers, and competitor footprints.', 'Research', '["Industry Market Sizing", "Competitor Intelligence Gathering", "Regulatory Analysis"]', '["market_research", "competitor_scan"]', 'fixed_per_task', 2.00, 'USD', 'available', 4.95, 248, 'Search', '30-45s'),
('agent_analysis_02', 'Quantitative Data Analysis Agent', 'Deterministic quantitative analysis engine. Computes CAGR, market shares, financial metrics, valuation multiples, and formats structured chart-ready datasets.', 'Analytics', '["CAGR Projection Modeling", "Market Share Breakdown", "Chart-Ready Structuring"]', '["financial_modeling", "cagr_computation"]', 'fixed_per_task', 3.00, 'USD', 'available', 4.98, 194, 'BarChart3', '20-30s'),
('agent_content_03', 'Executive Content Synthesis Agent', 'Expert business report author. Transforms raw data and quantitative findings into polished, publication-grade executive briefings and markdown dossiers.', 'Content', '["Executive Summary Generation", "Markdown Reporting", "Strategic Recommendations"]', '["executive_briefing", "research_report"]', 'fixed_per_task', 2.00, 'USD', 'available', 4.92, 281, 'FileText', '25-35s'),
('agent_qa_04', 'Quality Assurance & Fact Auditor', 'Rigorous verification agent. Audits deliverable completeness against original user constraints, detects inconsistencies, and issues audit sign-offs.', 'Verification', '["Constraint Compliance", "Fact Grounding", "Completeness Scoring"]', '["deliverable_audit", "consistency_check"]', 'fixed_per_task', 1.00, 'USD', 'available', 4.97, 320, 'CheckCircle2', '15-20s'),
('agent_finance_05', 'Marketplace Finance Agent', 'Trusted ledger & budget controller. Calculates itemized marketplace service costs from immutable database records, checks budget thresholds, and prepares formal invoices.', 'Financial Management', '["Ledger Cost Aggregation", "Budget Enforcement", "Invoice Generation"]', '["invoice_generation", "budget_check"]', 'internal', 0.00, 'USD', 'available', 5.00, 410, 'DollarSign', 'Instant'),
('agent_payment_06', 'PayPal Settlement Agent', 'Secure payment bridge agent. Interfaces with official PayPal Orders v2 APIs, verifies user authorization, creates and captures PayPal Sandbox orders.', 'Payment Management', '["PayPal REST API v2 Handshake", "Capture Verification", "Receipt Emission"]', '["paypal_order_creation", "paypal_capture"]', 'internal', 0.00, 'USD', 'available', 5.00, 389, 'CreditCard', 'Instant')
ON CONFLICT (id) DO UPDATE SET
name = EXCLUDED.name,
description = EXCLUDED.description,
price = EXCLUDED.price;
