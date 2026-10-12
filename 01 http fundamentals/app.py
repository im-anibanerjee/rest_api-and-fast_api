"""
a tiny demo API used only to generate real, verified output for
'01 fastapi http fundamentals.md'. not the real standalone project -
just big enough to show every HTTP concept the doc covers.
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
