
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:Rachael1806@localhost:5432/QMS-MD"
engine = create_engine(DATABASE_URL)

def migrate():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE testruns ADD COLUMN IF NOT EXISTS test_text VARCHAR;"))
            conn.commit()
            print("Migration successful: added test_text column to testruns table.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
