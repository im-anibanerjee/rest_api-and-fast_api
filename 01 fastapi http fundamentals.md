# 01 — HTTP Fundamentals & REST Principles (FastAPI)

This is doc 1 of the FastAPI series. Everything in this doc was run for real against the demo app shown in section 2, using FastAPI's `TestClient` — every status code and every response body you see here is genuine captured output, not something typed from memory. To reproduce any of it yourself, copy the app code from section 2 into a file and run it with `uvicorn` (explained in section 2 — in short, the actual program that makes your FastAPI app reachable over a real network), or drive it with `TestClient` the way this doc's output was captured.

Goal of this doc: understand what actually happens when your React/Node frontend talks to your FastAPI backend — the request/response cycle, HTTP methods, status codes, idempotency, and the core REST ideas — well enough that reading any FastAPI route in your real office codebase stops feeling like magic.

## 1. What an API call actually is

### What "API" even means, before anything else

Simple version: an API is just an agreed-upon way for one piece of software to ask another piece of software to do something, and get an answer back. "API" literally stands for **Application Programming Interface** — but that phrase is more confusing than helpful, so throw it away and keep this instead: it's a *menu*.

Real-life example: when you sit down at a restaurant, you don't walk into the kitchen and cook your own food. You look at a menu, which lists exactly what you're allowed to ask for ("Butter Chicken", "Plain Naan") and in what form (you can ask for "spicy" or "mild", but you can't ask the kitchen to also do your laundry). You tell the waiter what you want, the kitchen does the actual work out of your sight, and the waiter brings back a plate. You never need to know *how* the kitchen cooked it — only what you're allowed to ask for, and what you'll get back.

Real-world use case: your React/Node frontend is "the customer" and your FastAPI backend is "the kitchen." The frontend isn't allowed to reach directly into your PostgreSQL database and grab rows itself (that would be like a customer walking into the kitchen) — instead, it's only allowed to ask for exactly what your FastAPI routes offer (`GET /accounts`, `POST /accounts`, etc. — this is literally "the menu"), and your backend code does the real work (talking to the database) out of the frontend's sight, then hands back an answer.

Technical deep dive: an **API** is a defined set of operations one program can call on another program, each with a fixed shape of input and output, without either side needing to know how the other is internally built. A **REST API over HTTP** (what this whole doc is about) is simply an API where those operations are HTTP requests to specific URLs using specific methods — `GET /accounts` is one "menu item," `POST /accounts` is another. FastAPI's whole job is to let you define that menu (via `@app.get(...)`, `@app.post(...)`, etc.) and handle all the low-level plumbing of actually receiving requests and sending responses, so you only have to write the part that matters: what happens when that menu item is ordered.

Connecting back: so "calling an API" just means "asking the kitchen for something that's actually on the menu, through the waiter" — which, in HTTP terms, is sending a request to a specific URL with a specific method, and waiting for a response. That's exactly what the rest of this section breaks down, step by step.

### The actual mechanics of one API call

When your frontend "calls an API", it is doing exactly this, no more:

1. The browser/frontend code opens a network connection to a server (your FastAPI app) and sends a **request**: a method, a URL, some headers, and optionally a body.
2. The server runs some Python code that decides what to do, and sends back a **response**: a status code, some headers, and optionally a body.
3. The connection closes (or is reused), and that's it. The server does not remember this happened unless it was explicitly told to write something to a database.

Breaking that down further, in plain words, piece by piece:

- **"Opens a network connection to a server"** — your frontend's code (running in the user's browser, or in Node) reaches out, over the internet or a local network, to the actual computer running your FastAPI app. Think of this like picking up a phone and dialing a number — a connection has to be established before you can say anything.
- **"A server"** — this is just the computer (or process on a computer) that's sitting there, running your FastAPI code, waiting for requests to arrive. "Your FastAPI app" and "the server" mean the same thing here, for this doc's purposes.
- **"A request"** — the actual message your frontend sends once connected. It has four parts: a **method** (what kind of thing you want to do — covered fully in section 3), a **URL** (which resource you want — `/accounts/1` means "account number 1"), **headers** (small pieces of metadata about the request itself — covered in section 5), and optionally a **body** (the actual data you're sending, like the new account details on a `POST`).
- **"The server runs some Python code"** — this is the part *you* write. FastAPI looks at the method + URL and finds the matching function you wrote (this matching is called **routing** — more in section 2), then runs it.
- **"Sends back a response"** — the server's answer, with the same basic shape as a request: a **status code** (a 3-digit number saying what happened — full breakdown in section 4), headers, and optionally a body (the actual data you asked for).
- **"The connection closes... and that's it"** — once the answer is sent, nothing is kept around. The server doesn't keep a memory of "oh, this person just asked for account 1" sitting anywhere by default.

That last point is the REST principle called **statelessness**. In even simpler words: imagine a shopkeeper with total amnesia between customers — every single time you walk up to the counter, you have to tell them your name and what you want all over again, because they genuinely don't remember you from thirty seconds ago, even if you were just there. That's your API server. Every request must carry everything the server needs to handle it (who you are, what you want) — the server is not sitting there "remembering" that you're logged in from your last click. That's exactly why auth tokens get sent on *every* request, not just once at login (more on this in section 5, and in full depth in doc 09 on OAuth2/JWT) — there's no memory to rely on in between.

### What "JSON" means, since it's about to come up constantly

Simple version: JSON is just a plain-text way of writing down structured information — like a form with labeled boxes — that both humans and computers can read easily.

Real-life example: `{"id": 1, "holder": "Ravi Kumar", "balance": 5000.0}` is JSON for "account number 1, held by Ravi Kumar, with a balance of 5000.0" — same information as a filled-out form, just written with curly braces, colons, and commas instead of boxes and lines.

Technical deep dive: **JSON** stands for **JavaScript Object Notation** — it's a text format for representing data as key-value pairs (`"holder": "Ravi Kumar"`), lists, numbers, strings, booleans, and nulls, nested as deep as you need. It's the near-universal format for request and response bodies in modern APIs (FastAPI reads and writes it automatically, which is most of what makes it convenient) — but it's worth remembering JSON is just *text* under the hood, no different in principle from a `.txt` file; it just follows strict punctuation rules so every program parsing it agrees on what it means.

### What a raw request and response actually look like, travelling over the wire

A request and a response are both just **text** over the wire (HTTP is a text-based protocol — meaning the actual bytes sent between your frontend and your server are plain, readable text, not some mysterious binary format — even though bodies are usually JSON these days). Here's the literal shape of one request/response pair from the demo, written out the way it actually travels over the network, broken down line by line below it:

```
Request:
  GET /accounts/1 HTTP/1.1
  Host: localhost:8000

Response:
  HTTP/1.1 200 OK
  content-type: application/json

  {"id":1,"holder":"Ravi Kumar","balance":5000.0}
```

Line by line, in plain words:
- `GET /accounts/1 HTTP/1.1` — the method (`GET`), the path (`/accounts/1`), and which version of the HTTP protocol is being spoken (`HTTP/1.1` — you don't need to worry about version numbers for this doc; just know every request states one).
- `Host: localhost:8000` — a header saying which actual server (by address) this request is meant for; `localhost` means "this same computer," `8000` is the specific port (a numbered "door" on that computer) the FastAPI app happens to be listening on.
- (a blank line) — in the real HTTP format, a blank line is what separates the headers from the body. This particular GET request has no body at all, so nothing follows.
- `HTTP/1.1 200 OK` — the response's first line: same protocol version, then the status code (`200`) and its standard short text label (`OK`).
- `content-type: application/json` — a response header telling the receiver "the body you're about to read is JSON, parse it that way."
- (a blank line, then) `{"id":1,"holder":"Ravi Kumar","balance":5000.0}` — the actual response body, in JSON, as plain text.

Everything else in FastAPI — routers, dependency injection, Pydantic models — exists to make building *this* easier and safer. Keep this picture in your head; it's the foundation for every doc that follows.

## 2. The demo app

This is the full demo app every example in this doc was run against — a tiny in-memory "accounts" API (no real database yet; that's doc 06):

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

### What every line of this is actually doing, and why you'd bother writing it

Before any HTTP concepts, it's worth being completely literal about what each piece of this file does — not just mechanically, but *why anyone would write that line in the first place*. Everything after this section just points back into it.

**The app object and the "database":**

Simple version: before you can open a shop, you first need to actually open the shop — switch the lights on, hang the "open" sign. Nothing can be registered or sold until that exists.

```python
app = FastAPI(title="Demo Accounts API")
```
This one line is "open the shop." It creates the actual running application object. Every `@app....` decorator below registers itself onto this exact `app` object.

**What "uvicorn" actually is, since it keeps coming up:**

Simple version: writing the `app` object above is like writing a complete, ready-to-cook recipe. It's not cooking anything by itself — you still need an actual stove to put it on. `uvicorn` is the stove.

Real-life example: your FastAPI code (`app = FastAPI(...)`, the routes) describes *what* should happen for each kind of request — it's pure Python, sitting on disk, not doing anything on its own. For a real browser or a real frontend to actually reach it over a network, something has to literally open a network port, listen for incoming connections, read the raw bytes of each HTTP request, and hand them to your FastAPI code to process — then take whatever your code returns and write it back out as real HTTP bytes. That "something" is `uvicorn`.

Technical deep dive: `uvicorn` is a separate Python package — an **ASGI server** (ASGI is just the technical name for the standard way Python web frameworks and servers agree to talk to each other; you don't need more than that right now). You run it from a terminal, typically as `uvicorn app:app --reload`, pointing it at your file (`app.py`, say) and the variable name of your FastAPI object inside it (`app`). Once running, it genuinely opens a network port (commonly `8000`, like in section 1's raw example) and keeps running, waiting for real requests, until you stop it. This doc never actually needed `uvicorn` to produce any of its output — section 2's walkthrough covers why `TestClient` was used instead (it calls your routes directly, in-process, without needing a real open network port at all) — but in your actual job, and once you start building FastAPI's own standalone project later in this phase, `uvicorn` (or something that wraps it, like Docker eventually will) is what's actually running at all times, keeping your API reachable.

Connecting back: so `app = FastAPI(...)` is the recipe, your route functions are the individual cooking steps, and `uvicorn` is the stove that actually plugs them into the real world of network requests. `title` on the `FastAPI(...)` call is just a label — it shows up on the auto-generated docs page FastAPI builds for you for free at `/docs` once something like `uvicorn` is actually serving the app, worth opening once you try this yourself.

Simple version: a real app needs somewhere to actually keep its data. A real database is the proper tool for that, but for a tiny demo like this, a database is overkill — so this just uses a sticky-note board instead: a couple of notes already stuck on it, and a reminder of what number to write on the next new note.

```python
accounts: dict[int, dict] = {
    1: {"id": 1, "holder": "Ravi Kumar", "balance": 5000.00},
    2: {"id": 2, "holder": "Priya Shah", "balance": 3000.00},
}
next_id = 3
```
`accounts` IS the entire "database" for this demo — a plain Python dictionary, keyed by account id, where each value is itself a dictionary of that account's fields. `dict[int, dict]` is only a type hint (for you and your editor); Python does not enforce it at runtime. `next_id` is a plain integer tracking what id the *next* created account should get — it starts at 3 because ids 1 and 2 are already taken. Because this is just a variable sitting in the running process's memory (not a real sticky-note board, not a file, not a database), it resets to exactly this starting state every time the process restarts — nothing here actually persists. That's deliberate for this demo; doc 06 replaces this dict with a real PostgreSQL table that *does* persist.

**The two Pydantic models:**

Simple version: before you let someone into a building, you want a bouncer at the door checking their paperwork is actually filled in — "do you have a name, do you have an ID" — rather than letting anyone in and finding out something's missing once they're already inside causing problems.

```python
class AccountIn(BaseModel):
    holder: str
    balance: float


class AccountUpdate(BaseModel):
    balance: float
```
These two classes are that bouncer's checklist. Doc 02 goes deep on what `BaseModel` is actually doing; the minimum you need now is: declaring a class like this tells FastAPI "a valid request body for this route must have a `holder` that's a string and a `balance` that's a number — nothing missing, nothing extra, by default." Why two separate checklists instead of one? Because creating a new account and updating an existing one need different paperwork — creating needs a name AND a balance (`AccountIn`), but updating a balance only needs the new number, not the holder's name all over again (`AccountUpdate`). Using the smaller checklist where it fits is just not asking for information you don't need.

**Every route — what it's actually for, what triggers it, and what each line does:**

Simple version: you need a "look up a group of customers" counter at the bank, and sometimes the customer wants to filter — "only show me accounts with at least ₹4000 in them" — rather than being handed every single account and having to scan through them by hand.

```python
@app.get("/accounts")
def list_accounts(min_balance: float | None = Query(default=None)):
```
`@app.get("/accounts")` registers this function to run whenever a GET request arrives for exactly the path `/accounts` — that's **routing**: the (method, path) pair is the key, this function is the value. `min_balance: float | None = Query(default=None)` means: look for a query-string parameter named `min_balance` (the part after `?` in a URL, e.g. `/accounts?min_balance=4000`); default to `None` if nobody asked for a filter; if present, convert it to `float` automatically — and reject the request with a 422 if it can't be converted (e.g. `?min_balance=abc`), before this function body ever runs. Doing the filtering on the server, instead of sending every account to the frontend and letting it filter, matters for real APIs: you don't want to ship your entire customer list over the network just to throw most of it away on the other end.

```python
    if min_balance is not None and min_balance < 0:
        raise HTTPException(status_code=400, detail="min_balance cannot be negative")
    results = list(accounts.values())
    if min_balance is not None:
        results = [a for a in results if a["balance"] >= min_balance]
    return results
```
The first check exists because "show me accounts with a balance of at least -5" makes no real-world sense — it's a business rule *we* chose to enforce ourselves, which is exactly why it's a 400 and not a 422 (FastAPI's own validation had nothing to do with rejecting it; see section 4).

`accounts.values()` pulls every account out of the sticky-note board — worth seeing exactly what that actually gives you back, since it's not quite a plain list on its own:

```
accounts.values()
dict_values([{'id': 1, 'holder': 'Ravi Kumar', 'balance': 5000.0}, {'id': 2, 'holder': 'Priya Shah', 'balance': 3000.0}])
```

Breaking that down: `.values()` on a dict gives you back only the values — not the keys (the account ids `1` and `2` are dropped here), just the two dictionaries that were stored under those keys. It doesn't come back as a plain `list` — it's a special object called a `dict_values` view, which just means "a live window onto the dict's current values" (if the dict changes later, this view reflects the change automatically — you don't need to call `.values()` again). It's printed with a `dict_values([...])` wrapper around it so you can see what type it is, but notice the actual content inside those square brackets is exactly the two account dicts, in the order they were inserted — one value per key in the dict, comma-separated, in insertion order, regardless of what type each value happens to be.

That's why the code wraps it in `list(...)`: `list(accounts.values())` converts that special view into an ordinary Python list — `[{'id': 1, ...}, {'id': 2, ...}]` — which is what `results` actually becomes in `list_accounts()`, so the rest of the function (filtering, returning) can treat it like any normal list. It's a `list` only after that explicit `list(...)` wrap — on its own, `.values()` gives back the `dict_values` view, which behaves like a list you can loop over or print, but isn't technically a `list` object until you convert it.

`[a for a in results if a["balance"] >= min_balance]` is a **list comprehension** — plain Python shorthand for "build a new list by going through `results` one item at a time (`a`), and only keeping the ones where the condition after `if` is true." It's exactly the same idea as a `for` loop with an `if` check inside it that appends to a new list — just written on one line, which is an extremely common pattern in real Python code, not FastAPI-specific at all.

Whatever this function `return`s, FastAPI automatically **serializes** it to JSON and sends it back as the response body. "Serialize" just means "convert a real, in-memory Python object (a list of dicts, here) into plain text that can actually travel over a network" — the reverse of what happens to an incoming JSON body when it becomes a real Python/Pydantic object. You never call anything like `response.send()` yourself; the return value *is* the response, and FastAPI handles turning it into bytes on the wire.

Simple version: this is the "look up one specific customer by their account number" counter — like a bank teller who asks for your account number and goes straight to your folder, instead of handing you the entire filing cabinet to search through yourself.

```python
@app.get("/accounts/{account_id}")
def get_account(account_id: int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    return accounts[account_id]
```
`{account_id}` in the decorated path is a placeholder — FastAPI matches it against whatever's actually in the URL (`/accounts/1` → the raw string `"1"`), then converts it to `int` because that's the parameter's type hint, rejecting with a 422 if it isn't a valid integer at all (`/accounts/abc`) — same validate-before-your-code-runs idea as the body case, just applied to a piece of the URL instead. Once `account_id` is a real Python `int`, the function body is just a dict lookup — why bother checking `if account_id not in accounts` first, rather than just looking it up directly? Because looking up a missing dict key crashes with a real Python error; checking first lets us hand back a clean, deliberate 404 instead of an ugly server crash. `raise HTTPException(...)` is how you deliberately produce a non-200 response from inside your own code — raising it stops execution right there, and FastAPI turns it into the response described by that `status_code`/`detail`.

Simple version: this is the "open a brand-new account" counter — the one and only place in this whole file that invents a new id. Every other route works on an account that already exists; this is the exception that creates one from scratch.

```python
@app.post("/accounts", status_code=201)
def create_account(account: AccountIn):
    global next_id
    new_account = {"id": next_id, "holder": account.holder, "balance": account.balance}
    accounts[next_id] = new_account
    next_id += 1
    return new_account
```
`status_code=201` overrides FastAPI's default of 200 for this one route — convention is 201 for a POST that creates something, so the frontend can tell "created" apart from "just fetched." `account: AccountIn` is the request body — FastAPI reads the incoming JSON, runs it past the bouncer's checklist from above (this is exactly where the 422 in section 4 actually gets raised, before this line of code ever runs), and hands you a real Python object with real attributes (`account.holder`, `account.balance`) — no manual `json.loads()` anywhere in sight. Why `global next_id`? Because this function changes `next_id` (`next_id += 1`), and without telling Python "I mean the one outside this function," Python would quietly create a brand-new, separate `next_id` that only exists inside this one call and throw it away afterward — leaving the real counter outside never incremented. That's the same scoping rule the Python docs' `global` coverage already walked through, just showing up here inside a route.

**Where does that "incoming JSON" actually come from, concretely?**

Everything so far described what happens once a request has already arrived. It's worth pinning down exactly where that request itself comes from, and how you could send one yourself, right now, without needing a frontend at all. To make this concrete, this app was actually started for real with `uvicorn` (the stove, from earlier) on `127.0.0.1:8010` (`127.0.0.1` means "this same computer," `8010` is just the port number it happened to be listening on), and then sent real requests at it from three different directions.

*1. The raw bytes a request actually is, captured with `curl -v` (a command-line tool for sending HTTP requests, with `-v` for "verbose" — show me everything, not just the answer):*

```
> POST /accounts HTTP/1.1
> Host: 127.0.0.1:8010
> User-Agent: curl/8.5.0
> Accept: */*
> Content-Type: application/json
> Content-Length: 45
>
} [45 bytes data]
< HTTP/1.1 201 Created
< date: Sat, 17 Oct 2026 10:51:25 GMT
< server: uvicorn
< content-length: 49
< content-type: application/json
<
{ [49 bytes data]
```

Lines starting with `>` are what was *sent*; lines starting with `<` are what came *back*. `Content-Type: application/json` is the header telling FastAPI "the body I'm about to send you is JSON — parse it that way" (this is exactly what lets FastAPI know to run it through `AccountIn`'s validation at all). `Content-Length: 45` just says how many bytes the body is, so the server knows when it's finished receiving it. Everything else (`User-Agent`, `Accept`, `Host`) is routine metadata `curl` adds automatically — a real browser or frontend library adds its own equivalents without you writing them by hand.

*2. Sending that request with `curl` directly from a terminal — no frontend, no browser, nothing but a single command:*

```
curl -i -X POST http://127.0.0.1:8010/accounts \
  -H "Content-Type: application/json" \
  -d '{"holder": "Dev Patel", "balance": 1200.0}'
```

Real output:
```
HTTP/1.1 201 Created
date: Sat, 17 Oct 2026 10:51:20 GMT
server: uvicorn
content-length: 46
content-type: application/json

{"id":3,"holder":"Dev Patel","balance":1200.0}
```

`-X POST` sets the method, `-H` adds a header, `-d` supplies the body — that's the entire recipe for sending any request by hand, for any route in this doc, any time you want to try something without a frontend. This is genuinely the fastest way to test a single endpoint while you're developing one.

*3. The way your actual frontend would do this — a real Node `fetch` call, run for real against the same server:*

```javascript
const response = await fetch("http://127.0.0.1:8010/accounts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ holder: "Frontend Caller", balance: 777.0 }),
});

console.log("status:", response.status);
const body = await response.json();
console.log("body:", body);
```

Real output:
```
status: 201
body: { id: 5, holder: 'Frontend Caller', balance: 777 }
```

This is structurally identical to what `axios.post("/accounts", {...})` does in section 7, and to what `client.post("/accounts", json={...})` did throughout this whole doc via `TestClient` — `method`, `headers`, and `body` are the exact same three ingredients every single time, however the request happens to get sent. `JSON.stringify(...)` is JavaScript's equivalent of Python's `json.dumps()` — turning a real in-memory object into JSON text before it's sent, which is the client-side half of the "serialize"/"deserialize" pair discussed earlier in this section.

One more option worth knowing about, without needing any of the above: FastAPI automatically builds an interactive page at `/docs` for any running app (mentioned back when `title=` was explained) — opening `http://127.0.0.1:8010/docs` in a browser while the server is running gives you a clickable "Try it out" button for every single route, where you can type in a body and fire a real request straight from the browser, no `curl` or code required. Worth opening once you have this running yourself.

Simple version: this is the "correct this account's balance to this exact number" counter — like crossing out a typo on a form and writing the right number, not adding a new line underneath it.

```python
@app.put("/accounts/{account_id}")
def replace_balance(account_id: int, update: AccountUpdate):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    accounts[account_id]["balance"] = update.balance
    return accounts[account_id]
```
Same path-parameter and body-validation mechanics as `POST` above, just combined on one route — `account_id` comes from the URL, `update` comes from the JSON body (checked against the smaller `AccountUpdate` checklist). The actual "replace" is one line: overwrite `balance` with whatever was sent, unconditionally — no counter, no `+=`, nothing that depends on how many times this has already run. That unconditional overwrite is exactly *why* PUT is idempotent (section 3).

Simple version: this is the "close this account" counter.

```python
@app.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    del accounts[account_id]
    return None
```
`status_code=204` again overrides the default, matching the "No Content" convention — once something's deleted, there's nothing left to show you, so why send back a body at all? `del accounts[account_id]` is plain Python dict deletion — nothing FastAPI-specific. Returning `None` here isn't optional style — FastAPI won't let a 204 response carry a body at all (section 4), so returning anything with real content on a `status_code=204` route would be a framework-level error, not just an unconventional choice.

Simple version: this simulates a locked door. You need the right key (a header) to get in, and the doorman checks two separate things, in a specific order: do you even have a key at all, and only if you do, is it the *right* key?

```python
@app.get("/secure-accounts")
def secure_list(x_api_key: str | None = Header(default=None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if x_api_key != "secret-admin-key":
        raise HTTPException(status_code=403, detail="This key is not allowed to view secure accounts")
    return list(accounts.values())
```
`Header(default=None)` is the header equivalent of `Query(default=None)` above — it pulls a value out of the request's headers instead of the query string or body, because a credential like this belongs with the "metadata about the request," not mixed into the actual data (section 5 explains why). FastAPI automatically matches the Python parameter name `x_api_key` to the real HTTP header `X-API-Key`. The two `if` checks, run in that exact order (no key at all, THEN wrong key), are the whole 401-vs-403 decision tree traced in section 4's diagram — and that order matters, not just for correctness but so a wrong-key attempt can never accidentally be mistaken for "no key presented."

**What exactly is `x_api_key`, what header name does it come from, and what value makes each branch run? Run for real against the live server, not guessed:**

`x_api_key` is just a plain Python variable name — a parameter of the `secure_list` function, nothing more. It is NOT the header's name; it's where FastAPI *puts* the header's value once it's found it. The actual header name a caller must send is `X-API-Key` (with those exact hyphens) — FastAPI converts between the two automatically: the real HTTP header `X-API-Key` (hyphens, because HTTP headers conventionally use hyphens) becomes the Python parameter `x_api_key` (underscores, because hyphens aren't legal in a Python variable name). Whatever string value arrives in that header is what ends up *inside* `x_api_key` when the function runs — if the caller sends `X-API-Key: secret-admin-key`, then inside the function, `x_api_key` literally holds the string `"secret-admin-key"`, as if you'd written `x_api_key = "secret-admin-key"` yourself.

Three real requests against the running demo app, varying only the header, prove exactly which value lands in which branch:

*No `X-API-Key` header sent at all:*
```
curl -i http://127.0.0.1:8011/secure-accounts
```
```
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Missing X-API-Key header"}
```
Here, `x_api_key` is `None` (that's exactly what `Header(default=None)` means — "if this header is missing, give me `None` instead of erroring") — so the first `if x_api_key is None:` check is true, and the function stops at the 401 before even reaching the second check.

*`X-API-Key: wrong-key` sent:*
```
curl -i http://127.0.0.1:8011/secure-accounts -H "X-API-Key: wrong-key"
```
```
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"This key is not allowed to view secure accounts"}
```
Now `x_api_key` holds the real string `"wrong-key"` — not `None` anymore, so the first check passes straight through — but it doesn't equal the hardcoded `"secret-admin-key"` the second check compares against, so it fails there instead, landing on 403.

*`X-API-Key: secret-admin-key` sent — the one and only value that passes both checks:*
```
curl -i http://127.0.0.1:8011/secure-accounts -H "X-API-Key: secret-admin-key"
```
```
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"holder":"Ravi Kumar","balance":5000.0},{"id":2,"holder":"Priya Shah","balance":3000.0}]
```
`x_api_key` now holds `"secret-admin-key"`, exactly matching the string the code compares it against — both `if` checks fail to trigger (there IS a key, and it IS the right one), so execution falls through to `return list(accounts.values())` and the real account data comes back.

One more real detail worth confirming rather than assuming: HTTP header *names* (not their values) are case-insensitive, so sending the header as lowercase `x-api-key: secret-admin-key` instead of `X-API-Key: secret-admin-key` still works identically —
```
curl -i http://127.0.0.1:8011/secure-accounts -H "x-api-key: secret-admin-key"
```
```
HTTP/1.1 200 OK
```
— same 200, because FastAPI (like HTTP itself) treats `X-API-Key` and `x-api-key` as the exact same header. The *value* `"secret-admin-key"` on the other side of the colon is compared with ordinary Python string equality (`!=`), which is fully case-sensitive — `"Secret-Admin-Key"` would NOT match and would still 403, only the header's own name ignores case, never the value you're actually checking.

Simple version: every programmer eventually ships a real bug — this route isn't a feature at all, it exists purely to show you, on purpose and safely, what that actually looks like from the outside.

```python
@app.get("/boom")
def boom():
    return 1 / 0
```
No `HTTPException`, no validation, nothing deliberate about producing an error response — `1 / 0` just raises a real Python **exception** (a `ZeroDivisionError`, specifically), exactly as it would in any ordinary script. In plain words, an exception is Python's way of saying "something went wrong and I cannot continue running this line normally" — it immediately stops whatever function it happened in and looks for some surrounding code that said "if something goes wrong here, do this instead" (that's what `try`/`except` is for, and what `raise HTTPException(...)` is actually doing deliberately everywhere else in this file). Nothing here catches it. That's the entire point: showing what happens when your own code genuinely breaks and nobody wrote a `try`/`except` for it (section 4's 500), without you having to wait for a real bug in a real project to see it.

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

**Flow diagram — why the two methods leave the world in different states:**

```
POST /accounts {"holder": "Dev Patel", "balance": 1200.0}   -- called TWICE, same body

Call 1:
    accounts BEFORE                    accounts AFTER
    ┌──────────────────────┐           ┌──────────────────────┐
    │ 1: Ravi Kumar         │           │ 1: Ravi Kumar         │
    │ 2: Priya Shah         │    -->    │ 2: Priya Shah         │
    └──────────────────────┘           │ 3: Dev Patel  (NEW)   │
    next_id = 3                        └──────────────────────┘
                                        next_id = 4   (bumped)

Call 2 (identical body):
    accounts BEFORE                    accounts AFTER
    ┌──────────────────────┐           ┌──────────────────────┐
    │ 1: Ravi Kumar         │           │ 1: Ravi Kumar         │
    │ 2: Priya Shah         │    -->    │ 2: Priya Shah         │
    │ 3: Dev Patel          │           │ 3: Dev Patel          │
    └──────────────────────┘           │ 4: Dev Patel  (NEW, again) │
    next_id = 4                        └──────────────────────┘
                                        next_id = 5

POST reads next_id, creates a brand-new entry at that id, and bumps the
counter — every call changes the state DIFFERENTLY, even with
byte-identical input. That's non-idempotency, mechanically.

----------------------------------------------------------------------

PUT /accounts/1 {"balance": 9999.0}   -- called TWICE, same body

Call 1:  accounts[1].balance   5000.0  -->  9999.0
Call 2:  accounts[1].balance   9999.0  -->  9999.0   (overwritten with itself)

PUT doesn't read a counter or add anything — it just overwrites
accounts[1]["balance"] with exactly what the body says. Overwriting a
value with itself leaves the world looking identical to calling it
once. That's idempotency, mechanically.
```

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

**Flow diagram — the actual decision tree `secure_list()` runs on every call:**

```
GET /secure-accounts

              Is there an X-API-Key header at all?
                          │
          ┌────────────── NO ───────────────┐
          │                                   │
         YES                            401 Unauthorized
          │                      "I don't know who you are"
          ▼                        (no identity presented at all)
   Does the key equal "secret-admin-key"?
          │
   ┌───── NO ──────┐
   │                 │
  YES          403 Forbidden
   │       "I know who you are, and
   ▼        the answer is still no"
200 OK         (a real, recognized,
(key matches,   but insufficient key)
 access granted)
```

The two checks run in a fixed order — "do you exist" before "are you allowed" — which is why a request with NO key can never accidentally land on 403, and a request with a WRONG key can never accidentally land on 401. Get this order backwards in your own code later and you'll leak information about which usernames/keys are even real.

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

**Flow diagram — the exact order of operations, and why `create_account()`'s own code never runs:**

```
POST /accounts   body: {"holder": "No Balance Field"}        <- "balance" missing

Step 1: FastAPI receives the raw bytes and parses them as JSON.
Step 2: FastAPI inspects create_account()'s signature and sees it
        declares one parameter: account: AccountIn.
Step 3: FastAPI hands the parsed JSON to AccountIn for validation -
        this happens BEFORE create_account()'s body executes a
        single line.
Step 4: AccountIn requires "holder" (str) and "balance" (float).
        "holder" is present and correctly typed. "balance" is
        missing entirely.
Step 5: Validation FAILS right here, inside FastAPI's own machinery.
        A 422 response is built, describing exactly which field
        failed and why, and sent back immediately.
Step 6: create_account()'s own code --
            global next_id
            new_account = {...}
            accounts[next_id] = new_account
            next_id += 1
        -- NEVER RUNS. The function body is not reached at all.

This is why a 422 can never corrupt your data: if the shape of the
request is wrong, the part of your route that actually touches
accounts/the database doesn't get a chance to run in the first place.
```

**500 Internal Server Error** — the server itself crashed on an exception nobody caught:
```
--- GET /boom (500) ---
status: 500
body (raw): Internal Server Error
```
The route does `return 1 / 0`, a plain Python `ZeroDivisionError` (an exception — see section 2's `/boom` explanation for what that word means). Nothing in the route catches it, so FastAPI's default behavior is to turn *any* unhandled exception into a generic 500 with no detail about what actually broke. That's deliberate, and worth understanding why: a **stack trace** is the detailed, line-by-line record of exactly what your code was doing when it crashed — which file, which function, which variables. That's incredibly useful to *you* while debugging, but genuinely dangerous to show a stranger on the internet, since it can reveal your file structure, library versions, or even snippets of your own logic — information an attacker could use. That's called an **information-disclosure risk**: leaking information you didn't mean to, just by being too helpful in an error message. So FastAPI deliberately hides all of that from the client and shows a plain "Internal Server Error" instead — while still keeping the real exception and full traceback logged on the server itself, where only you (not the public internet) can see it, for you to actually debug.

A note on how this specific example was captured: by default, FastAPI's `TestClient` re-raises the exception in the test process itself, rather than quietly turning it into a 500 — useful when you're writing pytest tests and want a failure to show you the real traceback immediately. To see the *actual* HTTP-level 500 a real browser would get instead, the client here was built with `TestClient(app, raise_server_exceptions=False)` (see the methodology section at the end of this doc for the full detail on this). Doc 10 (middleware) and later docs cover writing custom exception handlers so a 500 can return a consistent JSON error shape instead of this plain-text default.

## 5. Headers: metadata about the request/response, not the content itself

A header is a key-value pair sent alongside the request or response, separate from the body. Some headers are standard and handled by the framework automatically (`Content-Type`, `Content-Length`); some are custom and you define their meaning yourself. The demo's `/secure-accounts` endpoint reads a custom header:

```python
@app.get("/secure-accounts")
def secure_list(x_api_key: str | None = Header(default=None)):
```

FastAPI converts `X-API-Key` (the real HTTP header name, case-insensitive, hyphenated) into the Python parameter `x_api_key` (underscored) automatically — that naming conversion is a FastAPI convention worth remembering so header-based code doesn't look mysterious later.

Why headers and not query params or body for things like this? Because headers are the conventional place for information *about* the request, rather than the actual data the request is carrying. A few examples of what that means in practice, in plain words: authentication tokens ("who is making this request"); **content negotiation** — headers like `Accept` and `Content-Type`, which just mean "what format am I sending/expecting back, JSON or something else"; **correlation/tracing IDs** — a unique ID attached to a request purely so that if it passes through several different backend services, you can find all the related log lines across every one of them afterward, like a tracking number for a request instead of a package; and caching directives — headers telling browsers/proxies things like "you're allowed to remember this response for 5 minutes instead of asking again." None of these are "the data" the frontend actually wants — they're metadata *about* the asking, which is exactly why they travel separately from the body. The real `Authorization: Bearer <token>` header you'll build in doc 09 works exactly the same mechanical way as `X-API-Key` does here; only the parsing and validation logic gets more involved.

## 6. REST, concretely

"REST" gets thrown around vaguely, but concretely, the ideas this demo already follows are:

- **Resources are nouns, identified by URLs.** `/accounts` is the collection, `/accounts/1` is one specific account. The *method* (GET/POST/PUT/DELETE) carries the verb, not the URL. A URL like `/getAccount?id=1` or `/deleteAccount` is the anti-pattern — if you ever see that in older code, that's **RPC-style** thinking leaking into what's supposed to be REST. In plain words: RPC ("Remote Procedure Call") is an older style where a URL is basically just the *name of a function* you're calling remotely ("get-account", "delete-account") — the verb lives in the URL itself, and every URL is its own one-off action. REST deliberately moves the verb into the HTTP method instead, so the URL only ever has to name *what thing* you mean (`/accounts/1`), not *what you're doing to it* — that's what makes `GET /accounts/1` and `DELETE /accounts/1` reuse the exact same URL instead of needing two different ones.
- **Uniform interface.** Every resource in this API is manipulated with the same five verbs. You don't invent `/accounts/1/remove` when DELETE `/accounts/1` already means that.
- **Representations, not the resource itself.** The client never gets the actual Python dict from the server's memory — it gets a JSON *representation* of it. This is why the response for `GET /accounts/1` and the internal `accounts[1]` dict happen to look identical here (we didn't bother hiding any fields in this toy example), but in a real API you'll often return a different shape than what's stored (e.g., never return a password hash even though it's a real column).
- **Statelessness** (section 1) — nothing here depends on "the previous request." Each call to `/accounts/1` carries everything needed to answer it.

What this demo does *not* yet show, on purpose, because they need their own docs — explained briefly here just so the words aren't a total mystery when you hear them:
- **Pagination** — when `/accounts` has 2 rows, returning all of them is fine; when it has 2 million, you'd never return them all in one response. Pagination means returning a small page at a time (e.g. "give me rows 1-50"), with some way to ask for the next page.
- **Nested resources** (`/accounts/1/transactions`) — a URL shape for "things that belong to a specific other thing" — "the transactions that belong to account 1," read as a path, left to right.
- **HATEOAS-style links** (rarely used in practice — don't worry about this one) — an idea where a response itself contains links to related actions you could take next (e.g. the account response also includes a link to its own transactions), so a client doesn't need to know any URL structure in advance. Mentioned only because you may hear the term; it's genuinely rare in real APIs.
- **Versioning** (`/v1/accounts`) — putting a version number in the URL so that when you change how an endpoint behaves, old frontend code calling `/v1/accounts` keeps working exactly as before, while new code can call `/v2/accounts` for the new behavior.

You'll meet these as they come up in the real work-project deep dive later in the roadmap.

## 7. How this maps to your actual job

Your real frontend (React/Node) talks to your real FastAPI backend using exactly this mechanism — `fetch` and `axios` are simply the names of the tools JavaScript code uses to actually send an HTTP request (the same way `TestClient` was used to send one from Python throughout this doc) — so a line like `axios.post("/accounts", {...})` in your frontend code is doing exactly what `client.post("/accounts", json={...})` did here, just from the browser side instead of from a test script. Those calls are GET/POST/PUT/DELETE requests to specific URLs, and your backend routes handle them with functions that look structurally identical to the ones in this demo (just backed by PostgreSQL instead of a dict, which is doc 06). When you're reading an existing route in your office codebase and see `@router.post("/something", status_code=201)`, you now know precisely what every piece of that means: it's registering a non-idempotent, non-safe handler for creating something, and 201 is the convention for "created successfully, here's what you created." When something in the frontend shows an error, checking whether it's a 4xx or 5xx immediately tells you which side of the wire to go debug first.

## Interview questions

These are the kind of questions this topic actually draws in an interview — conceptual, meant to be answered out loud without looking anything up. Every one of them is answerable straight from what's above; work through them from memory first, then check back against the doc for anything shaky. No answers are given here on purpose — say them out loud or write them out, and share them if you want them checked.

1. What's the difference between a request being "safe" and a request being "idempotent"? Give one method that's idempotent but not safe, and explain why.
2. Why is DELETE idempotent even though it's not safe?
3. If a frontend sends a login request with the wrong password, should the response be 401 or 403? What if the password is right but the account isn't allowed to perform that specific action?
4. Why can a request with zero credentials never correctly be a 403?
5. What's actually different, mechanically, between a 400 and a 422 — why can't `min_balance=-5` just be a 422 too, and why can't a missing `balance` field just be a 400?
6. Why does FastAPI reject `POST /accounts` with a missing field before `create_account()`'s own code ever runs? What's the practical benefit of that order?
7. Why should a 500 response never include the real exception message or stack trace to the client? Where does that information actually go instead?
8. Why does a GET endpoint need to avoid changing server state, even if it would be convenient for it to do so?
9. What's the risk of a frontend retrying a POST request after a network timeout, and how would you defend against it?
10. What's the practical difference between a header and a query parameter — why does an API key go in a header instead of `?api_key=...`?
11. What does "statelessness" mean for an HTTP API, and why does an auth token have to be sent on every single request instead of just once at login?
12. Why is `/getAccount?id=1` or `/deleteAccount` considered bad REST design compared to `GET /accounts/1` and `DELETE /accounts/1`?
13. If your frontend shows an error, what's the first thing the status code tells you about which side of the system to go debug?

## Practice questions

Attempt these yourself first — copy the demo app from section 2 into your own file, extend it, run it for real, and see what happens before checking anything. Then share your code and real output for a check.

1. **Predict, then verify.** Add a new endpoint, `PATCH /accounts/{account_id}/holder`, that updates only the `holder` name on an existing account (leave `balance` untouched). Before you write a single line, answer: should this be idempotent? Is it safe? Write it, run it twice with the same body, and confirm your prediction against the real output.

2. **Add a validation rule and trigger the real error.** Right now `AccountIn` accepts a negative `balance` on `POST /accounts` with no complaint. Add a Pydantic validator (or a field constraint) so creating an account with a negative balance fails — then actually create one with `balance: -50` and capture the real error response. Is it a 400 or a 422? Why does it come out that way given what section 4 explained about where each one originates?

3. **Confirm 404 is consistent.** `GET /accounts/999` and `DELETE /accounts/999` should both 404 for the same reason. Run both for real against an account id that was never created, and explain in your own words why the delete route has to check for existence even though "deleting something that's already gone" is supposed to be harmless (idempotent) — what would go wrong if `delete_account()` skipped that check and just did `del accounts[account_id]` unconditionally?

4. **Cause a genuine 500 on purpose, on a different endpoint than `/boom`.** Add a new endpoint that takes a body (e.g. a `POST /accounts/{account_id}/apply-bonus` that divides the new balance by some caller-supplied number) and feed it an input that makes it crash with an unhandled exception. Run it for real, confirm you get a plain 500 with no detail — then explain why this is a 500 and not a 422, given that the *shape* of the request body was perfectly valid.

5. **Explain the 401 vs 403 decision tree in your own words**, in writing — not just "401 is this, 403 is that," but walking through the actual order `secure_list()` checks things in, and why swapping that order would be a real security mistake (what would a wrong-key request incorrectly reveal if the key check ran before the "is there a key at all" check?).

### "The questions that you gave to solve, how to run the code?"

That was the real question asked after seeing the 5 practice questions above, and it's worth keeping the full answer here rather than only in chat, since every future practice-question set in this series needs the same setup.

**1. Open a terminal and go to the repo folder.**
```
cd /d "D:\interview prep\fast_api"
```
(The `/d` matters — plain `cd` to a different drive letter in Windows Command Prompt silently fails to actually switch drives.)

**2. Install FastAPI and the two things needed to actually run it.** Python itself is already set up from the earlier topics, but FastAPI is a new library, not installed on this machine yet:
```
pip install fastapi uvicorn
```
`uvicorn` is the "stove" explained in section 2 — the thing that actually runs a FastAPI app as a real, reachable server. This install only needs to happen once.

**3. Create a file with the demo app code**, e.g. `demo.py`, in that same folder — copy in the code from section 2 of this doc, then make whatever change the practice question asks for (a new endpoint, a validation rule, etc.).

**4. Two different ways to actually run it and see real output — pick whichever fits the question:**

**Option A — the simplest: add a `TestClient` block and just run the file.** This is exactly how every real output in this doc was captured. At the bottom of `demo.py`, add:
```python
if __name__ == "__main__":
    from fastapi.testclient import TestClient
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/accounts", json={"holder": "Test", "balance": 100.0})
    print("status:", response.status_code)
    print("body:", response.json())
```
Then just run:
```
python demo.py
```
No server, no network, no separate terminal needed — it prints the real result immediately. Best for quickly checking one or two calls (practice questions 2, 3, and 4 fit this well).

**Option B — a real running server**, if the question involves something like headers, or it's just easier to poke at it like a real API. In the terminal:
```
uvicorn demo:app --reload
```
(`demo` is the filename without `.py`; `app` is the FastAPI object's variable name inside it — use your own file/variable names if different.) This starts a real server and keeps running — leave that terminal open. Then, in a second terminal (or a browser), send real requests the same way shown earlier in this doc:
```
curl -i -X POST http://127.0.0.1:8000/accounts -H "Content-Type: application/json" -d "{\"holder\": \"Test\", \"balance\": 100.0}"
```
(Windows Command Prompt needs the escaped `\"` quotes like that, unlike the Linux `curl` examples earlier in this doc.) Or just open `http://127.0.0.1:8000/docs` in a browser for the clickable "Try it out" version — no `curl` needed at all. Press `Ctrl+C` in the server's terminal to stop it when done.

Use Option A for quick single checks, Option B when the question specifically involves things like headers, or just to see it behave like a real API end to end.

---

*When you've worked through these, share your code and the real output you captured — that's more useful than me just confirming you understood the diagrams. Once this one's checked off, say "next" and I'll build the next doc.*

## How the output in this doc was actually captured

Here's exactly what was done, in order, with the real commands, so this isn't just a claim to take on faith:

1. **Checked what was already available.**

   ```
   python3 -c "import fastapi, pydantic; print(fastapi.__version__, pydantic.VERSION)"
   ```

   This confirms FastAPI and Pydantic are installed on the cloud server (a separate computer in the cloud that I run on — not your laptop) before writing anything that depends on them. Output was `0.143.0 2.13.3`.

2. **Wrote the demo app itself.**
   A file was created with the actual FastAPI code — the `app = FastAPI(...)`, the `accounts` dict, the two Pydantic models, and all 7 routes (the exact code shown in section 2 above).

3. **Added a block at the bottom of that same file that drives it.**
   Inside `if __name__ == "__main__":` (meaning: this block only runs when you execute the file directly, not when something else imports it), the following was written:
   - `from fastapi.testclient import TestClient` — a tool FastAPI ships specifically for calling your own routes in code, without needing to actually start a real web server on a real port.
   - `client = TestClient(app, raise_server_exceptions=False)` — creates that caller, pointed at the `app` object. The `raise_server_exceptions=False` part matters for the `/boom` route specifically — without it, this tool would crash with the real Python error instead of giving back a proper 500 response the way a real server would.
   - A small helper function, `show(label, resp)`, that just prints a label, the real `resp.status_code`, and the real response body.
   - One call to `show(...)` per scenario demonstrated in this doc — `client.get("/accounts")`, `client.post("/accounts", json={...})`, etc. — 16 calls total, covering every status code the doc discusses.

4. **Actually ran the file, on the cloud server.**

   ```
   python3 "01 fastapi http fundamentals.py"
   ```

   This started the FastAPI app in-process and fired all 16 of those calls at it for real, printing each one's genuine status code and body to the terminal.

5. **Copied that real printed output straight into this doc.**
   Whatever the terminal printed — `status: 201`, `status: 422` with the exact Pydantic error shape, `status: 500` with `Internal Server Error`, all of it — was pasted verbatim into the matching sections above. Nothing in this doc was typed from memory; it's literally what step 4 printed.
