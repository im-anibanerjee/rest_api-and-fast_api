# 01 — HTTP Fundamentals & REST Principles (FastAPI)

This is doc 1 of the FastAPI series. Everything in this doc was run for real against the companion script `01 fastapi http fundamentals.py` (same folder as this doc) using FastAPI's `TestClient` — every status code and every response body you see here is genuine captured output, not something typed from memory. To reproduce any of it yourself, run `python "01 fastapi http fundamentals.py"` — the full script, including the part that drives every endpoint and prints the output, is reproduced at the bottom of this doc.

Goal of this doc: understand what actually happens when your React/Node frontend talks to your FastAPI backend — the request/response cycle, HTTP methods, status codes, idempotency, and the core REST ideas — well enough that reading any FastAPI route in your real office codebase stops feeling like magic.

## 1. What an API call actually is

When your frontend "calls an API", it is doing exactly this, no more:

1. The browser/frontend code opens a network connection to a server (your FastAPI app) and sends a **request**: a method, a URL, some headers, and optionally a body.
2. The server runs some Python code that decides what to do, and sends back a **response**: a status code, some headers, and optionally a body.
3. The connection closes (or is reused), and that's it. The server does not remember this happened unless it was explicitly told to write something to a database.

That last point is the REST principle called **statelessness**: every request must carry everything the server needs to handle it (who you are, what you want). The server is not sitting there "remembering" that you're logged in from your last click — that's why auth tokens get sent on *every* request (more on this in section 5, and in full depth in doc 09 on OAuth2/JWT).

A request and a response are both just **text** over the wire (HTTP is a text-based protocol, even though bodies are usually JSON these days). Here's the literal shape of one request/response pair from the demo, written out the way it travels over the network:

```
Request:
  GET /accounts/1 HTTP/1.1
  Host: localhost:8000

Response:
  HTTP/1.1 200 OK
  content-type: application/json

  {"id":1,"holder":"Ravi Kumar","balance":5000.0}
```

Everything else in FastAPI — routers, dependency injection, Pydantic models — exists to make building *this* easier and safer. Keep this picture in your head; it's the foundation for every doc that follows.

## 2. The demo app

This is the app half of the companion script every example in this doc was run against — a tiny in-memory "accounts" API (no real database yet; that's doc 06). The full file (shown in the appendix) also has a runnable block at the bottom that drives it:

```python
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
```

Things to notice already, even before we discuss any of it:
- `@app.get(...)`, `@app.post(...)`, etc. are **decorators** that register a Python function to handle a specific HTTP method + URL path. This mapping of (method, path) → function is called **routing**.
- `account_id: int` in the function signature is a **path parameter** — FastAPI pulls it out of the URL (`/accounts/1` → `account_id=1`) and converts it to an `int` automatically. If you send `/accounts/abc`, FastAPI rejects it before your function even runs (we'll see this produce a 422 in practice).
- `account: AccountIn` is a **request body** — FastAPI reads the JSON body, validates it against the `AccountIn` Pydantic model, and hands you a real Python object. Doc 02 goes deep on this; today we just need to know validation failures become 422 responses automatically, for free.

## 3. HTTP methods and what they *mean*

HTTP methods aren't arbitrary labels — each one carries a meaning that your code should honor, because frontend code, browsers, caches, and proxies all rely on that meaning being true.

| Method | Meaning | Has a body? | Safe? | Idempotent? |
|---|---|---|---|---|
| GET | Retrieve a resource | No (request body ignored by convention) | Yes | Yes |
| POST | Create a new resource / trigger an action | Yes | No | No |
| PUT | Replace a resource entirely | Yes | No | Yes |
| PATCH | Partially update a resource | Yes | No | No (usually) |
| DELETE | Remove a resource | Usually no | No | Yes |

Two words in that table matter a lot and are worth defining precisely:

- **Safe** means the method doesn't change server state — calling it is "just looking." Only GET (and HEAD/OPTIONS) are safe. This is why you should never design a GET endpoint that deletes something, even if it's convenient — browsers, link previewers, and crawlers will call GET requests without asking you, assuming they're harmless.
- **Idempotent** means calling it once has the same effect as calling it 10 times. This is NOT the same as "safe" — DELETE changes state (not safe) but is still idempotent (deleting an already-deleted thing just keeps it deleted; same end state).

### Proof: POST is not idempotent, PUT is

This is the kind of thing that's much more convincing seen running than read about. From the demo, calling `POST /accounts` twice with the **exact same body**:

```
--- POST /accounts (1st call) ---
status: 201
body: {
  "id": 3,
  "holder": "Dev Patel",
  "balance": 1200.0
}

--- POST /accounts (2nd call, same body) ---
status: 201
body: {
  "id": 4,
  "holder": "Dev Patel",
  "balance": 1200.0
}
```

Same request, sent twice → **two different accounts created** (id 3, then id 4). That's non-idempotency. This is exactly why a "Submit Order" button that does a POST needs to be disabled after the first click, or guarded with an idempotency key on the backend — otherwise a flaky network causing the frontend to retry silently double-creates things. You'll see this pattern for real in doc 08 when we talk about layered architecture and in the payments-style endpoints later.

Now `PUT /accounts/1` twice with the same body:

```
--- PUT /accounts/1 (1st call) ---
status: 200
body: {
  "id": 1,
  "holder": "Ravi Kumar",
  "balance": 9999.0
}

--- PUT /accounts/1 (2nd call, same body) ---
status: 200
body: {
  "id": 1,
  "holder": "Ravi Kumar",
  "balance": 9999.0
}
```

Identical result both times — the balance is just "set to 9999.0" again. That's idempotency: PUT means "make the resource look like this", and doing that twice leaves it looking the same as doing it once.

## 4. Status codes: what they actually tell the caller

Status codes are a 3-digit number whose **first digit is the category**:

- **2xx** — success, request understood and handled
- **3xx** — redirection (not used much in APIs; mostly a browser/HTML thing)
- **4xx** — the *client* did something wrong (bad input, not allowed, doesn't exist)
- **5xx** — the *server* did something wrong (a bug, a crash, a dependency failure)

This client-vs-server split is the single most useful thing to internalize: when you see a 4xx in the frontend, the fix is almost always "the frontend sent something wrong" (bad form data, missing field, expired token). When you see a 5xx, the fix is in the backend — something threw an exception that nobody caught.

Here is every status code the demo app produces, each with real captured output.

**200 OK** — a GET (or other method) succeeded and is returning data:
```
--- GET /accounts/1 ---
status: 200
body: {
  "id": 1,
  "holder": "Ravi Kumar",
  "balance": 5000.0
}
```

**201 Created** — a POST succeeded and created something new (convention: return the created thing, including its new id):
```
--- POST /accounts (1st call) ---
status: 201
body: {
  "id": 3,
  "holder": "Dev Patel",
  "balance": 1200.0
}
```

**204 No Content** — the request succeeded but there's nothing meaningful to return (classic for DELETE):
```
--- DELETE /accounts/2 (204) ---
status: 204
body (raw):
```
Note the body is genuinely empty — not `null`, not `{}`, nothing. A 204 response must not have a body; that's part of the HTTP spec, and FastAPI enforces it when you set `status_code=204`.

**400 Bad Request** — the client sent a value that's syntactically fine but semantically invalid for this endpoint — our own business rule, not a Pydantic type error:
```
--- GET /accounts?min_balance=-5 (400) ---
status: 400
body: {
  "detail": "min_balance cannot be negative"
}
```
We raised this ourselves in the route with `raise HTTPException(status_code=400, detail="...")`. This is the pattern for "the type is right but the value doesn't make sense."

**401 Unauthorized** — you didn't prove who you are (no credentials at all):
```
--- GET /secure-accounts no header (401) ---
status: 401
body: {
  "detail": "Missing X-API-Key header"
}
```

**403 Forbidden** — you proved who you are, but you're not allowed to do this:
```
--- GET /secure-accounts wrong key (403) ---
status: 403
body: {
  "detail": "This key is not allowed to view secure accounts"
}
```
The 401 vs 403 distinction trips people up constantly, so lock in this phrasing: **401 = "I don't know who you are."** **403 = "I know who you are, and the answer is no."** A request with zero credentials is always 401, never 403. A request with valid-but-insufficient credentials (wrong role, wrong key, expired-but-recognizable token depending on your design) is 403. This demo uses a single hardcoded API key only to isolate the concept — real auth (login, tokens, roles) is doc 09.

**404 Not Found** — the resource you asked for doesn't exist:
```
--- GET /accounts/999 (404) ---
status: 404
body: {
  "detail": "Account not found"
}
```
and, after deleting something, it's gone — same 404:
```
--- GET /accounts/2 after delete (404) ---
status: 404
body: {
  "detail": "Account not found"
}
```

**422 Unprocessable Entity** — this one is special to FastAPI/Pydantic and you will see it constantly: the request body doesn't match the shape the endpoint declared. Sending `POST /accounts` with no `balance` field at all:
```
--- POST /accounts malformed body (422) ---
status: 422
body: {
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "balance"
      ],
      "msg": "Field required",
      "input": {
        "holder": "No Balance Field"
      }
    }
  ]
}
```
Notice: we never wrote a single line of code to produce this. FastAPI validated the incoming JSON against `AccountIn` *before* `create_account()` ran at all, and rejected it automatically. `loc` tells you exactly where the problem is (`body` → `balance`), which is exactly what the frontend needs to show a useful "this field is required" message next to the right form input. This is the payoff of doc 02 (Pydantic) — you get this for free just by declaring a type.

**500 Internal Server Error** — the server itself crashed on an exception nobody caught:
```
--- GET /boom (500) ---
status: 500
body (raw): Internal Server Error
```
The route does `return 1 / 0`, a plain Python `ZeroDivisionError`. Nothing in the route catches it, so FastAPI's default behavior is to turn *any* unhandled exception into a generic 500 with no detail about what actually broke (good — you never want to leak a stack trace or internal exception message to a client; that's an information-disclosure risk). Internally, the real exception and traceback are still logged on the server for you to debug. A note on how this was captured: by default, FastAPI's `TestClient` re-raises the exception in the test process (useful when you're writing pytest tests and want a failure to show you the real traceback) — to see the *actual* HTTP-level 500 a real browser would get, the client here was built with `TestClient(app, raise_server_exceptions=False)`. Doc 10 (middleware) and later docs cover writing custom exception handlers so a 500 can return a consistent JSON error shape instead of this plain-text default.

## 5. Headers: metadata about the request/response, not the content itself

A header is a key-value pair sent alongside the request or response, separate from the body. Some headers are standard and handled by the framework automatically (`Content-Type`, `Content-Length`); some are custom and you define their meaning yourself. The demo's `/secure-accounts` endpoint reads a custom header:

```python
@app.get("/secure-accounts")
def secure_list(x_api_key: str | None = Header(default=None)):
```

FastAPI converts `X-API-Key` (the real HTTP header name, case-insensitive, hyphenated) into the Python parameter `x_api_key` (underscored) automatically — that naming conversion is a FastAPI convention worth remembering so header-based code doesn't look mysterious later.

Why headers and not query params or body for things like this? Because headers are the conventional place for cross-cutting concerns that aren't part of "the data" — authentication tokens, content negotiation (`Accept`, `Content-Type`), correlation/tracing IDs, caching directives. The real `Authorization: Bearer <token>` header you'll build in doc 09 works exactly the same mechanical way as `X-API-Key` does here; only the parsing and validation logic gets more involved.

## 6. REST, concretely

"REST" gets thrown around vaguely, but concretely, the ideas this demo already follows are:

- **Resources are nouns, identified by URLs.** `/accounts` is the collection, `/accounts/1` is one specific account. The *method* (GET/POST/PUT/DELETE) carries the verb, not the URL. A URL like `/getAccount?id=1` or `/deleteAccount` is the anti-pattern — if you ever see that in older code, that's RPC-style thinking leaking into what's supposed to be REST.
- **Uniform interface.** Every resource in this API is manipulated with the same five verbs. You don't invent `/accounts/1/remove` when DELETE `/accounts/1` already means that.
- **Representations, not the resource itself.** The client never gets the actual Python dict from the server's memory — it gets a JSON *representation* of it. This is why the response for `GET /accounts/1` and the internal `accounts[1]` dict happen to look identical here (we didn't bother hiding any fields in this toy example), but in a real API you'll often return a different shape than what's stored (e.g., never return a password hash even though it's a real column).
- **Statelessness** (section 1) — nothing here depends on "the previous request." Each call to `/accounts/1` carries everything needed to answer it.

What this demo does *not* yet show, on purpose, because they need their own docs: pagination for large collections, nested resources (`/accounts/1/transactions`), HATEOAS-style links (rarely used in practice — don't worry about this one), and versioning (`/v1/accounts`). You'll meet these as they come up in the real work-project deep dive later in the roadmap.

## 7. How this maps to your actual job

Your real frontend (React/Node) talks to your real FastAPI backend using exactly this mechanism — `fetch`/`axios` calls that are GET/POST/PUT/DELETE requests to specific URLs, and your backend routes handle them with functions that look structurally identical to the ones in this demo (just backed by PostgreSQL instead of a dict, which is doc 06). When you're reading an existing route in your office codebase and see `@router.post("/something", status_code=201)`, you now know precisely what every piece of that means: it's registering a non-idempotent, non-safe handler for creating something, and 201 is the convention for "created successfully, here's what you created." When something in the frontend shows an error, checking whether it's a 4xx or 5xx immediately tells you which side of the wire to go debug first.

## 8. Quick self-check

Before moving to doc 02 (Pydantic & validation), you should be able to answer these without looking back up:
- Why is DELETE idempotent even though it's not safe?
- If a frontend sends a login request with the wrong password, should that be 401 or 403? (It's 401 — no valid identity was established at all. If the password were right but the account is role-restricted from a specific action, *that's* 403.)
- Why does FastAPI return 422 instead of 400 for a malformed request body?
- Why is it dangerous to let a 500 response leak the real exception message to the client?

## Appendix: the full companion script

For completeness/reproducibility, this is the complete `01 fastapi http fundamentals.py` (same folder as this doc) — the app definitions from section 2, plus the runnable block at the bottom that produced every captured output above. Run it directly with `python "01 fastapi http fundamentals.py"`:

```python
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
```

**Next:** doc 02 — Pydantic & validation (what `BaseModel` is actually doing under the hood, custom validators, nested models, and why the 422 error shape above looks the way it does).
