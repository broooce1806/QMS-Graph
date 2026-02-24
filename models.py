from sqlalchemy import Column, String, Date, JSON, Text
from database import Base

class ProjectDB(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    config = Column(JSON) # { components: [], types: [], custom_fields: [] }

class RequirementDB(Base):
    __tablename__ = "requirements"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True)
    title = Column(String)
    description = Column(String)
    type = Column(String)
    status = Column(String)
    version = Column(String)
    component = Column(String)
    custom_data = Column(JSON) # { field_id: value }

class TestCaseDB(Base):
    __tablename__ = "testcases"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True)
    title = Column(String)
    steps = Column(String)
    expected_result = Column(String)
    status = Column(String)
    custom_data = Column(JSON)

class TestRunDB(Base):
    __tablename__ = "testruns"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True)
    date = Column(String)
    result = Column(String)
    executed_by = Column(String)
    test_text = Column(String) # For the "text" field requested by user

class DefectDB(Base):
    __tablename__ = "defects"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True)
    title = Column(String)
    severity = Column(String)
    status = Column(String)
