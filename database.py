from neo4j import GraphDatabase
URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = "Traunstein@1806"

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD),
    encrypted=False
)

def get_session():
    return driver.session()
