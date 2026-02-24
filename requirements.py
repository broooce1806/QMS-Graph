from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from database import get_session, SessionLocal
from pydantic import BaseModel
from models import ProjectDB, RequirementDB, TestCaseDB, TestRunDB, DefectDB
from sqlalchemy.orm import Session
import pandas as pd
import io
from typing import Optional
router = APIRouter(prefix="/requirements", tags=["Requirements"])

# Dependency to get Postgres session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    config: Optional[dict] = {"components": [], "types": [], "custom_fields": []}

class Requirement(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    type: str
    status: str
    version: str
    component: Optional[str] = None
    custom_data: Optional[dict] = {}

class RequirementLink(BaseModel):
    source_id: str
    target_id: str
    link_type: str  # DERIVES_FROM, IMPACTS, etc.

class RequirementTestLink(BaseModel):
    requirement_id: str
    testcase_id: str

class TestCase(BaseModel):
    id: str
    project_id: str
    title: str
    steps: str
    expected_result: str
    status: str
    custom_data: Optional[dict] = {}

class TestRun(BaseModel):
    id: str
    project_id: str
    date: str
    result: str  # Pass or Fail
    executed_by: str
    test_text: Optional[str] = "" # New field requested by user
    testcase_id: Optional[str] = None # Added for easier handling in creation

class Defect(BaseModel):
    id: str
    project_id: str
    title: str
    severity: str
    status: str

class DefectLink(BaseModel):
    testrun_id: str
    defect_id: str

class TestRunLink(BaseModel):
    testcase_id: str
    testrun_id: str

# --- PROJECT ENDPOINTS ---
@router.post("/projects")
def create_project(proj: Project, db: Session = Depends(get_db)):
    print(f"DEBUG: Creating project {proj.id}")
    try:
        db_proj = ProjectDB(**proj.dict())
        db.merge(db_proj)
        db.commit()
        print(f"DEBUG: Project {proj.id} created successfully")
        return {"message": "Project created"}
    except Exception as e:
        print(f"DEBUG: ERROR creating project: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects")
def get_projects(db: Session = Depends(get_db)):
    return db.query(ProjectDB).all()

@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    proj = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
    if not proj: raise HTTPException(status_code=404, detail="Project not found")
    return proj

@router.post("/")
def create_requirement(req: Requirement, db: Session = Depends(get_db)):
    print(f"DEBUG: Creating requirement {req.id} for project {req.project_id}")
    try:
        # 1. Store in Postgres
        db_req = RequirementDB(**req.dict())
        db.merge(db_req)
        db.commit()
        print(f"DEBUG: Postgres sync successful for {req.id}")

        # 2. Sync to Neo4j
        with get_session() as session:
            session.run("""
                MERGE (r:Requirement {id: $id})
                SET r.project_id = $project_id
            """, id=req.id, project_id=req.project_id)
        print(f"DEBUG: Neo4j sync successful for {req.id}")

        return {"message": "Requirement created"}
    except Exception as e:
        print(f"DEBUG: ERROR creating requirement: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_requirements(project_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(RequirementDB)
    if project_id:
        query = query.filter(RequirementDB.project_id == project_id)
    return query.all()

@router.post("/import/inspect")
async def inspect_excel(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        xl = pd.ExcelFile(io.BytesIO(contents))
        info = {}
        for sheet in xl.sheet_names:
            df = xl.parse(sheet, nrows=0)
            info[sheet] = [str(c) for c in df.columns]
        return {"sheets": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to inspect Excel: {e}")

@router.post("/import/mapped")
async def import_mapped_excel(
    file: UploadFile = File(...),
    sheet_name: str = Query(...),
    mapping: str = Query(...), # JSON string
    project_id: str = Query(...),
    table_type: str = Query("requirement"), # requirement, testcase, testrun
    db: Session = Depends(get_db)
):
    import json
    try:
        field_map = json.loads(mapping)
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet_name)
        
        imported_ids = []
        tc_links = []
        for _, row in df.iterrows():
            entity_id = str(row.get(field_map.get("id"))) if field_map.get("id") in row else None
            if not entity_id or pd.isna(entity_id): continue
            
            if table_type == "requirement":
                db.merge(RequirementDB(
                    id=entity_id,
                    project_id=project_id,
                    title=str(row.get(field_map.get("title"), "")),
                    description=str(row.get(field_map.get("description"), "")),
                    type=str(row.get(field_map.get("type"), "Functional")),
                    status=str(row.get(field_map.get("status"), "Proposed")),
                    version="1.0"
                ))
            elif table_type == "testcase":
                db.merge(TestCaseDB(
                    id=entity_id,
                    project_id=project_id,
                    title=str(row.get(field_map.get("title"), "")),
                    steps=str(row.get(field_map.get("steps"), "")),
                    expected_result=str(row.get(field_map.get("expected_result"), "")),
                    status=str(row.get(field_map.get("status"), "Draft"))
                ))
                # Link to Requirements
                req_val = row.get(field_map.get("requirement_id"))
                if req_val and pd.notna(req_val):
                    r_ids = [r.strip() for r in str(req_val).split(",") if r.strip()]
                    for r_id in r_ids:
                        tc_links.append({"tid": entity_id, "rid": r_id})

            elif table_type == "testrun":
                db.merge(TestRunDB(
                    id=entity_id,
                    project_id=project_id,
                    date=str(row.get(field_map.get("date"), "")),
                    result=str(row.get(field_map.get("result"), "Pass")),
                    executed_by=str(row.get(field_map.get("executed_by"), "Unknown"))
                ))
            
            imported_ids.append(entity_id)
        
        db.commit()
        
        # Sync to Neo4j
        with get_session() as session:
            if table_type == "requirement":
                session.run("UNWIND $ids AS rid MERGE (r:Requirement {id: rid}) SET r.project_id = $pid", ids=imported_ids, pid=project_id)
            elif table_type == "testcase":
                session.run("UNWIND $ids AS tid MERGE (t:TestCase {id: tid}) SET t.project_id = $pid", ids=imported_ids, pid=project_id)
                if tc_links:
                    session.run("""
                        UNWIND $links AS link 
                        MERGE (t:TestCase {id: link.tid})
                        MERGE (r:Requirement {id: link.rid})
                        MERGE (t)-[:VERIFIES]->(r)
                    """, links=tc_links)
            elif table_type == "testrun":
                session.run("UNWIND $ids AS rid MERGE (r:TestRun {id: rid}) SET r.project_id = $pid", ids=imported_ids, pid=project_id)
            
        return {"message": f"Successfully imported {len(imported_ids)} {table_type}s from {sheet_name}"}
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Mapped import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Mapped import failed: {e}")

@router.post("/import/excel")
async def import_requirements_excel(
    file: UploadFile = File(...), 
    table_type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    print(f"DEBUG: Starting Excel import. Type: {table_type}, Project: {project_id}")
    contents = await file.read()
    try:
        xl = pd.ExcelFile(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")

    # Helper to parse a sheet generically
    def get_df(sheet_name=None):
        if sheet_name and sheet_name in xl.sheet_names:
            return xl.parse(sheet_name)
        return xl.parse(xl.sheet_names[0]) # Default to first sheet if table_type is explicit

    # 1. PROCESS REQUIREMENTS
    if table_type == "requirement" or (not table_type and "Requirements" in xl.sheet_names):
        df_req = get_df("Requirements")
        df_req.columns = [c.strip().lower() for c in df_req.columns]
        req_ids = []
        for _, row in df_req.iterrows():
            rid = str(row["id"])
            req_ids.append(rid)
            db.merge(RequirementDB(
                id=rid,
                project_id=project_id,
                title=str(row.get("title", "")),
                description=str(row.get("description", "")),
                type=str(row.get("type", "Functional")),
                status=str(row.get("status", "Proposed")),
                version=str(row.get("version", "1.0"))
            ))
        db.commit()
        with get_session() as session:
            session.run("""
                UNWIND $ids AS rid 
                MERGE (r:Requirement {id: rid})
                SET r.project_id = $project_id
            """, ids=req_ids, project_id=project_id)

    # 2. PROCESS TEST CASES
    if table_type == "testcase" or (not table_type and "TestCases" in xl.sheet_names):
        df_tc = get_df("TestCases")
        df_tc.columns = [c.strip().lower() for c in df_tc.columns]
        tc_data = []
        links = []
        for _, row in df_tc.iterrows():
            tcid = str(row["id"])
            tc_data.append(tcid)
            db.merge(TestCaseDB(
                id=tcid,
                project_id=project_id,
                title=str(row.get("title", "")),
                steps=str(row.get("steps", "")),
                expected_result=str(row.get("expected_result", "")),
                status=str(row.get("status", "Draft"))
            ))
            if "requirement_id" in df_tc.columns and pd.notna(row["requirement_id"]):
                links.append({"req": str(row["requirement_id"]), "tc": tcid})
        db.commit()
        with get_session() as session:
            session.run("""
                UNWIND $ids AS tcid 
                MERGE (t:TestCase {id: tcid})
                SET t.project_id = $project_id
            """, ids=tc_data, project_id=project_id)
            if links:
                session.run("""
                    UNWIND $links AS link
                    MATCH (r:Requirement {id: link.req})
                    MATCH (t:TestCase {id: link.tc})
                    MERGE (r)-[:VERIFIED_BY]->(t)
                """, links=links)

    # 3. PROCESS TRACEABILITY
    if table_type == "traceability" or (not table_type and "Traceability" in xl.sheet_names):
        df_trace = get_df("Traceability")
        df_trace.columns = [c.strip().lower() for c in df_trace.columns]
        trace_links = []
        for _, row in df_trace.iterrows():
            if "source_id" in df_trace.columns and "target_id" in df_trace.columns:
                trace_links.append({"s": str(row["source_id"]), "t": str(row["target_id"])})
        if trace_links:
            with get_session() as session:
                session.run("""
                    UNWIND $links AS link
                    MATCH (src:Requirement {id: link.s})
                    MATCH (tgt:Requirement {id: link.t})
                    MERGE (src)-[:DERIVES_FROM]->(tgt)
                """, links=trace_links)

    # 4. PROCESS TEST RESULTS
    if table_type == "testrun" or (not table_type and "TestResults" in xl.sheet_names):
        df_res = get_df("TestResults")
        df_res.columns = [c.strip().lower() for c in df_res.columns]
        run_ids = []
        run_links = []
        defect_links = []
        for _, row in df_res.iterrows():
            run_id = str(row["id"])
            run_ids.append(run_id)
            db.merge(TestRunDB(
                id=run_id,
                project_id=project_id,
                date=str(row.get("date", "")),
                result=str(row.get("result", "Pass")),
                executed_by=str(row.get("executed_by", "Unknown"))
            ))
            if "testcase_id" in df_res.columns and pd.notna(row["testcase_id"]):
                run_links.append({"tc": str(row["testcase_id"]), "tr": run_id})
            
            if "defect_id" in df_res.columns and pd.notna(row["defect_id"]):
                def_id = str(row["defect_id"])
                # Create defect in Postgres if not exists
                db.merge(DefectDB(id=def_id, project_id=project_id, title=f"Auto-generated for {run_id}", status="Open", severity="Medium"))
                defect_links.append({"tr": run_id, "def": def_id})
        
        db.commit()
        with get_session() as session:
            session.run("""
                UNWIND $ids AS trid 
                MERGE (tr:TestRun {id: trid})
                SET tr.project_id = $project_id
            """, ids=run_ids, project_id=project_id)
            if defect_links:
                def_ids = [d["def"] for d in defect_links]
                session.run("UNWIND $ids AS did MERGE (d:Defect {id: did}) SET d.project_id = $project_id", ids=list(set(def_ids)), project_id=project_id)
                session.run("""
                    UNWIND $links AS link
                    MATCH (tr:TestRun {id: link.tr})
                    MATCH (d:Defect {id: link.def})
                    MERGE (tr)-[:HAS_DEFECT]->(d)
                """, links=defect_links)
            if run_links:
                session.run("""
                    UNWIND $links AS link
                    MATCH (tc:TestCase {id: link.tc})
                    MATCH (tr:TestRun {id: link.tr})
                    MERGE (tc)-[:HAS_TEST_RUN]->(tr)
                """, links=run_links)

    return {"message": f"Import for {table_type or 'all sheets'} completed successfully"}


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
def downstream_trace(req_id: str, db: Session = Depends(get_db)):
    with get_session() as session:
        result = session.run("""
            MATCH (r:Requirement {id: $req_id})-[:DERIVES_FROM*]->(downstream)
            RETURN downstream.id AS id
        """, req_id=req_id)
        ids = [record["id"] for record in result]
    
    return db.query(RequirementDB).filter(RequirementDB.id.in_(ids)).all()

@router.get("/trace/upstream/{req_id}")
def upstream_trace(req_id: str, db: Session = Depends(get_db)):
    with get_session() as session:
        result = session.run("""
            MATCH (upstream)-[:DERIVES_FROM*]->(r:Requirement {id: $req_id})
            RETURN upstream.id AS id
        """, req_id=req_id)
        ids = [record["id"] for record in result]

    return db.query(RequirementDB).filter(RequirementDB.id.in_(ids)).all()


@router.post("/testcases")
def create_testcase(tc: TestCase, db: Session = Depends(get_db)):
    try:
        # 1. Store in Postgres - filter for model columns
        tc_data = {k: v for k, v in tc.dict().items() if k in TestCaseDB.__table__.columns.keys()}
        db_tc = TestCaseDB(**tc_data)
        db.merge(db_tc)
        db.commit()

        # 2. Sync to Neo4j
        with get_session() as session:
            session.run("""
                MERGE (t:TestCase {id: $id})
                SET t.project_id = $project_id
            """, id=tc.id, project_id=tc.project_id)
            
            # Link to Requirements
            req_id = tc.custom_data.get("requirement_id") or tc.dict().get("requirement_id")
            if req_id:
                r_ids = [r.strip() for r in str(req_id).split(",") if r.strip()]
                for r_id in r_ids:
                    session.run("""
                        MATCH (t:TestCase {id: $t_id})
                        MATCH (r:Requirement {id: $r_id})
                        MERGE (t)-[:VERIFIES]->(r)
                    """, t_id=tc.id, r_id=r_id)

        return {"message": "Test case updated/created"}
    except Exception as e:
        print(f"Error creating testcase: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/testruns")
def create_testrun(tr: TestRun, db: Session = Depends(get_db)):
    try:
        # 1. Store in Postgres - filter for model columns
        tr_data = {k: v for k, v in tr.dict().items() if k in TestRunDB.__table__.columns.keys()}
        db_tr = TestRunDB(**tr_data)
        db.merge(db_tr)
        db.commit()

        # 2. Sync to Neo4j
        with get_session() as session:
            session.run("""
                MERGE (t:TestRun {id: $id})
                SET t.project_id = $project_id
            """, id=tr.id, project_id=tr.project_id)
            
            # Link to TestCase
            # We check common fields in payload
            tc_id = tr.dict().get("testcase_id")
            if tc_id:
                session.run("""
                    MATCH (tr:TestRun {id: $tr_id})
                    MATCH (tc:TestCase {id: $tc_id})
                    MERGE (tc)-[:HAS_TEST_RUN]->(tr)
                """, tr_id=tr.id, tc_id=tc_id)
                
        return {"message": "Test run updated/created"}
    except Exception as e:
        print(f"Error creating testrun: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/defects")
def create_defect(defect: Defect, db: Session = Depends(get_db)):
    # 1. Store in Postgres
    db_defect = DefectDB(**defect.dict())
    db.merge(db_defect)
    db.commit()

    # 2. Sync to Neo4j
    with get_session() as session:
        session.run("""
            MERGE (d:Defect {id: $id})
        """, id=defect.id)
    return {"message": "Defect created"}



@router.post("/link-defect")
def link_defect(link: DefectLink):
    with get_session() as session:
        session.run("""
            MATCH (tr:TestRun {id: $testrun_id})
            MATCH (d:Defect {id: $defect_id})
            MERGE (tr)-[:HAS_DEFECT]->(d)
        """, testrun_id=link.testrun_id, defect_id=link.defect_id)

    return {"message": "Defect linked to TestRun"}

@router.get("/risk-requirements")
def risk_requirements(db: Session = Depends(get_db)):
    # 1. Get IDs of all open defects from Postgres
    open_defect_ids = [d.id for d in db.query(DefectDB).filter(DefectDB.status == "Open").all()]
    
    if not open_defect_ids:
        return {"risky_requirements": []}

    # 2. Trace in Neo4j
    with get_session() as session:
        result = session.run("""
            MATCH (r:Requirement)-[:VERIFIED_BY]->(tc:TestCase)
            MATCH (tc)-[:HAS_TEST_RUN]->(tr:TestRun)
            MATCH (tr)-[:HAS_DEFECT]->(d:Defect)
            WHERE d.id IN $defect_ids
            RETURN DISTINCT r.id AS requirement_id
        """, defect_ids=open_defect_ids)

        risky = [record["requirement_id"] for record in result]

    return {"risky_requirements": risky}

@router.get("/dashboard/list")
def get_requirements_dashboard(project_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    # 1. Get from Postgres
    query = db.query(RequirementDB)
    if project_id:
        query = query.filter(RequirementDB.project_id == project_id)
    reqs = query.all()
    
    # 2. Get status from Neo4j (scoped by project)
    with get_session() as session:
        cypher = """
            MATCH (r:Requirement)
            WHERE ($project_id IS NULL OR r.project_id = $project_id)
            OPTIONAL MATCH (r)-[:VERIFIED_BY]->(tc:TestCase)
            OPTIONAL MATCH (tc)-[:HAS_TEST_RUN]->(tr:TestRun)
            RETURN r.id AS rid, 
                   count(tc) AS tc_count,
                   collect(tr.id) AS run_ids
        """
        result = session.run(cypher, project_id=project_id)
        
        status_map = {}
        for record in result:
            rid = record["rid"]
            tc_count = record["tc_count"]
            run_ids = record["run_ids"]
            
            if tc_count == 0:
                status_map[rid] = "Not Covered"
            elif not run_ids:
                status_map[rid] = "Covered (No Runs)"
            else:
                runs = db.query(TestRunDB).filter(TestRunDB.id.in_(run_ids)).all()
                if any(run.result == "Fail" for run in runs):
                    status_map[rid] = "Failing"
                elif all(run.result == "Pass" for run in runs):
                    status_map[rid] = "Passing"
                else:
                    status_map[rid] = "Mixed"

    dashboard_data = []
    for r in reqs:
        dashboard_data.append({
            "id": r.id,
            "project_id": r.project_id,
            "title": r.title,
            "description": r.description,
            "type": r.type,
            "status": r.status,
            "version": r.version,
            "component": r.component,
            "custom_data": r.custom_data,
            "fulfillment": status_map.get(r.id, "Unknown")
        })
    return dashboard_data

@router.get("/testcases/dashboard/list")
def get_testcases_dashboard(project_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    # ... (existing logic)
    query = db.query(TestCaseDB)
    if project_id:
        query = query.filter(TestCaseDB.project_id == project_id)
    tcs = query.all()
    
    with get_session() as session:
        result = session.run("""
            MATCH (t:TestCase)
            WHERE ($project_id IS NULL OR t.project_id = $project_id)
            OPTIONAL MATCH (r:Requirement)-[:VERIFIES]-(t)
            OPTIONAL MATCH (t)-[:HAS_TEST_RUN]->(tr:TestRun)
            OPTIONAL MATCH (tr)-[:HAS_DEFECT]->(d:Defect)
            RETURN t.id AS tcid, 
                   r.id AS req_id,
                   tr.id AS last_run_id,
                   tr.result AS last_result,
                   d.id AS defect_id
            ORDER BY tr.date DESC
        """, project_id=project_id)
        
        tc_meta = {}
        for record in result:
            tcid = record["tcid"]
            if tcid not in tc_meta: 
                tc_meta[tcid] = {
                    "req_id": record["req_id"],
                    "last_result": record["last_result"],
                    "defect_id": record["defect_id"]
                }
    
    data = []
    for tc in tcs:
        meta = tc_meta.get(tc.id, {})
        data.append({
            "id": tc.id,
            "title": tc.title,
            "requirement_id": meta.get("req_id"),
            "last_result": meta.get("last_result") or "N/A",
            "defect_id": meta.get("defect_id") or "None"
        })
    return data

@router.get("/testruns/dashboard/list")
def get_testruns_dashboard(project_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(TestRunDB)
    if project_id:
        query = query.filter(TestRunDB.project_id == project_id)
    runs = query.all()
    
    # Enrich with Test Case info from Neo4j
    with get_session() as session:
        result = session.run("""
            MATCH (tr:TestRun)
            WHERE ($project_id IS NULL OR tr.project_id = $project_id)
            OPTIONAL MATCH (tc:TestCase)-[:HAS_TEST_RUN]->(tr)
            RETURN tr.id AS trid, tc.id AS tcid, tc.title AS tc_title
        """, project_id=project_id)
        
        tr_meta = {record["trid"]: {"tcid": record["tcid"], "title": record["tc_title"]} for record in result}
    
    data = []
    for r in runs:
        meta = tr_meta.get(r.id, {})
        data.append({
            "id": r.id,
            "date": r.date,
            "result": r.result,
            "executed_by": r.executed_by,
            "test_text": r.test_text, # Include in dashboard
            "testcase_id": meta.get("tcid"),
            "testcase_title": meta.get("title")
        })
    return data

@router.get("/full-graph/{req_id}")
def full_graph_v1(req_id: str, db: Session = Depends(get_db)):
    print(f"DEBUG: Generating graph for ID={req_id}")
    with get_session() as session:
        # 1. Find the starting node and all nodes reachable via any path (undirected)
        # We limit depth to 5 to avoid performance death on huge graphs, 
        # but 5 is usually plenty for ALM traceability (Req->TC->Run->Defect is 3-4 deep)
        result = session.run("""
            MATCH (r {id: $req_id})
            OPTIONAL MATCH path = (r)-[*..5]-(n)
            RETURN r.id AS root_id, collect(DISTINCT n) AS connected_nodes, collect(DISTINCT path) AS paths
        """, req_id=req_id).single()

        if not result or not result["root_id"]:
            print(f"DEBUG: Root ID {req_id} not found in Neo4j")
            return {"nodes": [], "edges": []}

        node_ids = {result["root_id"]}
        if result["connected_nodes"]:
            for node in result["connected_nodes"]:
                if node and "id" in node:
                    node_ids.add(node["id"])

        edges = set()
        if result["paths"]:
            for path in result["paths"]:
                if not path: continue
                for rel in path.relationships:
                    edges.add((rel.start_node["id"], rel.end_node["id"], rel.type))

        print(f"DEBUG: Found {len(node_ids)} nodes and {len(edges)} edges")

        # 2. Bulk fetch full objects from Postgres
        # We query all tables because we don't know the type of 'n' yet
        req_objs = {r.id: r for r in db.query(RequirementDB).filter(RequirementDB.id.in_(list(node_ids))).all()}
        tc_objs = {t.id: t for t in db.query(TestCaseDB).filter(TestCaseDB.id.in_(list(node_ids))).all()}
        tr_objs = {tr.id: tr for tr in db.query(TestRunDB).filter(TestRunDB.id.in_(list(node_ids))).all()}
        def_objs = {d.id: d for d in db.query(DefectDB).filter(DefectDB.id.in_(list(node_ids))).all()}
        
        all_metadata = {**req_objs, **tc_objs, **tr_objs, **def_objs}

        nodes_list = []
        for nid in node_ids:
            obj = all_metadata.get(nid)
            # Determine type for styling
            node_type = "Unknown"
            if nid in req_objs: node_type = "Requirement"
            elif nid in tc_objs: node_type = "TestCase"
            elif nid in tr_objs: node_type = "TestRun"
            elif nid in def_objs: node_type = "Defect"

            label = nid
            if obj:
                if hasattr(obj, 'title') and obj.title: label = obj.title
                elif hasattr(obj, 'date') and obj.date: label = f"Run: {obj.date}"

            nodes_list.append({
                "id": nid,
                "label": label,
                "type": node_type,
                "metadata": {k: v for k, v in obj.__dict__.items() if not k.startswith('_')} if obj else {"id": nid}
            })

        return {
            "nodes": nodes_list,
            "edges": [
                {"source": s, "target": t, "type": ty} 
                for s, t, ty in edges
            ]
        }
@router.get("/graph/{req_id}")
def full_graph_v2(req_id: str, db: Session = Depends(get_db)):
    with get_session() as session:
        result = session.run("""
            MATCH (r:Requirement {id: $req_id})
            OPTIONAL MATCH (r)-[:DERIVES_FROM*]->(child)
            OPTIONAL MATCH (r)-[:VERIFIED_BY]->(tc:TestCase)
            OPTIONAL MATCH (tc)-[:HAS_TEST_RUN]->(tr:TestRun)
            OPTIONAL MATCH (tr)-[:HAS_DEFECT]->(d:Defect)
            RETURN r.id AS r_id, child.id AS child_id, tc.id AS tc_id, tr.id AS tr_id, d.id AS d_id
        """, req_id=req_id)

        ids = set()
        data_rows = []
        for record in result:
            row = {k: record[k] for k in record.keys()}
            data_rows.append(row)
            for val in row.values():
                if val: ids.add(val)

        # Bulk fetch metadata
        reqs = {r.id: r for r in db.query(RequirementDB).filter(RequirementDB.id.in_(list(ids))).all()}
        tcs = {t.id: t for t in db.query(TestCaseDB).filter(TestCaseDB.id.in_(list(ids))).all()}
        trs = {tr.id: tr for tr in db.query(TestRunDB).filter(TestRunDB.id.in_(list(ids))).all()}
        defects = {d.id: d for d in db.query(DefectDB).filter(DefectDB.id.in_(list(ids))).all()}

        enriched_data = []
        for row in data_rows:
            enriched_data.append({
                "requirement": reqs.get(row["r_id"]),
                "child": reqs.get(row["child_id"]),
                "testcase": tcs.get(row["tc_id"]),
                "testrun": trs.get(row["tr_id"]),
                "defect": defects.get(row["d_id"])
            })

    return enriched_data