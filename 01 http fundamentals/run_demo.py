"""
Drives app.py through every scenario doc 01 needs to show, using
TestClient, and prints real request/response pairs. This output gets
pasted into the doc verbatim - nothing in the doc is guessed.
"""
import json
from fastapi.testclient import TestClient
from app import app

# raise_server_exceptions=False so /boom's unhandled ZeroDivisionError
# comes back as a genuine HTTP 500 response instead of re-raising inside
# this test process (the default is True, meant for pytest-style tests
# that want the traceback to fail the test).
client = TestClient(app, raise_server_exceptions=False)


def show(label, resp):
    print(f"\n--- {label} ---")
    print(f"status: {resp.status_code}")
    try:
        print("body:", json.dumps(resp.json(), indent=2))
    except Exception:
        print("body (raw):", resp.text)


# 1. GET /accounts - no filter
show("GET /accounts", client.get("/accounts"))

# 2. GET /accounts - with min_balance filter
show("GET /accounts?min_balance=4000", client.get("/accounts", params={"min_balance": 4000}))

# 3. GET /accounts - negative min_balance -> 400
show("GET /accounts?min_balance=-5 (400)", client.get("/accounts", params={"min_balance": -5}))

# 4. GET /accounts/{id} - found
show("GET /accounts/1", client.get("/accounts/1"))

# 5. GET /accounts/{id} - not found -> 404
show("GET /accounts/999 (404)", client.get("/accounts/999"))

# 6. POST /accounts - create (non-idempotent: run twice, see two different ids)
show("POST /accounts (1st call)", client.post("/accounts", json={"holder": "Dev Patel", "balance": 1200.0}))
show("POST /accounts (2nd call, same body)", client.post("/accounts", json={"holder": "Dev Patel", "balance": 1200.0}))

# 7. POST /accounts - malformed body -> 422
show("POST /accounts malformed body (422)", client.post("/accounts", json={"holder": "No Balance Field"}))

# 8. PUT /accounts/{id} - replace balance (idempotent: run twice, same result)
show("PUT /accounts/1 (1st call)", client.put("/accounts/1", json={"balance": 9999.0}))
show("PUT /accounts/1 (2nd call, same body)", client.put("/accounts/1", json={"balance": 9999.0}))

# 9. DELETE /accounts/{id} then GET to confirm gone
show("DELETE /accounts/2 (204)", client.delete("/accounts/2"))
show("GET /accounts/2 after delete (404)", client.get("/accounts/2"))

# 10. GET /secure-accounts - no header -> 401
show("GET /secure-accounts no header (401)", client.get("/secure-accounts"))

# 11. GET /secure-accounts - wrong key -> 403
show("GET /secure-accounts wrong key (403)", client.get("/secure-accounts", headers={"X-API-Key": "wrong-key"}))

# 12. GET /secure-accounts - correct key -> 200
show("GET /secure-accounts correct key (200)", client.get("/secure-accounts", headers={"X-API-Key": "secret-admin-key"}))

# 13. GET /boom - unhandled exception -> real 500
show("GET /boom (500)", client.get("/boom"))
