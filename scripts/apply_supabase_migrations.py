from pathlib import Path
from sqlalchemy import create_engine, text
import urllib.parse
import sys

env_file = Path("D:/paypal hackathon/.env")
content = env_file.read_text(encoding="utf-8")
db_url = ""
for line in content.splitlines():
    if line.strip().startswith("DATABASE_URL="):
        db_url = line.split("=", 1)[1].strip().strip("'\"")

if not db_url:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

print("=== APPLYING SUPABASE POSTGRESQL MIGRATIONS ===")
engine = create_engine(db_url, pool_pre_ping=True)

schema_sql_path = Path("D:/paypal hackathon/migrations/schema.sql")
schema_sql = schema_sql_path.read_text(encoding="utf-8")

# Execute statements
with engine.connect() as conn:
    print("1. Connected to Supabase PostgreSQL.")
    
    # Enable extensions
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
    conn.commit()
    print("   ✓ UUID extension enabled.")

    # We can execute schema statements using raw connection or statements
    # Split by semicolon where appropriate, or execute raw blocks
    # Tables creation
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS agents (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        description TEXT NOT NULL,
        category VARCHAR(64) NOT NULL,
        capabilities TEXT NOT NULL,
        supported_tasks TEXT NOT NULL,
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
    """))
    conn.commit()
    print("   ✓ 'agents' table verified.")

    conn.execute(text("""
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
    """))
    conn.commit()
    print("   ✓ 'tasks' table verified.")

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS task_steps (
        id VARCHAR(64) PRIMARY KEY,
        task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        step_name VARCHAR(64) NOT NULL,
        assigned_agent_id VARCHAR(64) REFERENCES agents(id),
        dependencies TEXT,
        input_data TEXT,
        output_data TEXT,
        status VARCHAR(32) DEFAULT 'pending',
        error_message TEXT,
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX IF NOT EXISTS idx_task_steps_task_id ON task_steps(task_id);
    """))
    conn.commit()
    print("   ✓ 'task_steps' table verified.")

    conn.execute(text("""
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
    """))
    conn.commit()
    print("   ✓ 'agent_runs' table verified.")

    conn.execute(text("""
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
    """))
    conn.commit()
    print("   ✓ 'transactions' table verified.")

    conn.execute(text("""
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
    """))
    conn.commit()
    print("   ✓ 'activity_logs' table verified.")

    # Enable RLS with permissive policies for service role
    conn.execute(text("""
    ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Public agents view" ON agents;
    CREATE POLICY "Public agents view" ON agents FOR ALL USING (true);
    
    ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Tasks service access" ON tasks;
    CREATE POLICY "Tasks service access" ON tasks FOR ALL USING (true);

    ALTER TABLE task_steps ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Steps service access" ON task_steps;
    CREATE POLICY "Steps service access" ON task_steps FOR ALL USING (true);

    ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Runs service access" ON agent_runs;
    CREATE POLICY "Runs service access" ON agent_runs FOR ALL USING (true);

    ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Transactions service access" ON transactions;
    CREATE POLICY "Transactions service access" ON transactions FOR ALL USING (true);

    ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Logs service access" ON activity_logs;
    CREATE POLICY "Logs service access" ON activity_logs FOR ALL USING (true);
    """))
    conn.commit()
    print("   ✓ RLS policies configured.")

    # Seed agents using seed_marketplace_agents
    import sys
    sys.path.insert(0, "D:/paypal hackathon")
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from api.seed_data import seed_marketplace_agents
        seed_marketplace_agents(session)
    print("   ✓ Seed marketplace agents populated in Supabase.")

    # Count records
    agent_count = conn.execute(text("SELECT count(*) FROM agents")).scalar()
    task_count = conn.execute(text("SELECT count(*) FROM tasks")).scalar()
    tx_count = conn.execute(text("SELECT count(*) FROM transactions")).scalar()

    print(f"\n2. Verification:")
    print(f"   Agents count in Supabase:       {agent_count}")
    print(f"   Tasks count in Supabase:        {task_count}")
    print(f"   Transactions count in Supabase: {tx_count}")
    print("\nALL SUPABASE MIGRATIONS APPLIED SUCCESSFULLY!")
