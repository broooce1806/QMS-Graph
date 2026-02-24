from sqlalchemy import create_engine, text
DATABASE_URL = "postgresql://postgres:Rachael1806@localhost:5432/QMS-MD"
engine = create_engine(DATABASE_URL)

migrations = [
    # Requirements
    "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS project_id VARCHAR;",
    "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS status VARCHAR;",
    "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS version VARCHAR;",
    "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS component VARCHAR;",
    "ALTER TABLE requirements ADD COLUMN IF NOT EXISTS custom_data JSONB DEFAULT '{}';",
    
    # TestCases
    "ALTER TABLE testcases ADD COLUMN IF NOT EXISTS project_id VARCHAR;",
    "ALTER TABLE testcases ADD COLUMN IF NOT EXISTS status VARCHAR;",
    "ALTER TABLE testcases ADD COLUMN IF NOT EXISTS custom_data JSONB DEFAULT '{}';",
    
    # TestRuns
    "ALTER TABLE testruns ADD COLUMN IF NOT EXISTS project_id VARCHAR;",
    "ALTER TABLE testruns ADD COLUMN IF NOT EXISTS custom_data JSONB DEFAULT '{}';",
    
    # Defects
    "ALTER TABLE defects ADD COLUMN IF NOT EXISTS project_id VARCHAR;",
    "ALTER TABLE defects ADD COLUMN IF NOT EXISTS custom_data JSONB DEFAULT '{}';",
]

with engine.connect() as conn:
    for stmt in migrations:
        try:
            conn.execute(text(stmt))
            conn.commit()
            print(f"Executed: {stmt}")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

print("Schema alignment complete.")
