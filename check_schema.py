from sqlalchemy import create_engine, inspect
DATABASE_URL = "postgresql://postgres:Rachael1806@localhost:5432/QMS-MD"
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
tables = ['requirements', 'testcases', 'testruns', 'defects', 'projects']
for table in tables:
    columns = [c['name'] for c in inspector.get_columns(table)]
    print(f"Table '{table}' columns: {columns}")
