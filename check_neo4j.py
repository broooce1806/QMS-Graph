from database import get_session
import sys

def check_nodes(project_id):
    print(f"Checking nodes for project: {project_id}")
    with get_session() as session:
        # Check specific project nodes
        res = session.run("MATCH (n {project_id: $pid}) RETURN labels(n) as labels, n.id as id LIMIT 20", pid=project_id)
        found = False
        for r in res:
            print(f" Found: {r['labels']} ID: {r['id']}")
            found = True
        
        if not found:
            print(" No nodes found with project_id filter. Checking all nodes...")
            res2 = session.run("MATCH (n) RETURN labels(n) as labels, n.id as id, n.project_id as pid LIMIT 10")
            for r in res2:
                print(f" Found: {r['labels']} ID: {r['id']} (Project: {r['pid']})")

if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "PR-002"
    check_nodes(pid)
