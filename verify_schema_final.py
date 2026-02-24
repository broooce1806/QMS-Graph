from sqlalchemy import create_engine, inspect
DATABASE_URL = "postgresql://postgres:Rachael1806@localhost:5432/QMS-MD"
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
columns = [c['name'] for c in inspector.get_columns('requirements')]
print(f"Columns in 'requirements': {columns}")
missing = [col for col in ['id', 'project_id', 'title', 'description', 'type', 'status', 'version', 'component', 'custom_data'] if col not in columns]
if not missing:
    print("Schema is PERFECT!")
else:
    print(f"STILL MISSING: {missing}")
