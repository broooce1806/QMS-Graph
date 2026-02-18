from fastapi import APIRouter
from database import get_session
from pydantic import BaseModel

router = APIRouter(prefix="/requirements", tags=["Requirements"])

class Requirement(BaseModel):
    id: str
    title: str
    description: str
    type: str
    status: str
    version: str

@router.post("/")
def create_requirement(req: Requirement):
    with get_session() as session:
        session.run("""
            CREATE (r:Requirement {
                id: $id,
                title: $title,
                description: $description,
                type: $type,
                status: $status,
                version: $version
            })
        """, **req.dict())
    return {"message": "Requirement created"}

@router.get("/")
def get_requirements():
    with get_session() as session:
        result = session.run("MATCH (r:Requirement) RETURN r")
        requirements = [record["r"] for record in result]
    return requirements

class RequirementLink(BaseModel):
    source_id: str
    target_id: str
    link_type: str  # DERIVES_FROM, IMPACTS, etc.

class RequirementTestLink(BaseModel):
    requirement_id: str
    testcase_id: str


@router.post("/link")
def link_requirements(link: RequirementLink):
    with get_session() as session:
        session.run(f"""
            MATCH (a:Requirement {{id: $source_id}})
            MATCH (b:Requirement {{id: $target_id}})
            MERGE (a)-[r:{link.link_type}]->(b)
        """, source_id=link.source_id, target_id=link.target_id)

    return {"message": "Requirements linked"}

@router.get("/trace/downstream/{req_id}")
def downstream_trace(req_id: str):
    with get_session() as session:
        result = session.run("""
            MATCH (r:Requirement {id: $req_id})-[:DERIVES_FROM*]->(downstream)
            RETURN downstream
        """, req_id=req_id)

        nodes = [record["downstream"] for record in result]

    return nodes

@router.get("/trace/upstream/{req_id}")
def upstream_trace(req_id: str):
    with get_session() as session:
        result = session.run("""
            MATCH (upstream)-[:DERIVES_FROM*]->(r:Requirement {id: $req_id})
            RETURN upstream
        """, req_id=req_id)

        nodes = [record["upstream"] for record in result]

    return nodes

class TestCase(BaseModel):
    id: str
    title: str
    steps: str
    expected_result: str
    status: str

@router.post("/testcases")
def create_testcase(tc: TestCase):
    with get_session() as session:
        session.run("""
            CREATE (t:TestCase {
                id: $id,
                title: $title,
                steps: $steps,
                expected_result: $expected_result,
                status: $status
            })
        """, **tc.dict())
    return {"message": "Test case created"}

@router.post("/link-testcase")
def link_requirement_testcase(link: RequirementTestLink):
    with get_session() as session:
        session.run("""
            MATCH (r:Requirement {id: $requirement_id})
            MATCH (t:TestCase {id: $testcase_id})
            MERGE (r)-[:VERIFIED_BY]->(t)
        """, requirement_id=link.requirement_id, testcase_id=link.testcase_id)

    return {"message": "Requirement linked to Test Case"}

@router.get("/coverage")
def coverage_analysis():
    with get_session() as session:
        result = session.run("""
            MATCH (r:Requirement)
            OPTIONAL MATCH (r)-[:VERIFIED_BY]->(t:TestCase)
            RETURN r.id AS requirement_id, COUNT(t) AS testcase_count
        """)

        coverage = []
        for record in result:
            coverage.append({
                "requirement_id": record["requirement_id"],
                "testcase_count": record["testcase_count"],
                "covered": record["testcase_count"] > 0
            })

    return coverage

@router.get("/impact-matrix")
def impact_matrix():
    with get_session() as session:
        result = session.run("""
            MATCH (r:Requirement)-[:VERIFIED_BY]->(t:TestCase)
            RETURN r.id AS requirement, t.id AS testcase
        """)

        matrix = []
        for record in result:
            matrix.append({
                "requirement": record["requirement"],
                "testcase": record["testcase"]
            })

    return matrix
