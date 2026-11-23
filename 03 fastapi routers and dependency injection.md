# 03 — Routers & Dependency Injection (FastAPI)

This is doc 3 of the FastAPI series, picking up right after doc 02's deep dive into Pydantic models. Doc 01 and doc 02 both put every route in one file on one `app` object — fine for a demo, but no real API stays that small. This doc covers the two things that let a FastAPI codebase grow without turning into one unreadable file: splitting routes across **routers**, and sharing logic across routes with **dependency injection** (`Depends()`). Everything below was run for real against the extended demo app in section 2, using the same `TestClient` approach doc 01 and doc 02 used (see the last section of this doc for the exact method) — every status code and every response body shown here is genuine captured output.

Goal of this doc: stop thinking of `Depends()` as "a thing you occasionally see in FastAPI tutorials" and start seeing routers and dependencies as the two tools that let you organize a growing API — splitting *where* routes live, and sharing *what runs before* a route, without copy-pasting the same checks into every function.

> **Follow-up: these two ideas didn't land — explain "splitting routes across routers" and "sharing logic across routes with dependency injection (`Depends()`)" in much more detail and in a very simple way, like every other confusing part in this series.**

## Thing 1: "splitting routes across routers"

### Simple version
A "route" is just one single rule your API knows: "when someone visits this exact web address with this exact method (GET, POST, etc.), run this one function." Every FastAPI app built so far (doc 01, doc 02) wrote every single one of these rules, one after another, in one file, all stuck under the same `app` object. "Splitting routes across routers" just means: instead of writing all your rules in one giant file, you group related rules together into their own smaller files, and then connect those smaller files back to the main one.

### Real-life example
Imagine you're organizing a house that currently has everything — clothes, dishes, tools, books — dumped into one single room. You can technically still find things, but it's a mess, and it gets worse every time you buy something new. So instead, you make separate rooms: a bedroom for clothes, a kitchen for dishes, a garage for tools. Each room is still part of the same house — you haven't built a second house — you've just decided "clothes-related stuff lives here, kitchen-related stuff lives there." A router is one of those rooms. It's not a new building; it's a labeled section of the same one house.

### Real-world use case
In the actual demo app: every rule about accounts (`create_account`, `get_account`, `list_accounts`) got moved into its own file, `accounts.py`. Every rule about transfers (`create_transfer`) got moved into its own file, `transfers.py`. Each of those files has its own small `router` object — think of it as "the box these rules get packed into" — and then `main.py` has exactly two lines that say "take the accounts box, and the transfers box, and plug them both into the real app." That's it. Nothing more mysterious than: decide which rules belong together, put them in their own file, then plug that file's box into the main app.

### Technical deep dive
Mechanically, here's the whole sequence, step by step, with no skipped steps:
1. In `accounts.py`, you write `router = APIRouter(...)`. This creates an empty box. It is not connected to anything yet — if you ran your server right now with only this, none of these routes would actually work, because this box isn't plugged in.
2. Still in `accounts.py`, every route you write — `@router.get(...)`, `@router.post(...)` — gets added into that box, not onto the real app.
3. In `main.py`, you write `app.include_router(accounts.router)`. This is the literal "plug the box into the house" step. Before this line runs, the routes inside that box are invisible to anyone using your API. After this line runs, they work exactly like any normal route.
4. You do the exact same thing for `transfers.py`'s box.

So the entire idea of "routers" is just: write groups of related routes in their own file, inside a box (`APIRouter()`), then plug each box into the real app with one line (`include_router`). Nothing about how an individual route works has changed at all — `@router.get(...)` behaves exactly like `@app.get(...)` always did; it's purely about *where you physically write the code* and *how it gets reconnected*.

### Connecting back
So "splitting routes across routers" is not a new way of writing a single route — it's a new way of *organizing many routes* once you have too many to comfortably keep in one file. Nothing changes about how any one route works; only where it physically lives, and the one extra step (`include_router`) needed to reconnect it.

## Thing 2: "sharing logic across routes with dependency injection (`Depends()`)"

### Simple version
Sometimes, before a route's actual job can run, something needs to be checked or prepared first — "does this account exist," "did they send a valid password," "what page of results did they ask for." If more than one route needs the exact same check, you'd normally have to copy-paste that same checking code into every route that needs it. Dependency injection is a way to write that checking code *once*, in its own separate function, and then just tell FastAPI "run this first, automatically, before this route" — using `Depends(...)` — instead of pasting the same code over and over.

### Real-life example
Think about starting a new job. On your very first day, HR checks your ID, verifies your paperwork, and sets you up in the system — once. After that, you don't re-do that whole process every single time you walk into a different department. Each department just trusts that "HR already checked this person, here they are, already verified." Dependency injection is that HR step: a check written once, that every route who needs it can just ask for, instead of each department re-inventing its own ID-checking process from scratch.

### Real-world use case
In the demo app, `get_account_or_404` is exactly this. Three different routes (`get_account`, `update_balance`, and anything else that needs one specific account) all need to answer the same question first: "does this account ID actually exist, and if not, send back a 404." Instead of writing that same `if account not found: error` check inside all three route functions, it's written once, as its own function, and each route just says `account: dict = Depends(get_account_or_404)` in its parameter list. FastAPI sees that, runs `get_account_or_404` by itself first, and only calls your actual route function afterward, handing it the real account it already found.

### Technical deep dive
Here's the literal mechanical sequence, with no steps skipped:
1. You write a normal Python function, `get_account_or_404`, that does one specific job — check something, and either raise an error or return a result.
2. In a route's own parameter list, you write `something = Depends(get_account_or_404)`. This is the actual instruction to FastAPI: "before you call this route, call `get_account_or_404` first."
3. When a real request comes in, FastAPI sees that `Depends(...)`, calls `get_account_or_404` on its own, and waits for it to either raise an error (in which case your route never even runs) or return a value.
4. If it returned a value, FastAPI hands that value to your route as the parameter you named — in this case, `account`.
5. Your route's own code never has to perform the check itself. It just trusts that if its own body is running at all, the check already passed.

The actual word "Depends" is just a plain Python function — there's no special syntax happening. Writing `Depends(get_account_or_404)` as a parameter's default value is simply the specific spot FastAPI looks for this instruction.

### Connecting back
So dependency injection isn't some separate, exotic FastAPI feature — it's the direct answer to "I don't want to copy-paste this same check into five different routes." You write the check once, as its own function, and `Depends(...)` is the one-word instruction that tells FastAPI "run this before the route, every time this route is called."

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

### The folder layout these four files live in

Before looking at any code, here's the actual folder structure being built — this matters because the code below only works if the files sit exactly here, and nothing about this layout was shown before now:

```
fast_api/
    app/
        __init__.py
        main.py
        dependencies.py
        routers/
            __init__.py
            accounts.py
            transfers.py
```

`app/` holds `main.py` and `dependencies.py` directly, and a `routers/` folder sits inside `app/` holding `accounts.py` and `transfers.py`. That nesting is exactly what makes `from app.dependencies import ...` and `from app.routers.accounts import ...` valid later — the dots in `app.routers.accounts` are literally walking down this folder structure, `app/routers/accounts.py`, one slash at a time.

The two `__init__.py` files are completely empty — open one, there's nothing inside it. Historically, their entire job was to tell Python "this folder isn't just a loose pile of scripts, it's an importable package" — without one, older Python versions would refuse `from app.dependencies import ...` entirely. Modern Python (3.3 onward) relaxed this and can actually import a plain folder without an `__init__.py` too (verified this directly rather than assuming it) — but keeping an empty one in every package folder is still the overwhelmingly common real-world convention, including in this demo app, because it's explicit and some tools still expect it. So: create the two empty files exactly where the tree above shows them, and don't worry about them beyond that — they do nothing active, they're just a marker.

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

### What every new piece is actually doing, and why you'd bother writing it

**In `app/dependencies.py`:**

`from fastapi import Header, HTTPException, Query` imports three things used across this file. `Header` reads a value out of the incoming HTTP request's headers — the same idea as `Query` reading one out of the URL's query string, just pointed at a different part of the request.

`db_log: list[str] = []` creates one plain Python list the moment this file is first imported. Because it's written at the top level of the module — not inside any function — every request, from every route in the whole app, shares this exact same list. That's deliberate; it's what lets section 5 and section 8 show a running log across multiple calls.

`VALID_API_KEY = "topsecret123"` is a plain constant standing in for a real secret. A real app would read this from an environment variable or a secrets manager, never hardcode it — a hardcoded string is enough to demonstrate the mechanism itself.

`call_count = {"n": 0}` looks like an odd way to store one number — a dict with a single key, `"n"` — instead of just `call_count = 0`. The reason is a Python scoping rule: inside `count_call()` below, `call_count["n"] += 1` is modifying the dict that already exists, which is always allowed from inside a function. Writing `call_count += 1` on a plain int, instead, would try to create a brand-new *local* variable named `call_count` inside the function, which Python blocks unless you add a `global call_count` line first. Wrapping the number in a dict sidesteps needing `global` at all — a small trick that shows up often in real code.

`def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:` — `Header(default=None)` works exactly like the `Query(...)`/`Field(...)` defaults already used before, except it tells FastAPI "find this value among the request's headers," not the query string or body. FastAPI also does one more thing automatically here: it looks for a header literally named `X-API-Key` (capitalized, hyphenated) even though the Python parameter is named `x_api_key` (lowercase, underscored) — FastAPI converts between the two naming conventions for you, since real HTTP headers traditionally use hyphens and Python names can't. `str | None` is a type hint meaning "a string, or `None`" — the modern shorthand for what doc 02 would have written as `Optional[str]`. The body is two plain `if` checks, each raising `HTTPException` with a 401 status when something's wrong, and `return x_api_key` at the end hands back the validated key string if both checks pass — that return value only matters when this dependency is used per-route rather than router-wide (see section 6).

`def get_account_or_404(account_id: int) -> dict:` takes `account_id` as its only parameter, with no `Query`/`Header` wrapper around it — a bare `int` parameter like this is exactly what tells FastAPI "pull this one from the URL path," the same rule doc 01 already established for route functions themselves. The first line inside the function, `from app.routers.accounts import accounts`, is an import written *inside* the function body instead of up at the top of the file with the others — that's not a style choice, it's required here. `accounts.py` already imports things from this very `dependencies.py` file at its own top (`from app.dependencies import ...`), so if `dependencies.py` also tried to import from `accounts.py` at its own top, Python would hit a circular import — each file waiting on the other to finish loading before it can finish loading itself. This was confirmed for real rather than assumed: writing that same import at the top of this file produces `ImportError: cannot import name 'accounts' from partially initialized module 'app.routers.accounts' (most likely due to a circular import)`. Moving the import inside the function delays it until the function is actually *called*, by which point both files have already finished loading — the circular dependency never actually gets hit.

`class Pagination:` is an ordinary Python class — not a Pydantic `BaseModel` like every class in doc 02. There's no validation happening inside this class at all; `__init__(self, skip: int = 0, limit: int = Query(default=10, le=100))` just stores whatever two numbers it's given as `self.skip` and `self.limit`. The real validation (`le=100`) is still genuinely happening — it's just the `Query(...)` default FastAPI resolves *before* this `__init__` ever runs, not something the class itself checks.

`def count_call() -> int:` increments `call_count["n"]` and returns the new value — nothing else to it. This whole function exists purely to make section 8's dependency-caching demo visible.

`def get_db():` is written with `yield` instead of `return` — the same generator syntax as any other Python generator function, just put to a new use here. `db_log.append("OPEN session")` runs first; `yield session` is the point where this function pauses and hands `session` over to whatever called it (the route); and everything in the `finally` block runs only after the route is completely done with it — guaranteed, even if the route raises an exception along the way (full mechanics in section 5).

**In `app/routers/accounts.py`:**

`from fastapi import APIRouter, Depends` — these are the two central new names this whole doc is built around. `APIRouter` is the class you instantiate to get a "drawer" object (section 1); `Depends` is the function you wrap around another function or class to tell FastAPI "resolve this first, then hand me the result."

`from app.dependencies import Pagination, count_call, get_account_or_404, get_db` pulls four specific names in from the other file — the same `from <module> import <names>` syntax already used for `fastapi`/`pydantic`, just now pointed at this project's own file instead of an installed library.

`router = APIRouter(prefix="/accounts", tags=["accounts"])` is the actual line that creates this file's "drawer." Every `@router...` decorator below this line registers a route onto this one object — not onto the real `app`, which doesn't even exist in this file.

`accounts: dict[...] = {...}` and `next_id` are the same in-memory storage pattern from doc 01/02, just living in this file now instead of a single shared `main.py`.

`@router.get("", response_model=list[AccountOut])` — the decorator is `@router.get`, not `@app.get`, because this route belongs to the router, not the app directly. The path is just `""`, an empty string, because `prefix="/accounts"` already supplies the `/accounts` part — once this router is included into the real app, this becomes `GET /accounts`. `response_model=list[AccountOut]` is new syntax: doc 02 showed `response_model=AccountOut` for one object, and `list[AccountOut]` is the same idea for "a list of that shape" — every item in whatever this route returns gets validated and filtered through `AccountOut`, one at a time.

`def list_accounts(pagination: Pagination = Depends()):` is the actual, literal syntax `Depends()` uses. Writing `Depends()` (or `Depends(Pagination)`, see section 4) as a parameter's default value is what tells FastAPI: "before running `list_accounts`, go build a `Pagination` object first, using whatever `Pagination.__init__` needs from the request, and hand me that finished object as `pagination`." Nothing about the word `Depends` is special Python syntax on its own — it's an ordinary function call, used in a spot (a parameter's default value) where FastAPI specifically goes looking for it.

The `_dependency_cache_demo` route is explained by its own code comment and by section 8 further down — its only job is to make dependency caching visible.

`@router.get("/{account_id}", response_model=AccountOut)` / `def get_account(account: dict = Depends(get_account_or_404)):` — the same `Depends(...)` syntax, this time wrapped around a plain function instead of a class. `account_id` never appears anywhere in `get_account`'s own parameter list — FastAPI sees that `get_account_or_404` (the function `Depends()` points at) needs an `account_id` parameter, and pulls that straight from this route's own URL path (`/{account_id}`) to satisfy it, before ever calling `get_account` itself (full mechanics in section 3).

`@router.post("", status_code=201, response_model=AccountOut)` / `def create_account(account: AccountIn, db: dict = Depends(get_db)):` — `account: AccountIn` is the same request-body pattern from doc 02; `db: dict = Depends(get_db)` is new. Because `get_db` is written with `yield`, FastAPI runs its setup code, hands this route the yielded `session` dict as `db`, and only runs `get_db`'s teardown code once this whole function has returned (section 5).

`update_balance` stacks two `Depends(...)` calls in one signature — `get_account_or_404` and `get_db` both run, independently, before the function body ever executes.

**In `app/routers/transfers.py`:**

`from app.routers.accounts import accounts` reaches into the *other* router file and imports its `accounts` dict directly. This works, and genuinely matters, because Python only loads a module's code once and reuses that same loaded result everywhere it's imported — `accounts.py`'s `accounts` dict is one single dict object, and `transfers.py` importing it here gets a reference to that exact same dict, not a separate copy. That's why a transfer processed through this file is immediately visible if you then call a `GET /accounts/{account_id}` route defined in the other file.

`router = APIRouter(prefix="/transfers", tags=["transfers"], dependencies=[Depends(verify_api_key)])` — the new piece here is `dependencies=[Depends(verify_api_key)]`, passed directly into the `APIRouter(...)` constructor instead of onto one specific route. This is what makes `verify_api_key` run before *every single route* registered on this router, without any of those routes mentioning it themselves (full mechanics in section 6).

`TransferRequest` and its `@model_validator` are unchanged from doc 02 — just relocated into this file, since this is where the transfer route itself now lives.

`create_transfer` is an ordinary route with one `Depends(get_db)` of its own, on top of whatever `verify_api_key` already enforced at the router level before this function was ever reached.

**In `app/main.py`:**

`from app.routers import accounts, transfers` imports the two *modules themselves* — not specific functions or classes out of them, unlike every other import in this doc. This is what makes `accounts.router` and `transfers.router` (used on the next two lines) valid: `accounts` here refers to the whole `accounts.py` file, and `.router` reaches the one router object defined inside it.

`app.include_router(accounts.router)` and `app.include_router(transfers.router)` are the two lines that actually make everything above this point real. Up until this call, `accounts.router` and `transfers.router` are just router objects sitting in their own files, entirely disconnected from the live `app` — `include_router(...)` is what copies every route already registered on that router onto the real `app`, applying that router's own `prefix` and `tags` along the way. Nothing in `accounts.py` or `transfers.py` is reachable over HTTP until these two lines run.

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
