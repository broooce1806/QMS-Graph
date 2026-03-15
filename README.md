# QMS-Graph — Requirements Graph Backend

A **Quality Management System** backend that models requirements, test cases, test runs, defects, and system architecture blocks as a **graph** using **Neo4j**, with relational storage in **PostgreSQL**. Built with **FastAPI** (Python).

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  React UI   │────▶│  FastAPI API  │────▶│   Neo4j     │
│ (Frontend)  │     │  (This Repo)  │     │  (Graph DB) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  PostgreSQL  │
                    │ (Relational) │
                    └──────────────┘
```

- **Neo4j** stores the traceability graph — relationships between requirements, test cases, runs, defects, and architecture blocks using SysML stereotypes (`«satisfy»`, `«derive»`, `«verify»`, `«allocate»`, `«refine»`, `«trace»`, `«compose»`).
- **PostgreSQL** stores the full entity data (titles, descriptions, statuses, custom fields, etc.).
- **FastAPI** provides the REST API that synchronises both databases.

## Features

- **Multi-Project Support** — Create and manage isolated QMS projects
- **Requirements Management** — CRUD operations with custom fields, types, and components
- **SysML Relationship Stereotypes** — Model traceability using standard SysML link types
- **Test Case & Test Run Tracking** — Link test cases to requirements, record execution results
- **Defect Management** — Track defects linked to failing test runs
- **System Architecture Blocks** — Model hierarchical system decomposition (System → Product → Component → Part)
- **Full Graph Traversal** — Bidirectional graph exploration up to 5 hops
- **Coverage & Risk Analysis** — Identify uncovered requirements and at-risk items
- **Excel Import** — Bulk import with column-mapping wizard
- **Impact Matrix** — Requirement-to-test-case traceability matrix

## Prerequisites

| Dependency | Version |
|------------|---------|
| Python     | 3.9+    |
| Neo4j      | 4.x / 5.x |
| PostgreSQL | 13+     |

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/broooce1806/QMS-Graph.git
cd QMS-Graph
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your database credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Neo4j and PostgreSQL connection details.

### 5. Start the databases

Make sure both **Neo4j** and **PostgreSQL** are running. Create a PostgreSQL database named `QMS-MD` (or change the name in `.env`).

### 6. Run the API server

```bash
uvicorn main:app --reload
```

The API will be available at **http://127.0.0.1:8000**. Interactive docs at **http://127.0.0.1:8000/docs**.

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/requirements/projects` | Create a project |
| `GET` | `/requirements/projects` | List all projects |
| `POST` | `/requirements/` | Create a requirement |
| `GET` | `/requirements/` | List requirements |
| `POST` | `/requirements/link` | Create a SysML relationship |
| `DELETE` | `/requirements/link` | Delete a relationship |
| `GET` | `/requirements/stereotypes` | List available SysML stereotypes |
| `POST` | `/requirements/testcases` | Create a test case |
| `POST` | `/requirements/testruns` | Record a test run |
| `POST` | `/requirements/defects` | Create a defect |
| `POST` | `/requirements/blocks` | Create an architecture block |
| `GET` | `/requirements/full-graph/{id}` | Full graph traversal |
| `GET` | `/requirements/coverage` | Coverage analysis |
| `GET` | `/requirements/risk-requirements` | Risk analysis |
| `GET` | `/requirements/dashboard/list` | Requirements dashboard |
| `POST` | `/requirements/import/inspect` | Inspect Excel structure |
| `POST` | `/requirements/import/mapped` | Import with column mapping |

## Running Tests

```bash
pip install httpx pytest
pytest test_main.py -v
```

## Frontend

The companion React frontend is available at: [QMS-Frontend](https://github.com/broooce1806/QMS-Frontend)

## License

This project is provided as-is for educational and demonstration purposes.
