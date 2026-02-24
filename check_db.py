from sqlalchemy import create_engine, inspect
DATABASE_URL = "postgresql://postgres:Rachael1806@localhost:5432/QMS-MD"
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables in database: {tables}")
if "projects" in tables:
    print("Project table exists.")
else:
    print("Project table MISSING!")
