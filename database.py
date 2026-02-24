from neo4j import GraphDatabase
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
URI = "bolt://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = "Traunstein@1806"

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD),
    encrypted=False
)

def get_session():
    return driver.session()

DATABASE_URL = "postgresql://postgres:Rachael1806@localhost:5432/QMS-MD"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from models import ProjectDB, RequirementDB, TestCaseDB, TestRunDB, DefectDB
    Base.metadata.create_all(bind=engine)
