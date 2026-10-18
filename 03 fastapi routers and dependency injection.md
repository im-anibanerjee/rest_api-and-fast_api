# 03 — Routers & Dependency Injection (FastAPI)

This is doc 3 of the FastAPI series, picking up right after doc 02's deep dive into Pydantic models. Doc 01 and doc 02 both put every route in one file on one `app` object — fine for a demo, but no real API stays that small. This doc covers the two things that let a FastAPI codebase grow without turning into one unreadable file: splitting routes across **routers**, and sharing logic across routes with **dependency injection** (`Depends()`). Everything below was run for real against the extended demo app in section 2, using the same `TestClient` approach doc 01 and doc 02 used (see the last section of this doc for the exact method) — every status code and every response body shown here is genuine captured output.

Goal of this doc: stop thinking of `Depends()` as "a thing you occasionally see in FastAPI tutorials" and start seeing routers and dependencies as the two tools that let you organize a growing API — splitting *where* routes live, and sharing *what runs before* a route, without copy-pasting the same checks into every function.

## 1. Why split into routers at all

### Simple version
`APIRouter` is a mini version of `FastAPI` itself — you define routes on it exactly the way you'd define them on `app`, except it isn't live until you plug it into the real app with `app.include_router(...)`. This lets you put related routes (all the account routes, all the transfer routes) in their own file instead of one giant `main.py`.

### Real-life example
Think of a filing cabinet. One drawer holding every single paper the office has ever produced — invoices, contracts, HR forms, all mixed together — technically works, but finding anything means digging through everything. A filing cabinet with labeled drawers ("Accounts", "Transfers") means you open exactly one drawer for the thing you're looking for, and a new hire can guess where something lives without being told. `APIRouter` is the labeled drawer; `app.include_router()` is sliding that drawer into the cabinet.

### Real-world use case
Doc 01 and doc 02's demo app put `create_account`, `get_account`, `create_transfer` and friends all directly on `app` in one file. The real app below splits them into `app/routers/accounts.py` and `app/routers/transfers.py`, each with its own `APIRouter`, and `app/main.py` just imports both and includes them:

```python
# app/main.py
from fastapi import FastAPI
from app.routers import accounts, transfers

app = FastAPI(title="Demo Accounts API v3 - routers & dependency injection")

app.include_router(accounts.router)
app.include_router(transfers.router)
```

That's the entire file. Every route doc 01/02 would have put here now lives in `routers/accounts.py` or `routers/transfers.py` instead.

### Technical deep dive
`APIRouter(prefix="/accounts", tags=["accounts"])` does two things worth calling out separately. `prefix` is prepended to every route's path *on that router* — a route declared as `@router.get("/{account_id}")` becomes `GET /accounts/{account_id}` once included, so every route on the router writes its path relative to the prefix, never repeating `/accounts` itself (writing `@router.get("/accounts/{account_id}")` on a router that already has `prefix="/accounts"` would produce `/accounts/accounts/{account_id}`, which is a real, easy-to-make mistake). `tags=["accounts"]` is purely cosmetic — it's what groups these routes together under an "accounts" heading in the `/docs` Swagger UI (see the companion walkthrough doc) rather than one long undifferentiated list. Both can also be passed to `include_router()` itself instead of the router's own constructor, which is handy when the same router module needs to be mounted under two different prefixes (an internal vs external API, for instance) — but doing it once, up front, on the router itself is the normal case.

### Connecting back
Routers don't add any new capability FastAPI didn't already have — every route on a router could, in principle, be written directly on `app`. What routers buy you is purely organizational: as the Accounts API grows past the handful of routes in this doc into dozens of real endpoints, "every route lives directly on `app` in one file" stops being viable long before "every route lives on a router in its own file, with `app` just wiring routers together" does.

## 2. The extended demo app

This builds on doc 02's Accounts domain, simplified slightly (holder + balance only, no nested address/account_type) so the file split and the dependency logic are the clear focus. Four files:

```python
# app/dependencies.py
"""
Shared dependencies for the Accounts API.

These are the building blocks every router below plugs into FastAPI's
Depends() system. None of this is route-specific logic - that's the point.
"""
from fastapi import Header, HTTPException, Query

db_log: list[str] = []
VALID_API_KEY = "topsecret123"
call_count = {"n": 0}


def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """Gate dependency: doesn't feed data into the route, just decides
    whether the request is even allowed to reach it."""
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")
    if x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


def get_account_or_404(account_id: int) -> dict:
    """Path-parameter dependency: FastAPI sees this needs 'account_id'
    and pulls it from the URL path automatically, same as it would for
    a route function."""
    from app.routers.accounts import accounts

    account = accounts.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return account


class Pagination:
    """A class used as a dependency instead of a function. FastAPI calls
    Pagination(...) the same way it would call a function, resolving
    skip/limit from the query string, and hands your route an instance."""

    def __init__(self, skip: int = 0, limit: int = Query(default=10, le=100)):
        self.skip = skip
        self.limit = limit


def count_call() -> int:
    """Used twice in one route signature purely to demonstrate FastAPI's
    per-request dependency caching (section 8)."""
    call_count["n"] += 1
    return call_count["n"]


def get_db():
    """Yield dependency: everything before yield is setup, everything
    after is teardown, guaranteed to run even if the route raises."""
    db_log.append("OPEN session")
    session = {"log": db_log}
    try:
        yield session
    finally:
        db_log.append("CLOSE session")
```

```python
# app/routers/accounts.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import Pagination, count_call, get_account_or_404, get_db

router = APIRouter(prefix="/accounts", tags=["accounts"])

accounts: dict[int, dict] = {
    1: {"id": 1, "holder": "Ravi Kumar", "balance": 5000.00},
    2: {"id": 2, "holder": "Priya Shah", "balance": 3000.00},
    3: {"id": 3, "holder": "Anjali Mehta", "balance": 12500.00},
}
next_id = 4


class AccountIn(BaseModel):
    holder: str = Field(min_length=2, max_length=50)
    balance: float = Field(ge=0)


class AccountOut(BaseModel):
    id: int
    holder: str
    balance: float


@router.get("", response_model=list[AccountOut])
def list_accounts(pagination: Pagination = Depends()):
    values = list(accounts.values())
    return values[pagination.skip : pagination.skip + pagination.limit]


# NOTE: this route is defined BEFORE "/{account_id}" below on purpose -
# see section 1's technical deep dive about route-matching order.
@router.get("/_dependency_cache_demo")
def dependency_cache_demo(first: int = Depends(count_call), second: int = Depends(count_call)):
    return {"first": first, "second": second}


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account: dict = Depends(get_account_or_404)):
    return account


@router.post("", status_code=201, response_model=AccountOut)
def create_account(account: AccountIn, db: dict = Depends(get_db)):
    global next_id
    new_account = {"id": next_id, "holder": account.holder, "balance": account.balance}
    accounts[next_id] = new_account
    db["log"].append(f"INSERT account id={next_id}")
    next_id += 1
    return new_account


@router.patch("/{account_id}/balance", response_model=AccountOut)
def update_balance(
    new_balance: float,
    account: dict = Depends(get_account_or_404),
    db: dict = Depends(get_db),
):
    account["balance"] = new_balance
    db["log"].append(f"UPDATE account id={account['id']} balance={new_balance}")
    return account
```

```python
# app/routers/transfers.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.dependencies import get_db, verify_api_key
from app.routers.accounts import accounts

# dependencies=[Depends(verify_api_key)] applies to EVERY route on this
# router - no route below mentions verify_api_key itself.
router = APIRouter(prefix="/transfers", tags=["transfers"], dependencies=[Depends(verify_api_key)])


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(gt=0)

    @model_validator(mode="after")
    def accounts_must_differ(self):
        if self.from_account_id == self.to_account_id:
            raise ValueError("from_account_id and to_account_id must be different")
        return self


@router.post("")
def create_transfer(transfer: TransferRequest, db: dict = Depends(get_db)):
    from_acc = accounts.get(transfer.from_account_id)
    to_acc = accounts.get(transfer.to_account_id)
    if from_acc is None or to_acc is None:
        raise HTTPException(status_code=404, detail="One or both accounts not found")

    from_acc["balance"] -= transfer.amount
    to_acc["balance"] += transfer.amount
    db["log"].append(f"TRANSFER {transfer.amount} from={transfer.from_account_id} to={transfer.to_account_id}")
    return {"status": "ok", "transfer": transfer.model_dump()}
```

```python
# app/main.py
from fastapi import FastAPI
from app.routers import accounts, transfers

app = FastAPI(title="Demo Accounts API v3 - routers & dependency injection")
app.include_router(accounts.router)
app.include_router(transfers.router)
```

## 3. Function dependencies that read the path — `get_account_or_404`

### Simple version
A dependency function can take the exact same kind of parameters a route function can — including path parameters — and FastAPI fills them in from the request the same way, before your route ever runs.

### Real-life example
Think of airport security before you reach your actual gate. Every gate's agent doesn't re-check your ID and boarding pass from scratch — that check already happened once, at a shared checkpoint everyone passes through, and by the time you reach your gate the airline already knows who you are. `get_account_or_404` is that shared checkpoint for every route that operates on one account by ID: the "does this account exist" question gets asked and answered in exactly one place, and every route downstream just gets a real account, never has to ask again.

### Real-world use case
`get_account_or_404(account_id: int)` never appears explicitly as a parameter on `get_account` — FastAPI sees the route needs `Depends(get_account_or_404)`, sees *that function* needs `account_id`, and pulls it straight from the URL path, exactly as if `get_account` had declared `account_id: int` itself. Two real calls against the same route show both outcomes:

```
GET /accounts/2
status: 200
{"id": 2, "holder": "Priya Shah", "balance": 3000.0}

GET /accounts/999
status: 404
{"detail": "Account 999 not found"}
```

`get_account`'s own body is just `return account` — one line. All the actual logic, including the 404, lives in the dependency, reused identically by `update_balance` further down in section 2's code.

### Technical deep dive
This works because FastAPI resolves dependencies recursively, re-running its normal "where does this parameter come from" logic *inside* a dependency function exactly the way it does for a route function: no type hint with a special marker means "look in the path/query for a matching name," a `Body(...)`/`Header(...)` annotation means look there instead, and a nested `Depends(...)` means resolve that one first. `get_account_or_404` isn't doing anything magic — it's just a function FastAPI calls for you, with its own arguments filled in the normal way, before calling your actual route function with whatever that dependency returned.

### Connecting back
Any logic a route needs "before it can actually do its job" — checking something exists, checking something is allowed, loading something from a path parameter — is a candidate to pull out into a dependency instead of being the first few lines of every route function. The moment you catch yourself writing the same `if thing is None: raise HTTPException(404, ...)` at the top of two different routes, that's the dependency you're missing.

## 4. Classes as dependencies — `Pagination`

### Simple version
A dependency doesn't have to be a function — a class works too, as long as FastAPI can call it (which every class is, via `__init__`). `Depends()` with no arguments, used as a parameter's default, tells FastAPI "build this from the parameter's own type hint."

### Real-life example
Compare ordering coffee by naming three separate things ("medium, oat milk, extra shot") versus just saying "the usual" and having the barista already know it means all three together. `Pagination` bundles "skip" and "limit" into one object instead of two separate loose parameters threaded through every route that needs pagination — the route asks for "the usual pagination," not three individually-spelled-out values.

### Real-world use case
`list_accounts(pagination: Pagination = Depends())` — note the bare `Depends()`, no argument. FastAPI looks at the type hint (`Pagination`) and calls `Pagination(skip=..., limit=...)` itself, resolving `skip` and `limit` from the query string exactly as if they were ordinary route parameters, because that's literally what `Pagination.__init__` declares them as. A real call:

```
GET /accounts?skip=1&limit=1
status: 200
[{"id": 2, "holder": "Priya Shah", "balance": 3000.0}]
```

Three accounts exist; `skip=1` skips the first, `limit=1` caps the result at one — exactly `Pagination(skip=1, limit=1)`'s job, with `limit`'s `Query(default=10, le=100)` meaning a caller can never ask for more than 100 at once.

### Technical deep dive
`Depends()` with no argument and `Depends(Pagination)` (explicitly passing the class) do the same thing when the parameter is also type-hinted as `Pagination` — the bare form is shorthand that reads the callable off the type hint instead of making you repeat it. This only works because `Pagination.__init__` itself looks exactly like a route function signature to FastAPI: a plain `skip: int = 0` pulled from the query string, and `limit: int = Query(default=10, le=100)` with FastAPI's own validation applied before `Pagination` is even constructed — if someone requests `limit=500`, FastAPI rejects it with a 422 before `Pagination.__init__` runs at all, because the `le=100` constraint is checked at the parameter-resolution stage, not inside your class.

### Connecting back
Reach for a class dependency specifically when a dependency's "result" is naturally more than one related value that travel together — pagination (skip + limit), a date range (start + end), a set of filters. A single value with no related fields is usually clearer as a plain function dependency like `get_account_or_404`.

## 5. Yield dependencies — setup and guaranteed teardown

### Simple version
A dependency written with `yield` instead of `return` splits into two halves: everything before `yield` runs *before* your route, and everything after `yield` runs *after* your route returns — and FastAPI guarantees the "after" part runs even if your route raises an exception.

### Real-life example
Think of a library checking out a book. The librarian logs it out before handing it to you (setup), you go use it however you like, and whether you return it in perfect condition or spill coffee on it, the librarian still logs it back in when it comes back (teardown) — the "log it back in" step isn't conditional on how your reading went. `get_db`'s `try/finally` around `yield` is exactly that guarantee: "CLOSE session" happens whether the route finished cleanly or blew up.

### Real-world use case
`get_db()` appends `"OPEN session"` before handing a session dict to the route, and `"CLOSE session"` after, no matter what. Two real sequences, captured by clearing the log and checking it right after each call:

```
POST /accounts {"holder": "Dev Patel", "balance": 1000}
status: 201
db_log: ['OPEN session', 'INSERT account id=4', 'CLOSE session']

POST /transfers (with a valid API key) {"from_account_id": 1, "to_account_id": 2, "amount": 500}
status: 200
db_log: ['OPEN session', 'TRANSFER 500.0 from=1 to=2', 'CLOSE session']
```

In both cases, the route's own line (`INSERT ...` / `TRANSFER ...`) is sandwiched exactly between the dependency's open and close — the route never had to open or close anything itself.

### Technical deep dive
This is the standard pattern for any resource that needs cleanup — a real database session, a file handle, a lock. `try: yield session / finally: ...` is what makes teardown unconditional: if the route function (or anything else between `yield` and the route returning) raises, Python still runs the `finally` block on its way out, so `"CLOSE session"` is logged even on a failed request. A plain `return session` with no `yield` has no equivalent "after the route" hook at all — once a dependency returns a value, FastAPI's involvement with it is over.

### Connecting back
Any dependency representing something that needs to be "closed," "released," or "cleaned up" after the request — not just given to the route — should use `yield`, not `return`. A dependency that just computes or looks up a value with nothing to clean up afterward (`get_account_or_404`, `Pagination`) has no reason to.

## 6. Dependencies at the router level vs. per-route

### Simple version
`Depends(...)` can be listed once on an entire `APIRouter` (`dependencies=[Depends(verify_api_key)]`), applying it to every route on that router automatically, instead of writing `Depends(verify_api_key)` as a parameter on each route individually.

### Real-life example
Think of a building's front-door key card reader versus a separate lock on every individual office door inside. If every employee needs to swipe in at the front door no matter which office they're headed to, you put the reader at the front door once — you don't install an identical reader on every single office door and remember to configure each one the same way.

### Real-world use case
Every route on `transfers.router` needs a valid API key; none of `accounts.router`'s routes do (in this demo app) — a deliberate split to show the contrast. `transfers.router`'s `APIRouter(..., dependencies=[Depends(verify_api_key)])` means `create_transfer`'s own signature never mentions `verify_api_key` at all, yet every call is gated by it:

```
POST /transfers (no X-API-Key header)
status: 401
{"detail": "X-API-Key header is required"}

POST /transfers (X-API-Key: nope)
status: 401
{"detail": "Invalid API key"}

POST /transfers (X-API-Key: topsecret123)
status: 200
{"status": "ok", "transfer": {"from_account_id": 1, "to_account_id": 2, "amount": 500.0}}
```

### Technical deep dive
A router-level dependency still runs exactly like any other dependency — it's resolved before the route function, can raise `HTTPException` to short-circuit the request, and FastAPI still applies it per-route internally. The difference is purely where it's declared. One real consequence worth knowing: `verify_api_key`'s *return value* (the validated key string) is thrown away when it's declared this way — `create_transfer`'s signature has nowhere to receive it, because router-level `dependencies=[...]` entries are only ever run for their side effects (raise or don't raise), never for their return value. If a route genuinely needs the dependency's result as data, it has to be declared as a normal parameter on that specific route instead (`key: str = Depends(verify_api_key)`), not router-wide.

### Connecting back
Router-level `dependencies=[...]` is for "every route here needs this gate," and per-route `Depends(...)` is for "this specific route needs this value (or this specific gate)." Mixing both on the same router is completely normal — `transfers.router` gates everything with `verify_api_key` at the router level, while individual routes still add their own per-route dependencies (`get_db`) for things that aren't shared by every single route.

## 7. Overriding dependencies for testing

### Simple version
`app.dependency_overrides` is a dictionary FastAPI checks before calling the real dependency function — if a dependency is a key in that dict, FastAPI calls the *replacement* function instead, for every request, until you clear it.

### Real-life example
Think of a fire drill. Nobody wants to test "does the real fire alarm actually work" by setting an actual fire — you temporarily swap in a drill procedure that exercises everything else (people leaving, headcounts, the logistics) without the real trigger. `app.dependency_overrides[verify_api_key] = lambda: "test-key"` is the drill switch for authentication specifically: everything downstream behaves as if a valid key was supplied, without a test actually having to know or send one.

### Real-world use case
This is exactly why `TestClient` (the tool this whole doc series verifies itself with) is practical to use against routes with real auth — you don't want every test of `/transfers`'s actual business logic to also have to carry a real API key around. Overriding, using the override, then clearing it again, captured for real:

```
app.dependency_overrides[verify_api_key] = lambda: "test-key"

POST /transfers (NO header at all, override active)
status: 200
{"status": "ok", "transfer": {"from_account_id": 2, "to_account_id": 3, "amount": 100.0}}

app.dependency_overrides.clear()

POST /transfers (no header, override cleared)
status: 401
{"detail": "X-API-Key header is required"}
```

Same exact request both times — the only thing that changed was whether an override was registered.

### Technical deep dive
The dictionary is keyed by the *dependency function object itself* (`verify_api_key`, the function, not a string naming it), which is why both the real app and your test need to import the exact same function to override it correctly. This mechanism works for any dependency, not just auth — a test suite commonly overrides a real `get_db` (one that opens a real database connection) with a version pointed at a throwaway test database, so tests never touch production data. It's deliberately global and mutable on the `app` object, which is exactly why clearing it afterward (`app.dependency_overrides.clear()`) matters — an override left in place silently changes the behavior of every subsequent test that happens to share the same `app` instance.

### Connecting back
`dependency_overrides` is a testing tool, not a production pattern — real request traffic should always go through the real dependency. Its entire value is letting tests isolate "does my route's actual logic work" from "does my auth/db/external-service dependency work," checking each independently instead of needing a real API key or a real database spun up just to test a transfer's math.

## 8. A quick note on dependency caching within one request

FastAPI caches a dependency's result for the duration of a single request by default — if the same dependency function is depended on twice in one request (directly, or indirectly through two different routes' shared sub-dependencies), it only actually runs once, and the second "call" just reuses the first result. `count_call()` increments a counter every time it genuinely runs, and `dependency_cache_demo` depends on it twice:

```
GET /accounts/_dependency_cache_demo (1st request)
status: 200
{"first": 1, "second": 1}

GET /accounts/_dependency_cache_demo (2nd request)
status: 200
{"first": 2, "second": 2}
```

Within one request, `first` and `second` are identical (`1` and `1`, then `2` and `2`) — `count_call` only really ran once per request, even though it's written as `Depends(count_call)` twice. Across the two separate requests, the counter keeps climbing, because caching never crosses request boundaries. This is controlled by `Depends(..., use_cache=True)`, which is the default; passing `use_cache=False` forces a dependency to genuinely re-run every time it's depended on, even within the same request — rarely needed, but worth knowing exists if you ever see a dependency behave "more cached" than you expected.

## Interview questions

1. What problem does `APIRouter` actually solve — what capability does a router have that writing routes directly on `app` doesn't, versus what's purely organizational?
2. What does the `prefix` argument on `APIRouter` do, and what mistake does a developer make if they also include that same prefix inside an individual route's own path string?
3. How does FastAPI resolve `account_id` inside `get_account_or_404` when the route function itself (`get_account`) never declares `account_id` as a parameter at all?
4. Why would you reach for a class as a dependency (like `Pagination`) instead of a plain function? What has to be true about the class for `Depends()` with no arguments to work?
5. What's the actual mechanical difference between a dependency that `return`s a value and one that `yield`s it? Why does the `yield` version wrap its cleanup code in `try/finally` specifically?
6. What's the practical difference between declaring `dependencies=[Depends(verify_api_key)]` on an `APIRouter` versus adding `Depends(verify_api_key)` as a parameter on every individual route in that router? Name one thing you lose by choosing the router-level form.
7. Can a route that depends on a router-level dependency (declared via `dependencies=[...]`) access that dependency's return value directly? Why or why not?
8. What does `app.dependency_overrides` actually do, mechanically, and why is it the dictionary's *key* that matters rather than some string name?
9. If two different routes both depend (directly or through a shared sub-dependency) on the same dependency function within a single request, does that function run once or twice? What determines this, and what flag would change it?
10. A yield dependency's teardown code runs in a `finally` block. If the route function itself raises an unhandled exception, does the teardown still run? What would break if it didn't?

## Practice questions

Attempt these yourself first — recreate the four-file structure from section 2 in your own `D:\interview prep\fast_api` folder, extend it, run it for real, and see what happens before checking anything. Then share your code and real output for a check.

1. **Add a new router from scratch.** Create a third `APIRouter` (your choice of domain — a simple `/transactions` history endpoint for an account works well) with its own prefix and tag, add at least one real route to it, wire it into `main.py` with `include_router`, and capture a real successful call against it.

2. **Give a router-level dependency a real side effect you can observe.** Add a second router-level dependency to `accounts.router` (not `transfers.router`) that logs something to a list every time any accounts route is hit — then call two or three different account routes and show, with real captured output, that the log grew once per request regardless of which specific route was called.

3. **Deliberately trigger the route-ordering bug, then fix it.** Take `dependency_cache_demo` and `get_account`, swap their order in the file so `"/{account_id}"` is now defined first, restart, and capture the real (wrong) response when you hit `/accounts/_dependency_cache_demo` — it should get swallowed by the `{account_id}` route instead. Then move it back, confirm the real correct response returns, and explain in writing why the order mattered.

4. **Write your own yield dependency with a failure case.** Add a yield dependency that logs "OPEN" and "CLOSE" the same way `get_db` does, but use it in a route that deliberately raises an `HTTPException` partway through (after the dependency has already opened). Capture real output showing "CLOSE" still appears in the log even though the route raised — this is the guarantee from section 5.

5. **Override a dependency that returns real data, not just an auth gate.** Pick `get_account_or_404` and override it in a small test script so it returns a fake account dict without ever checking the real `accounts` dictionary. Call `/accounts/999` (which would normally 404) and capture the real 200 response the override produces instead, then clear the override and confirm `/accounts/999` goes back to a real 404.

### How to run the practice code and test

Same two options doc 01 and doc 02 walked through — recreate the file structure from section 2 in your `D:\interview prep\fast_api` folder, make the change the question asks for, then either:

**Option A — `TestClient`, no server needed.** Add a small script alongside your `app/` package:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
response = client.get("/accounts", params={"skip": 0, "limit": 2})
print("status:", response.status_code)
print("body:", response.json())
```

**Option B — a real running server**, with `uvicorn app.main:app --reload` (run from the folder containing the `app/` package), then either `curl` or the `/docs` Swagger UI — this time you'll actually see the "accounts" and "transfers" tags grouping routes separately, which is the `tags=[...]` argument from section 1 in action.

## How the output in this doc was actually captured

Same method as doc 01 and doc 02: the four files from section 2 were written for real, a separate script imported `app.main.app`, built a `TestClient(app, raise_server_exceptions=False)`, and fired one real request per scenario shown in this doc — eleven calls total, covering pagination, the path-parameter dependency's success and 404 paths, a yield dependency's open/close log on two different routes, a router-level auth gate's blocked/wrong-key/success paths, a cross-field validation failure still firing inside a router, a dependency override being applied and then cleared, and the per-request dependency-caching counter across two separate requests. Every status code and response body shown above is that script's real printed output, pasted in verbatim — nothing in this doc was typed from memory or reasoned out without running it.

---

*When you've worked through these, share your code and the real output you captured. Once this one's checked off, say "next" and I'll build the next doc.*
