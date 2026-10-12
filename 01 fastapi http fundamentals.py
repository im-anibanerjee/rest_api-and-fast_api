"""
Companion script for '01 fastapi http fundamentals.md'.

Defines a tiny demo API (not the real standalone project - just big
enough to show every HTTP concept the doc covers), then, if you run this
file directly, drives every endpoint with FastAPI's TestClient and
prints real request/response pairs. Every status code and body quoted
in the doc was produced by running exactly this file.
"""
from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel

app = FastAPI(title="Demo Accounts API")

# in-memory "database" - just a dict, reset every time the process starts
accounts: dict[int, dict] = {
    1: {"id": 1, "holder": "Ravi Kumar", "balance": 5000.00},
    2: {"id": 2, "holder": "Priya Shah", "balance": 3000.00},
}
next_id = 3


class AccountIn(BaseModel):
    holder: str
    balance: float


class AccountUpdate(BaseModel):
    balance: float


@app.get("/accounts")
def list_accounts(min_balance: float | None = Query(default=None)):
    if min_balance is not None and min_balance < 0:
        raise HTTPException(status_code=400, detail="min_balance cannot be negative")
    results = list(accounts.values())
    if min_balance is not None:
        results = [a for a in results if a["balance"] >= min_balance]
    return results


@app.get("/accounts/{account_id}")
def get_account(account_id: int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    return accounts[account_id]


@app.post("/accounts", status_code=201)
def create_account(account: AccountIn):
    global next_id
    new_account = {"id": next_id, "holder": account.holder, "balance": account.balance}
    accounts[next_id] = new_account
    next_id += 1
    return new_account


@app.put("/accounts/{account_id}")
def replace_balance(account_id: int, update: AccountUpdate):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    accounts[account_id]["balance"] = update.balance
    return accounts[account_id]


@app.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    del accounts[account_id]
    return None


@app.get("/secure-accounts")
def secure_list(x_api_key: str | None = Header(default=None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if x_api_key != "secret-admin-key":
        raise HTTPException(status_code=403, detail="This key is not allowed to view secure accounts")
    return list(accounts.values())


@app.get("/boom")
def boom():
    # deliberately unhandled - demonstrates a real 500
    return 1 / 0


if __name__ == "__main__":
    # Drives every scenario above and prints real request/response pairs.
    # This is the exact output quoted throughout the doc.
    import json
    from fastapi.testclient import TestClient

    # raise_server_exceptions=False so /boom's unhandled ZeroDivisionError
    # comes back as a genuine HTTP 500 response instead of re-raising inside
    # this process (the default is True, meant for pytest-style tests that
    # want the traceback to fail the test).
    client = TestClient(app, raise_server_exceptions=False)

    def show(label, resp):
        print(f"\n--- {label} ---")
        print(f"status: {resp.status_code}")
        try:
            print("body:", json.dumps(resp.json(), indent=2))
        except Exception:
            print("body (raw):", resp.text)

    show("GET /accounts", client.get("/accounts"))
    show("GET /accounts?min_balance=4000", client.get("/accounts", params={"min_balance": 4000}))
    show("GET /accounts?min_balance=-5 (400)", client.get("/accounts", params={"min_balance": -5}))
    show("GET /accounts/1", client.get("/accounts/1"))
    show("GET /accounts/999 (404)", client.get("/accounts/999"))
    show("POST /accounts (1st call)", client.post("/accounts", json={"holder": "Dev Patel", "balance": 1200.0}))
    show("POST /accounts (2nd call, same body)", client.post("/accounts", json={"holder": "Dev Patel", "balance": 1200.0}))
    show("POST /accounts malformed body (422)", client.post("/accounts", json={"holder": "No Balance Field"}))
    show("PUT /accounts/1 (1st call)", client.put("/accounts/1", json={"balance": 9999.0}))
    show("PUT /accounts/1 (2nd call, same body)", client.put("/accounts/1", json={"balance": 9999.0}))
    show("DELETE /accounts/2 (204)", client.delete("/accounts/2"))
    show("GET /accounts/2 after delete (404)", client.get("/accounts/2"))
    show("GET /secure-accounts no header (401)", client.get("/secure-accounts"))
    show("GET /secure-accounts wrong key (403)", client.get("/secure-accounts", headers={"X-API-Key": "wrong-key"}))
    show("GET /secure-accounts correct key (200)", client.get("/secure-accounts", headers={"X-API-Key": "secret-admin-key"}))
    show("GET /boom (500)", client.get("/boom"))
