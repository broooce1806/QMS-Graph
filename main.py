from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from requirements import router as requirement_router
from database import init_db
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(requirement_router)

@app.get("/")
def root():
    return {"message": "QMS Tool API running"}



@app.get("/visualize/{req_id}", response_class=HTMLResponse)
def visualize(req_id: str):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Requirement Graph</title>
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    </head>
    <body>
        <h2>Graph for {req_id}</h2>
        <div id="mynetwork" style="width:100%; height:600px; border:1px solid lightgray;"></div>

        <script>
            fetch("/requirements/full-graph/{req_id}")
                .then(res => res.json())
                .then(data => {{

                    const nodes = new vis.DataSet(
                        data.nodes.map(n => {{
                            return {{ id: n.id, label: n.label }};
                        }})
                    );

                    const edges = new vis.DataSet(
                        data.edges.map(e => {{
                            return {{
                                from: e.source,
                                to: e.target,
                                label: e.type,
                                arrows: "to"
                            }};
                        }})
                    );

                    const container = document.getElementById("mynetwork");
                    const network = new vis.Network(container, {{
                        nodes: nodes,
                        edges: edges
                    }}, {{
                        layout: {{ improvedLayout: true }},
                        physics: {{ enabled: true }}
                    }});
                }});
        </script>
    </body>
    </html>
    """
