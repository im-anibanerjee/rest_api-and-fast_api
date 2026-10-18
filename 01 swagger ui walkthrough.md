# 01 — Swagger UI Walkthrough (FastAPI)

This is a companion doc to "01 fastapi http fundamentals.md" — it does not teach any new HTTP concepts, it teaches you how to *read and drive the screen* you already have open at `/docs`. Every screenshot in section 3 is real, freshly captured against the exact demo app from doc 01's section 2, run for real and clicked through for real. Every screenshot in section 4 is one you captured yourself against your own practice file, over the course of this session.

Goal of this doc: stop treating the Swagger page as "a thing that happened to open" and start treating it as a tool — know what every piece of it means, and know how to make a real HTTP call through it without writing a single line of `curl` or Python.

## 1. What Swagger UI actually is

Simple version: it's a web page that FastAPI builds for you, automatically, from your own code — a clickable, fillable-in form for every route you wrote, so you (or anyone else on the team) can test the API directly from a browser instead of writing a separate script every time.

Real-life example: imagine if, the moment you wrote a restaurant menu, a vending machine that could actually place any order on that menu appeared next to it — press the button for "Butter Chicken, spicy," and it hands you one, for real, right there. You didn't build the vending machine. Writing the menu was enough.

Real-world use case: when a teammate asks "does `/accounts/{id}` return 404 or 400 for a missing account?", you don't need to read their code or write a test script — you open `/docs`, click the endpoint, hit Execute, and watch the real answer come back. This is also how you'll sanity-check your own endpoints before you believe they work, and it's often the first thing an interviewer will ask you to pull up if they want to see your API live.

Technical deep dive: FastAPI inspects every route you registered (`@app.get`, `@app.post`, ...), every Pydantic model you used for a request body, and every type hint on your path/query/header parameters, and from all of that generates a single JSON document describing your whole API — this lives at `/openapi.json` and follows a standard called the **OpenAPI Specification** (hence "OAS" badge you'll see on the page). Swagger UI is a separate piece of software (not written by you, not written by FastAPI's authors either — it's a well-known open-source project) that FastAPI serves at `/docs` by default; its only job is to read that `/openapi.json` document and render it as this interactive page. That's why the page updates itself automatically whenever you add or change a route and reload — it isn't hand-written HTML, it's generated fresh from your actual code, every time.

Connecting back: so when you see `/docs` show a `PATCH /accounts/{account_id}/holder` block, that block exists *only* because you wrote `@app.patch("/accounts/{account_id}/holder")` in your `.py` file — nothing about this page is separately maintained. Change your code, the page changes with it.

## 2. Anatomy of the page, piece by piece

This section explains every element you'll see, in the order they usually appear on screen. Read this once, then use it as a reference while you work through sections 3 and 4.

### The header

At the very top: your API's title (`app = FastAPI(title="Demo Accounts API")` is literally where that text comes from), a version badge (from `FastAPI(version=...)`, defaulting to `0.1.0` if you never set one), and an `OAS 3.1` badge naming which version of the OpenAPI spec this was generated against. Right under that is a link straight to `/openapi.json` — the raw machine-readable document this whole page was built from. You will basically never need to open that link yourself; it's there for tooling, not for you.

### The endpoint blocks — color means method

Below the header, every route you wrote shows up as one collapsed bar, grouped under a tag heading (`default` if you never explicitly tagged your routes — tags are a doc 10+ topic, ignore for now). Each bar is colored by HTTP method, and that color-coding is consistent across every FastAPI project you will ever open:

- **GET** — blue
- **POST** — green
- **PUT** — orange/amber
- **PATCH** — teal/turquoise
- **DELETE** — red

This means you can scan the whole page by color alone before reading a single word: "red bars are the dangerous ones, green bars create things." Next to the color comes the path (`/accounts/{account_id}`) and, in lighter text, the one-line summary FastAPI auto-generates from your function name (`update_holder_name` becomes "Update Holder Name").

### Expanding a block

Click anywhere on a collapsed bar and it opens into the detail view for that one endpoint. This is where everything else in this section lives. Click the same bar again (or the chevron on the right) to collapse it back — worth doing once you're done with one endpoint, since an open page with every endpoint expanded gets hard to scroll.

### The Parameters tab

Inside an expanded block, if the route takes any path parameters, query parameters, or headers, you'll see a **Parameters** tab with a table: **Name**, **Description** (blank unless you wrote a docstring/description for it), and, under the name, its type (`integer`, `string`, ...) and where it comes from — `(path)` for something baked into the URL itself like `{account_id}`, `(query)` for an optional `?key=value` style parameter, `(header)` for something like `x-api-key`. A red `*` and the word `required` next to a name means the call will fail without it; no `*` means it's optional and the route has a default for it.

### Try it out / Execute

Every block starts **read-only** — you can look at everything, but the input boxes are greyed out and there's no way to actually send a request yet. The **"Try it out"** button (top right of the expanded block) is what switches it into **editable mode**: the same input boxes become real text fields you can type into, and the button itself changes into **Cancel** (click that to go back to read-only without sending anything) plus a new blue **Execute** button appears below the inputs.

Fill in whatever the Parameters table asks for, then press **Execute**. This is the moment a real HTTP request leaves your browser and hits your actual running FastAPI process — not a simulation, not a preview. Whatever your Python function does, it does it for real: if it writes to the in-memory `accounts` dict, that dict is genuinely modified, and a subsequent `GET` will show the change.

### Request body — Example Value vs Schema

For `POST`/`PUT`/`PATCH` routes that take a body (anything typed with a Pydantic model, like `account: AccountIn`), you'll see a **Request body** section with a dropdown (almost always `application/json` — this is the **media type**, i.e., "what format is this body written in," and controls the request's `Content-Type` header) and, below it, two small tab links: **Example Value** and **Schema**.

- **Example Value** shows a ready-made, fake-but-correctly-shaped JSON body — this is what's in the editable textarea by default once you click Try it out, and it's exactly what you'd overwrite with your own real data.
- **Schema** shows the actual shape rules instead of a sample — every field's name, its type, whether it's required, and any constraints you declared (for example, `balance* number ≥ 0` is what `Field(ge=0)` on a Pydantic model renders as here — this is a direct, visual reflection of your model code).

### After you hit Execute — the Responses section

Once a request has actually run, a **Responses** section appears (or updates) with, in order:

- **Curl** — the exact same request, rewritten as a `curl` command you could paste into a real terminal. This is extremely useful once you start debugging outside the browser (e.g. from a teammate's machine, or in a script) — it's a correct, copy-pasteable translation of "what the UI just did."
- **Request URL** — the literal full URL that was called, with path and query parameters already substituted in.
- **Server response** — a small **Code / Details** table showing the real status code that came back (e.g. `404`), followed by the real **Response body** (the actual JSON your function returned, or FastAPI's own error body) and the real **Response headers** (`content-type`, `content-length`, `date`, `server`, and anything else FastAPI/uvicorn sent back). Everything in this block is genuine, captured, real output of this one specific request — not documentation, not an example.

### The static Responses table

Below the live "Server response" sits a second, unrelated **Responses** table — don't confuse the two. This one is **documentation**, not a result: it lists every status **Code** your function is declared to be able to return (e.g. `200`/`404`, or `201`/`422`), with a short **Description** and a **Links** column (always "No links" unless you've wired up OpenAPI response linking, which this series doesn't use). This table doesn't change when you click Execute — it's generated once from your code's type hints and `status_code=` arguments and stays the same no matter what you actually send. You can click into any listed code here to see its own Example Value / Schema, even without ever calling it for real.

### The Schemas section, at the very bottom of the page

Scroll (or click) all the way down and you'll find a **Schemas** section listing every Pydantic model your API uses, by name (`AccountIn`, `AccountUpdate`, `HTTPValidationError`, `ValidationError`, ...) — including two you never wrote yourself: `HTTPValidationError` and `ValidationError` are built into FastAPI/Pydantic and appear automatically the moment any route can return a `422`, which is any route with a typed body or parameter. Each entry shows every field, its type, and whether it's required (`*`) — this is the same information the per-endpoint Schema tab shows you, just all gathered in one place for reference.

## 3. Walkthrough — the original demo app from doc 01

Everything in this section was run against the unmodified demo app from doc 01, section 2 (same `app.py`, same routes, same in-memory accounts). Nothing here is special-cased or simplified for this doc — it's the literal page you'd see if you ran that exact code and opened `/docs`.

### Overview

![Swagger UI overview](01 swagger ui walkthrough_images/demo-app/01-overview.png)

Title "Demo Accounts API," version `0.1.0`, `OAS 3.1` badge, the `/openapi.json` link, then every route from doc 01's demo app collapsed into its colored bar: blue `GET /accounts`, blue `GET /accounts/{account_id}`, green `POST /accounts`, orange `PUT /accounts/{account_id}`, red `DELETE /accounts/{account_id}`, blue `GET /secure-accounts`, blue `GET /boom`.

### Schemas, expanded

![Schemas section](01 swagger ui walkthrough_images/demo-app/02-schemas.png)

`AccountIn` (`holder: string`, `balance: number`, both required) and `AccountUpdate` (`balance: number`, required) — the two request-body models this app defines. This is a direct rendering of:

```python
class AccountIn(BaseModel):
    holder: str
    balance: float

class AccountUpdate(BaseModel):
    balance: float
```

### GET /accounts — expanding it

![GET /accounts expanded](01 swagger ui walkthrough_images/demo-app/03-get-accounts-expanded.png)

Clicked the blue bar. Parameters tab shows one optional query parameter, `min_balance` (no red `*`, because `Query(default=None)` makes it optional) — no path parameters, because this route's path is just `/accounts` with nothing to fill in.

### Clicking "Try it out"

![Try it out clicked](01 swagger ui walkthrough_images/demo-app/04-get-accounts-tryitout.png)

The `min_balance` box is now a real, editable text input, and **Execute** has appeared.

### Filling it in, before executing

![min_balance filled with 4000](01 swagger ui walkthrough_images/demo-app/05-get-accounts-filled.png)

Typed `4000` into the box — nothing has been sent yet, this is still just local typing in the browser.

### After Execute — real response

![GET /accounts response](01 swagger ui walkthrough_images/demo-app/06-get-accounts-response.png)

Pressed Execute. Curl shows `curl -X 'GET' 'http://127.0.0.1:8030/accounts?min_balance=4000' -H 'accept: application/json'` — note the query string got appended automatically from what was typed. Server response: `200`, body is a JSON array containing only the one seed account whose balance is `>= 4000` (`"Ravi Kumar"`, balance `5000.0`) — `"Priya Shah"` at `3000.0` was correctly filtered out. This is real proof the `min_balance` filtering logic in `list_accounts()` works.

### POST /accounts — filling in a request body

![POST /accounts body filled](01 swagger ui walkthrough_images/demo-app/07-post-accounts-filled.png)

Expanded `POST /accounts`, clicked Try it out, then clicked directly into the Example Value textarea and replaced it with a real body: `{"holder": "Dev Patel", "balance": 1200}`.

### POST /accounts — real response

![POST /accounts response](01 swagger ui walkthrough_images/demo-app/08-post-accounts-response.png)

Execute pressed. Server response: `201`, body `{"id": 3, "holder": "Dev Patel", "balance": 1200}` — a brand-new account, genuinely created and assigned the next available id (`3`, continuing from the two seed accounts), exactly the way `create_account()` is written to behave.

### POST /accounts — triggering a real 422

![POST /accounts 422](01 swagger ui walkthrough_images/demo-app/09-post-accounts-422.png)

Same endpoint, this time the body was edited down to `{"holder": "No Balance Field"}` — missing the required `balance` field entirely — and Execute pressed again. Server response: `422`, with a body shaped exactly like the `HTTPValidationError`/`ValidationError` schemas from section 2 — `"loc": ["body", "balance"]` pinpoints exactly which field was the problem, `"msg": "Field required"` says why. This 422 was never written by hand anywhere in `app.py` — FastAPI generates it automatically the instant Pydantic validation fails, before your function body even runs.

### GET /accounts/{account_id} — a real 404

![GET account 404](01 swagger ui walkthrough_images/demo-app/10-get-account-404.png)

`account_id` filled in with `999`, which doesn't exist. Server response: `404`, body `{"detail": "Account not found"}` — this is the literal string from `raise HTTPException(status_code=404, detail="Account not found")` in `get_account()`, confirming the 404 path is not just declared in the Responses table, it's the real thing that happens.

### GET /secure-accounts — expanded

![secure-accounts expanded](01 swagger ui walkthrough_images/demo-app/11-secure-expanded.png)

One parameter, `x-api-key`, type `string | null`, location `(header)` — not required, because the route reads it as `x_api_key: str | None = Header(default=None)` and does its own manual check rather than FastAPI rejecting the request outright for a missing header.

### GET /secure-accounts — Try it out, no key entered

![secure-accounts try it out](01 swagger ui walkthrough_images/demo-app/12-secure-tryitout.png)

Editable `x-api-key` box, left empty on purpose, about to Execute.

### GET /secure-accounts — 401, no key sent

![secure-accounts 401](01 swagger ui walkthrough_images/demo-app/13-secure-401.png)

Curl shows no `-H 'x-api-key: ...'` line at all — the header was genuinely never sent. Server response: `401`, `{"detail": "Missing X-API-Key header"}` — this is `secure_list()`'s first check (`if x_api_key is None`) firing for real.

### GET /secure-accounts — 403, wrong key sent

![secure-accounts 403](01 swagger ui walkthrough_images/demo-app/14-secure-403.png)

This time `x-api-key` was filled in with `wrong-key` before Execute. Curl now shows `-H 'x-api-key: wrong-key'`. Server response: `403`, `{"detail": "This key is not allowed to view secure accounts"}` — the second check in `secure_list()` (`if x_api_key != "secret-admin-key"`), proving the 401-vs-403 split from doc 01's section on this is real and not just a design on paper.

### GET /secure-accounts — 200, correct key sent

![secure-accounts 200](01 swagger ui walkthrough_images/demo-app/15-secure-200.png)

`x-api-key` filled with `secret-admin-key`. Server response: `200`, full JSON array of every account, including the `"Dev Patel"` one created earlier in this same walkthrough with `POST /accounts` — proof that these are not isolated calls, they're all hitting the same running in-memory `accounts` dict, in order, exactly as a real session of using this app would.

## 4. Walkthrough — your own code

These are screenshots you captured yourself, from your own `01 fastapi http fundamentals.py`, running against your own VS Code setup (same page, same Swagger UI, now reading the OpenAPI document generated from your practice file instead of the doc's demo app).

### Overview and the endpoint list

![your overview](01 swagger ui walkthrough_images/your-code/01-overview-and-endpoints.png)

Same "Demo Accounts API" title (you kept `FastAPI(title="Demo Accounts API")` from the doc), same OAS 3.1 badge — and the `PATCH /accounts/{account_id}/holder` bar is your own Q1 endpoint, not something from doc 01's demo app. This confirms the page really is being generated fresh from *your* file, not some cached copy of the doc's version.

### GET /accounts/{account_id} — expanded, read-only

![your GET /accounts/{id}](01 swagger ui walkthrough_images/your-code/02-get-account-expanded.png)

Same shape as section 3's `GET` walkthrough — one required path parameter, `account_id`, type `integer`. Still in read-only mode here (Try it out not yet clicked) — box is greyed out, no Execute button yet.

### PATCH /accounts/{account_id}/holder — a real executed call

![your PATCH holder response](01 swagger ui walkthrough_images/your-code/03-patch-holder-executed.png)

This is a completed run of your Q1 endpoint: `account_id` was `2`, Execute was pressed, and the real response came back — `201`, body `{"id": 2, "holder": "Anirruddha", "balance": 3000}`. That status code is correct because of `@app.patch(..., status_code=201)` in your file, and the holder name changing to `"Anirruddha"` no matter what account you target is exactly what you predicted and explained in your Q1 answer (the hardcoded `accounts[account_id]['holder'] = 'Anirruddha'` line) — this screenshot is live proof of that prediction.

### PUT /accounts/{account_id} — Example Value

![your PUT balance example](01 swagger ui walkthrough_images/your-code/04-put-balance-example-value.png)

Still in read-only mode, showing the default Example Value `{"balance": 0}` for your `AccountUpdate` model's one field. Worth clicking the "Schema" tab next to "Example Value" here (not shown in this screenshot, but it's the same tab described in section 2) — for your file specifically, it will show `balance* number ≥ 0`, which is the visual rendering of your `Field(ge=0)` constraint. That `≥ 0` badge is a useful self-check: it tells you, just by looking at the page, that FastAPI/Pydantic will reject a negative balance *before* your own `not_neg_balanace` validator ever gets a chance to run — more on why that matters below, in section 5.

### Schemas — your models

![your schemas](01 swagger ui walkthrough_images/your-code/05-schemas.png)

`AccountUpdate` (`balance* number ≥ 0`) and `Bonus` (`divisor* number`, no constraint badge — because, unlike `balance`, `divisor` was never given a `Field(...)` on the model, only the custom `@field_validator`), plus the usual auto-generated `HTTPValidationError`/`ValidationError` pair.

### POST /accounts/{account_id}/apply-bonus — a parameter worth noticing

![your apply-bonus params](01 swagger ui walkthrough_images/your-code/06-apply-bonus-dead-param.png)

Look closely at the Parameters table here: alongside the required `account_id` path parameter, there's a second one — `staus_code`, type `any`, location `(query)`, default value `201`. This is not a typo in this doc; it's a real, visible symptom of a typo in your own code. Your function signature is:

```python
def divide_balance(account_id:int, payload:Bonus, staus_code=201):
```

`staus_code` (missing the `t`) was clearly meant to be `status_code` — but because it's spelled this way and given a plain default (`=201`, with no type hint and no `Field`/`Query` wrapper), FastAPI can't recognize it as the thing that sets your response's actual status code. Instead, FastAPI falls back to its default rule for any untyped, non-body parameter: treat it as an **optional query parameter** anyone calling this endpoint could pass in the URL, like `?staus_code=999` — and the function never even reads the value, so it does nothing either way. It is genuinely harmless (nothing breaks because of it), but it's dead, misleading surface area on your API: someone reading this Swagger page would reasonably assume passing `staus_code` changes something, and it doesn't. The actual status code (`201`) is set correctly elsewhere, by the real `status_code=201` argument on `@app.post(...)` itself.

### DELETE /accounts/{account_id}

![your DELETE endpoint](01 swagger ui walkthrough_images/your-code/07-delete-endpoint.png)

Collapsed red bar, same shape as section 3 — nothing unusual here, just confirming your own `DELETE` route renders with the same red-for-DELETE color convention as every other FastAPI project.

## 5. How to try this yourself

To reproduce anything in section 3 against doc 01's own demo app: copy the app code from "01 fastapi http fundamentals.md" section 2 into a file, then from that folder run:

```
uvicorn app:app --reload
```

(swap `app:app` for whatever your actual filename is, same as the "module:variable" pattern you already used for your own practice file), then open `http://127.0.0.1:8000/docs` in a browser.

To redo section 4 against your own file, you already know the command — it's the same one you used to get these screenshots in the first place:

```
uvicorn "01 fastapi http fundamentals:app" --reload
```

then `http://127.0.0.1:8000/docs`.

A few concrete things worth actually doing yourself, now that you know what every piece of the page means:

- Open the Schema tab (not Example Value) on `AccountUpdate`'s request body and confirm you can see the `≥ 0` constraint rendered from your own `Field(ge=0)`.
- Run `PUT /accounts/{account_id}` with a valid, positive balance through Try it out, and actually look at the `balance` field in the real response body that comes back — don't just check the status code.
- Run `POST /accounts/{account_id}/apply-bonus` with a valid, non-zero `divisor` through Try it out, and look closely at the response.

That last one is worth doing before you submit your answers — capture whatever you actually see for it in your own solution file, the same way you've been capturing the rest.
