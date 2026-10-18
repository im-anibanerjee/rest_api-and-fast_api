# 02 — Pydantic Models & Validation, In Depth (FastAPI)

This is doc 2 of the FastAPI series, picking up right where doc 01 left off. Doc 01's section 2 already introduced `Field(...)` and a single `@field_validator` as a brief taste of validation — this doc goes the rest of the way: nested models, constraining a field to a fixed set of choices, cross-field rules that need to see more than one field at once, and the less obvious half of Pydantic's job — controlling what you send *back out*, not just what you accept in. Everything below was run for real against the extended demo app in section 2, using the same `TestClient` approach doc 01 used (see the last section of this doc for the exact method) — every status code and every response body shown here is genuine captured output.

Goal of this doc: stop treating a Pydantic model as "just a type-hinted class" and start seeing it as two separate jobs wearing one syntax — validating untrusted input on the way in, and shaping trusted output on the way out — well enough to read and write real request/response models in your actual office FastAPI codebase.

## 1. Type coercion vs strict validation — what Pydantic is actually doing

### Simple version
Pydantic isn't just checking "is this the right type, yes or no" — by default it will also *convert* a value into the right type when it reasonably can, before deciding whether to accept it.

### Real-life example
Think of a strict bouncer versus a reasonable one at a club door. A strict bouncer only accepts a physical ID card shaped exactly like a driver's license — a photo of your ID on your phone gets rejected outright, even though it's obviously you. A reasonable bouncer looks at the photo, recognizes it's genuinely the same information in a slightly different form, and lets you in. Pydantic, by default, is the reasonable bouncer: it accepts information in a slightly different *shape* than you declared, as long as converting it is unambiguous.

### Real-world use case
Your frontend sends JSON, and JSON itself only has a handful of types (string, number, boolean, null, object, array) — there's no such thing as a JSON "float" versus a JSON "int" versus a JSON "Decimal." A sloppy frontend, or a query string parameter (which is *always* text, by definition) might hand your API `"balance": "5000"` — a string — when your model says `balance: float`. Pydantic doesn't reject this; it converts `"5000"` into `5000.0` for you, because that conversion is safe and unambiguous. This is real, verified behavior of the demo app below:

```
POST /accounts with balance sent as the JSON string "5000"
status: 201
"balance": 5000.0
```

### Technical deep dive
This is called Pydantic's **lax mode**, and it's the default in FastAPI. It will coerce a numeric string to `int`/`float`, `"true"`/`"false"`/`1`/`0` to `bool`, and a handful of other unambiguous conversions — but it will *not* coerce `"hello"` into an `int`, because there's no reasonable conversion. If you want the strict bouncer instead — reject `"5000"` as a string outright, demand a real JSON number — Pydantic v2 supports this per-field with `Field(strict=True)`, or for a whole model via `model_config = ConfigDict(strict=True)`. Most real APIs don't bother with strict mode for ordinary numbers, because rejecting `"5000"` when you obviously know what the caller meant is usually more annoying than helpful — but it's worth knowing this is a deliberate design choice, not an accident, and that you can turn it off when a field's type genuinely must not be guessed at (an API key, say, where a client passing the number `12345` instead of the string `"12345"` might indicate they're doing something wrong upstream).

### Connecting back
So "Pydantic validates your types" is only half the story — it validates *and* normalizes, converting what it reasonably can before deciding pass or fail. Keep that in mind any time a response looks subtly different in type from what you sent in; it's not a bug, it's lax mode doing its job.

## 2. The extended demo app

This builds directly on doc 01's demo app — same `accounts` dict, same domain — with new models added to demonstrate everything this doc covers:

```python
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

app = FastAPI(title="Demo Accounts API v2")

accounts: dict[int, dict] = {
    1: {"id": 1, "holder": "Ravi Kumar", "balance": 5000.00},
    2: {"id": 2, "holder": "Priya Shah", "balance": 3000.00},
}
next_id = 3


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    investment = "investment"


class Address(BaseModel):
    city: str
    state: str
    zip_code: str = Field(pattern=r"^\d{6}$")


class AccountIn(BaseModel):
    holder: str = Field(min_length=2, max_length=50)
    balance: float = Field(ge=0)
    account_type: AccountType
    address: Address
    internal_notes: Optional[str] = None

    @field_validator("holder")
    @classmethod
    def holder_must_be_letters_and_spaces(cls, value: str) -> str:
        if not all(ch.isalpha() or ch.isspace() for ch in value):
            raise ValueError("holder name must only contain letters and spaces")
        return value.title()


class AccountOut(BaseModel):
    id: int
    holder: str
    balance: float
    account_type: AccountType
    address: Address
    # internal_notes is deliberately left out - it never leaves the server


class StrictAccountIn(AccountIn):
    model_config = ConfigDict(extra="forbid")


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(gt=0)

    @model_validator(mode="after")
    def accounts_must_differ(self):
        if self.from_account_id == self.to_account_id:
            raise ValueError("from_account_id and to_account_id must be different")
        return self


@app.post("/accounts", status_code=201, response_model=AccountOut)
def create_account(account: AccountIn):
    global next_id
    new_account = {
        "id": next_id,
        "holder": account.holder,
        "balance": account.balance,
        "account_type": account.account_type,
        "address": account.address,
    }
    accounts[next_id] = new_account
    next_id += 1
    return new_account


@app.post("/accounts/strict", status_code=201)
def create_account_strict(account: StrictAccountIn):
    return {"accepted": account.model_dump()}


@app.post("/transfers")
def create_transfer(transfer: TransferRequest):
    return {"status": "ok", "transfer": transfer.model_dump()}
```

### What every new piece is actually doing, and why you'd bother writing it

`class AccountType(str, Enum):` creates a new type that can only ever be one of three exact values — `AccountType.checking`, `AccountType.savings`, or `AccountType.investment` — each backed by its matching string. Inheriting from both `str` and `Enum` (rather than just `Enum`) is a deliberate FastAPI/Pydantic convention: it means an `AccountType` value behaves like a real string everywhere a string is expected (it serializes to JSON as plain `"savings"`, not some special enum wrapper), while still giving you the safety of "only these three values are legal" everywhere it's used as a type hint.

`class Address(BaseModel):` is a Pydantic model exactly like `AccountIn` — the fact that it's going to be used *inside* another model doesn't require any special syntax. `zip_code: str = Field(pattern=r"^\d{6}$")` adds a regular-expression constraint: the value must be exactly six digits, nothing more or less — `pattern` is just another keyword argument `Field(...)` accepts, alongside `ge`/`min_length`/`max_length` you already know from doc 01.

`account_type: AccountType` on `AccountIn` is what actually turns the `Enum` from section 1 into a validation rule — Pydantic will accept only the three string values the enum defines, and reject anything else with a clear message listing what *is* allowed (shown in section 4 below).

`address: Address` is the nesting itself — a field typed as another `BaseModel` instead of a plain `str`/`int`/`float`. Nothing special is required to make this work: Pydantic recursively validates the nested object using `Address`'s own rules, the exact same way it validates `holder` or `balance` using their own rules.

`internal_notes: Optional[str] = None` declares a field that can be a string, or can be entirely absent/`None` — `Optional[str]` is shorthand for "`str` or `None`," and the `= None` default means the caller doesn't have to send this field at all. This field exists specifically to demonstrate something in section 6: it's perfectly fine for your *input* model to accept data that your *output* should never show back to the caller.

`class AccountOut(BaseModel):` is a second, separate model — same shape as the data you'd actually return, but with `internal_notes` left out entirely. This is the model that controls what the API's response *looks like*, independent of what `AccountIn` was willing to accept as input.

`class StrictAccountIn(AccountIn):` reuses every field `AccountIn` already has (via plain Python inheritance — nothing Pydantic-specific here) and adds exactly one thing: `model_config = ConfigDict(extra="forbid")`. `model_config` is a special class attribute Pydantic looks for to configure a model's overall behavior (as opposed to a single field's behavior, which is what `Field(...)` is for) — `extra="forbid"` tells Pydantic to reject the whole request if it contains any field the model doesn't know about, instead of silently ignoring it (the default).

`class TransferRequest(BaseModel):` is an ordinary model with three plain fields, plus one thing you haven't seen yet: `@model_validator(mode="after")` on `accounts_must_differ`. Unlike `@field_validator`, which only ever sees *one* field's value at a time, a `mode="after"` model validator runs once the whole model has already been built and gives you `self` — meaning this function can see every field at once (`self.from_account_id`, `self.to_account_id`) and check a rule that spans more than one of them. `return self` at the end matters for the same reason doc 01 flagged for `field_validator`: whatever a validator returns becomes the real result — a model validator in `mode="after"` has to return the (possibly modified) instance itself, not just "pass."

> **Follow-up: explain this part in detail and in a simpler way** — "`@model_validator(mode="after")` on `accounts_must_differ`. Unlike `@field_validator`, which only ever sees one field's value at a time, a `mode="after"` model validator runs once the whole model has already been built and gives you `self` — meaning this function can see every field at once (`self.from_account_id`, `self.to_account_id`) and check a rule that spans more than one of them. `return self` at the end matters for the same reason doc 01 flagged for `field_validator`: whatever a validator returns becomes the real result — a model validator in `mode="after"` has to return the (possibly modified) instance itself, not just 'pass.'"
>
> **Simple version**
> A normal Pydantic model just checks each field on its own — does `balance` look like a number, does `holder` look like a string, and so on, one field at a time. `@model_validator(mode="after")` is different: it waits until *every* field has already been checked and the object has already been built, and only then runs your function, handing you the whole finished object (that's what `self` is) so your function can compare fields against each other. "Return self" at the end just means: give that object back when you're done, unchanged (or changed, if you modified something) — don't give back nothing.
>
> **Real-life example**
> Imagine a form that asks for a "start date" and an "end date." Each date field, checked on its own, is perfectly valid — "March 1st" is a real date, "March 5th" is a real date. But there's a separate rule that only makes sense once you have *both* answers in front of you: "end date must come after start date." You can't check that rule while you're only looking at one blank on the form — you need the whole filled-in form in your hands first. That's exactly the difference between `@field_validator` (checks one blank at a time) and `@model_validator(mode="after")` (checks the whole filled-in form at once).
>
> **Real-world use case**
> In the transfer example, `from_account_id` and `to_account_id` are each perfectly valid integers on their own — `1` is fine, `2` is fine. The rule "these two must not be equal" can only be checked once both values exist together, which is exactly what `accounts_must_differ(self)` does: by the time it runs, `self` already has `self.from_account_id` and `self.to_account_id` both set, so it can compare them directly.
>
> **Technical deep dive**
> Here's the order things actually happen in, step by step:
>
> 1. Pydantic validates `from_account_id`, `to_account_id`, and `amount` individually first — same as always.
> 2. Once all three pass, Pydantic builds the real `TransferRequest` object with those values already sitting on it as attributes.
> 3. *Then*, because this is `mode="after"`, Pydantic calls `accounts_must_differ`, passing in that already-built object as `self` — so `self.from_account_id` inside the function is just normal attribute access on a normal object, nothing special.
> 4. Whatever `accounts_must_differ` returns becomes the official final result of building this model. If you return `self`, the object you were just handed is returned as-is, so nothing changes and everything downstream works normally.
>
> Now here's the part that makes `return self` matter, not just as a style choice: a Python function with no explicit `return` statement at the end automatically returns `None`. So if you write the `if self.from_account_id == self.to_account_id: raise ValueError(...)` check but forget to add `return self` afterward, your function's real, actual return value is `None` — and Pydantic takes you at your word. This was run for real to show exactly what breaks:
>
> ```
> # the validator with "return self" deleted on purpose
> TransferRequestBroken.model_validate({"from_account_id": 1, "to_account_id": 2, "amount": 500})
>
> result: None
> type(result): <class 'NoneType'>
>
> result.model_dump()
> error: AttributeError("'NoneType' object has no attribute 'model_dump'")
> ```
>
> The whole `TransferRequest` object — every field, `from_account_id`, `to_account_id`, `amount`, all of it — gets silently thrown away and replaced with `None`, even though the input was completely valid and should have succeeded. And sending this same broken model through a real FastAPI route, the same way this doc's demo app does, is what actually crashes the request:
>
> ```
> POST /transfers {"from_account_id": 1, "to_account_id": 2, "amount": 500}
> status: 500
> Internal Server Error
> ```
>
> A perfectly valid, correctly-filled-out transfer request causes a server crash, purely because one word (`return self`) was left off the bottom of the function.
>
> **Connecting back**
> This is the exact same category of bug as interview question 7 below, and the exact same bug already hit for real on `@field_validator` in doc 01's Q2/Q4 (`return value` missing, field silently nulled). The pattern is identical both times: whatever a validator function returns becomes the real, final value Pydantic uses — not "pass/fail," an actual replacement value. `@field_validator` replaces one field's value with whatever it returns; `@model_validator(mode="after")` replaces the *entire object* with whatever it returns. Forgetting the return statement doesn't mean "the check didn't run" — it means "the check ran, and then quietly destroyed everything by returning `None` instead of the thing you actually wanted to keep."

`@app.post("/accounts", status_code=201, response_model=AccountOut)` introduces `response_model=AccountOut` — this is the piece that actually enforces the `AccountOut`/`AccountIn` split. Even though the route's own `return new_account` includes every key from the input, FastAPI runs that return value back through `AccountOut` before sending it to the client, and `AccountOut` has no `internal_notes` field to put it in — so it's silently dropped. More on exactly why that matters in section 6.

`@app.post("/accounts/strict", ...)` and `@app.post("/transfers")` are ordinary routes with no new mechanics of their own — they exist purely to give `StrictAccountIn` and `TransferRequest` something real to be called through.

## 3. Nested models — one model inside another

### Simple version
A Pydantic model can have a field whose type is *another* Pydantic model, and when it does, validation happens at every level at once — the outer model's rules, and the inner model's rules, all checked together, with errors telling you exactly which level and which field actually failed.

### Real-life example
Think of a shipping label that has a "recipient" section and, inside that, a full "address" sub-section (street, city, postal code). If the postal code is wrong, a good label-checking system doesn't just say "something on this label is wrong" — it tells you specifically "the postal code, inside the address, inside the recipient section" is the problem. That's exactly what a nested Pydantic error path gives you.

### Real-world use case
A `POST /orders` endpoint in a real e-commerce API almost always nests something — a `shipping_address`, a list of `line_items`, each with its own fields. Without nested models, you'd either flatten everything into one giant model (ugly, and loses the reusability of `Address` as its own concept), or validate the nested data by hand with a pile of `if` statements. Nested models let you declare the shape once (`Address`), reuse it anywhere it's needed (`AccountIn.address`, and later a `TransferRequest` could have one too), and get full recursive validation for free.

### Technical deep dive
Here's what a real nested validation failure looks like — a zip code that's only 4 digits, inside a nested `address`:

```
POST /accounts with address.zip_code = "4000" (only 4 digits)
status: 422
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "address", "zip_code"],
      "msg": "String should match pattern '^\\d{6}$'",
      "input": "4000",
      "ctx": {"pattern": "^\\d{6}$"}
    }
  ]
}
```

Look closely at `"loc": ["body", "address", "zip_code"]` — this is the exact same `loc` mechanism doc 01 showed you for a flat, top-level field, except now it has three entries instead of two. Pydantic is telling you, precisely: this came from the request body, inside the `address` field, specifically its `zip_code`. If `Address` were nested three levels deep instead of one, `loc` would just keep growing — `["body", "shipment", "recipient", "address", "zip_code"]` — and you'd still know exactly where to look, without having to manually trace through the error yourself.

### Connecting back
Nesting isn't a special feature you have to opt into with extra syntax — it's just "what happens when a field's type happens to be another `BaseModel`." The payoff is that validation, and the resulting error messages, stay exactly as precise as a flat model's, no matter how deep the real-world data structure actually is.

## 4. Literal and Enum — constraining a field to a fixed set of choices

### Simple version
Sometimes a field shouldn't accept *any* string — it should only accept one of a known, fixed list of options, and Pydantic can enforce that directly, rather than you writing an `if value not in [...]` check by hand.

### Real-life example
A dropdown menu on a form is the everyday version of this — you're not allowed to type "spicy" into a shipping-method dropdown that only offers "Standard," "Express," and "Overnight." The form physically won't let you submit anything else. `AccountType` on the demo app is that same dropdown, enforced on the server instead of in a UI.

### Real-world use case
Account type, order status, user role, payment method — these are everywhere in real APIs, and they're exactly the kind of field where accepting an arbitrary string is actually a bug waiting to happen (a typo like `"invesment"` silently creating a broken account type that nothing else in the system recognizes). Constraining the field at the model level means that typo is caught immediately, as a clean 422, instead of quietly corrupting data that some other part of the system trusted to already be valid.

### Technical deep dive
Sending an account type that isn't one of the three real options:

```
POST /accounts with account_type = "crypto"
status: 422
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "account_type"],
      "msg": "Input should be 'checking', 'savings' or 'investment'",
      "input": "crypto",
      "ctx": {"expected": "'checking', 'savings' or 'investment'"}
    }
  ]
}
```

Notice the error message *lists the actual allowed values* — Pydantic generates that directly from the `Enum` class itself, so if you ever add a fourth account type to `AccountType`, every error message referencing it updates automatically; nothing to keep in sync by hand. You'll also sometimes see `Literal["checking", "savings", "investment"]` used instead of a full `Enum` class — it produces nearly identical validation behavior, but it's lighter weight: no class to define, just the exact values written directly into the type hint. The tradeoff is that an `Enum` gives you a real, reusable, importable type (`AccountType.savings` autocompletes in your editor and can be used elsewhere in your code), while `Literal` is a one-off, used right where it's declared. Most real codebases reach for `Enum` when the same set of choices gets used in more than one place, and `Literal` for a quick, local, one-off constraint.

### Connecting back
This is the same idea as `Field(ge=0)` from doc 01 — a declarative constraint Pydantic enforces for you — just applied to "which exact values are legal" instead of "what range of numbers is legal."

## 5. field_validator vs model_validator — one field vs the whole picture

### Simple version
`@field_validator` looks at one field, in isolation, and can't see any of the model's other fields. `@model_validator` (in `mode="after"`) runs once every field has already been individually validated, and can see — and compare — all of them at once.

### Real-life example
Imagine a form with "Start Date" and "End Date" fields. A field-level check can confirm each date, on its own, is a real, validly-formatted date — but only a check that looks at *both fields together* can catch "End Date is before Start Date." That's the exact difference between the two validator types: one field at a time, versus the whole form at once.

### Real-world use case
`TransferRequest` needs exactly this: `from_account_id` and `to_account_id` are each perfectly valid integers on their own — the problem only exists in the *relationship* between them (they're the same account). A `@field_validator("from_account_id")` physically cannot see what `to_account_id` was set to; it only ever receives the one value it was attached to. This is precisely the kind of rule that has to be a `@model_validator`.

### Technical deep dive
A transfer where `from_account_id` and `to_account_id` are the same account:

```
POST /transfers with from_account_id = 1, to_account_id = 1
status: 422
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, from_account_id and to_account_id must be different",
      "input": {"from_account_id": 1, "to_account_id": 1, "amount": 500},
      "ctx": {"error": {}}
    }
  ]
}
```

Notice `"loc": ["body"]` — just the body, with no specific field name after it. That's not a bug or a missing detail; it's the honest answer. This error isn't about any *one* field being wrong, it's about the relationship between two of them, so there's no single field to point at — `loc` correctly stops at the level the problem actually exists at.

And the same request with two different accounts, which passes cleanly:

```
POST /transfers with from_account_id = 1, to_account_id = 2
status: 200
{"status": "ok", "transfer": {"from_account_id": 1, "to_account_id": 2, "amount": 500.0}}
```

The `return self` at the end of `accounts_must_differ` matters here in exactly the way doc 01 warned about for `field_validator`: a `mode="after"` model validator that forgot to `return self` would silently produce a broken model (or, in some cases, raise a confusing internal error) even on input that should have passed — the same "a validator's return value is not optional" trap, just at the whole-model level instead of the single-field level.

### Connecting back
Use `@field_validator` for a rule about one field in isolation (doc 01's `holder` name check, or `balance >= 0`). Reach for `@model_validator(mode="after")` the moment a rule needs to compare two or more fields against each other — there's no way to express that kind of rule correctly with field-level validators alone.

## 6. Controlling what goes OUT: response_model

### Simple version
Everything doc 01 and sections 1-5 of this doc covered is about validating what comes *in*. `response_model` is the other half of the job: controlling, deliberately, what gets sent back *out* — even if the data your function has access to contains more than that.

### Real-life example
Think of a hospital's patient intake form versus the sign on the waiting-room display board. The intake form collects a lot — name, insurance details, medical history. The waiting-room board shows only a patient's first name and a queue number. Nobody manually scrubs the display board every time; the system is simply built so the board *only ever reads from* a narrower view of the data, one that never had the sensitive fields in it to begin with. `AccountOut` is that narrower view.

### Real-world use case
`AccountIn` accepts `internal_notes` — maybe a fraud-review flag, an internal risk comment, something genuinely useful for your own backend logic, but something a customer calling your API should never see in the response to their own `POST /accounts` call. Without `response_model`, it's dangerously easy to write `return new_account` where `new_account` is just the dict you built internally — which might still contain that sensitive field, now accidentally exposed over the network the moment someone adds a new internal field to that dict without remembering to also update what gets returned.

### Technical deep dive
A real account creation, where `internal_notes` was genuinely sent in the request, but the demo app still has `response_model=AccountOut` on the route:

```
POST /accounts with internal_notes = "flagged for KYC re-check"
status: 201
{
  "id": 3,
  "holder": "Dev Patel",
  "balance": 1200.0,
  "account_type": "savings",
  "address": {"city": "Pune", "state": "MH", "zip_code": "411001"}
}
```

`internal_notes` isn't just empty or `null` in that response — it's not there at all, because `AccountOut` has no field by that name. FastAPI takes whatever your function returns, re-validates and re-shapes it through the `response_model` you declared, and only the fields `AccountOut` actually defines make it into the JSON sent over the wire — this happens whether or not the dict you returned happened to contain more. That's the key safety property: it doesn't rely on you remembering to filter the field out by hand every single time; it's structurally impossible for `internal_notes` to leak through this route, because the model it's filtered through simply doesn't have a slot for it.

### Connecting back
`AccountIn` and `AccountOut` being two separate models isn't duplication for its own sake — it's the direct expression of "what I'm willing to accept" being a genuinely different question from "what I'm willing to show." Any time those two things aren't identical in a real API (and they very often aren't — passwords, internal flags, soft-deleted-but-still-in-the-dict records), `response_model` is the mechanism that keeps the difference enforced by the framework instead of by memory.

## 7. extra="forbid" vs the default — what happens to fields you didn't expect

### Simple version
By default, if a caller sends a field your model doesn't know about, Pydantic just quietly ignores it. `extra="forbid"` turns that into a hard rejection instead.

### Real-life example
Imagine handing someone a form with three blank lines and they staple an extra page to the back with a fourth answer written on it. The default behavior is like a clerk who just doesn't look at the stapled page at all — it's there, but nothing happens with it, and nobody's told. `extra="forbid"` is a clerk who hands the whole form back and says "I don't have a field for this, please fix your submission."

### Real-world use case
Imagine a client meant to send `"balance": 500` but actually sent `"blance": 500` — a typo. With the default behavior, your model has no `blance` field, so that typo'd key is silently dropped, `balance` falls back to... well, if `balance` were required, you'd get a normal "field required" error, which is at least visible. But if `balance` had a default value, the typo would go completely unnoticed — the account gets created with the default, and nobody finds out until much later that the client's real intended value never made it in. `extra="forbid"` turns that exact scenario into an immediate, loud 422 at the moment it happens, instead of a silent data problem discovered days later.

### Technical deep dive
The exact same extra field, `"nickname": "Ro"`, sent to two different routes — one using the default `AccountIn`, one using `StrictAccountIn`:

```
POST /accounts/strict (extra="forbid") with nickname="Ro"
status: 422
{
  "detail": [
    {
      "type": "extra_forbidden",
      "loc": ["body", "nickname"],
      "msg": "Extra inputs are not permitted",
      "input": "Ro"
    }
  ]
}

POST /accounts (default behavior) with the same nickname="Ro"
status: 201
{
  "id": 5,
  "holder": "Rohit Verma",
  "balance": 800.0,
  "account_type": "checking",
  "address": {"city": "Jaipur", "state": "RJ", "zip_code": "302001"}
}
```

Same exact extra field, same exact request otherwise — one rejects it outright with a clear 422 pointing at the unexpected key, the other accepts the request and simply never mentions `nickname` again. Nothing in the second response tells you it was ever sent.

### Connecting back
This is a genuine design decision every real model has to make, not a default you should assume is always right: lenient-by-default (`extra` ignored) is friendlier to callers who send a slightly outdated or slightly-too-generous payload, while `extra="forbid"` catches typos and API misuse early at the cost of being stricter about exactly what shape a request must be. A lot of real production APIs reach for `extra="forbid"` specifically on write operations (`POST`/`PUT`/`PATCH`) for exactly the typo-safety reason above, while staying lenient on things like internal/admin-only fields they don't want every client to have to know don't exist.

## 8. A quick note on the modern `Annotated` + `Field` style

You will often see the same constraint written two different ways in real FastAPI code:

```python
# the style used throughout this doc and doc 01
balance: float = Field(ge=0)

# the newer, increasingly common alternative
from typing import Annotated
balance: Annotated[float, Field(ge=0)]
```

Both do exactly the same validation — `Annotated[float, Field(ge=0)]` is read as "this is a `float`, and here's some extra metadata (`Field(ge=0)`) attached to that type hint, rather than being its default value." The practical difference shows up with *default values*: using the `= Field(...)` style, a required field with no default looks like `balance: float = Field(ge=0)`, which can read a little oddly (it looks like it has a default, but doesn't). Using `Annotated`, you write `balance: Annotated[float, Field(ge=0)] = 0.0` for an *actual* default, keeping the constraint metadata and the default value visibly separate instead of both living inside the same `Field(...)` call. Either style is correct and you'll see both in real codebases — this doc keeps using the `= Field(...)` style throughout for consistency with doc 01, but recognizing `Annotated[...]` the moment you see it in someone else's code is worth having in your pocket.

## Interview questions

1. What's the practical difference between a `@field_validator` and a `@model_validator(mode="after")` — and what kind of rule can only be expressed with the second one?
2. Why does `loc` in a validation error sometimes have two entries (`["body", "balance"]`) and sometimes three or more (`["body", "address", "zip_code"]`)? What determines the depth?
3. What does Pydantic's "lax mode" actually do, and why does `"balance": "5000"` (a JSON string) get accepted by a field typed `balance: float`?
4. Why would a real API define two separate models — one for input, one for output — for what's conceptually "the same resource"? What's the actual risk of using just one model for both?
5. What's the difference in behavior between the default (`extra` ignored) and `model_config = ConfigDict(extra="forbid")` when a client sends a field the model doesn't define? Which would you pick for a public write endpoint, and why?
6. When would you reach for `Literal[...]` instead of a full `Enum` class, and what do you lose by choosing the lighter-weight option?
7. If a `@model_validator(mode="after")` function forgets its `return self`, what actually goes wrong, and why is this the same category of mistake as a `@field_validator` forgetting `return value`?
8. A nested model's field fails validation. Does FastAPI run the outer model's other fields' validation too, or does it stop at the first nested failure? What would you expect to see in `detail` if *both* a top-level field and a nested field were invalid in the same request?
9. What does `response_model` actually do to the value your route function returns, mechanically — does it just serialize it as-is, or something more?
10. Why is `Annotated[float, Field(ge=0)]` sometimes preferred over `float = Field(ge=0)`, specifically once a field also needs a default value?

## Practice questions

Attempt these yourself first — copy the extended demo app from section 2 into your own file, extend it, run it for real, and see what happens before checking anything. Then share your code and real output for a check.

1. **Add a second nested model and break it on purpose.** Add a `PhoneNumber` model (e.g. `country_code: str` with a pattern constraint, `number: str` with a different pattern constraint) as a new field on `AccountIn`. Send a request with an invalid `number`, capture the real 422, and confirm the `loc` path correctly shows `["body", "phone", "number"]` (or whatever you name the field) rather than just `["body", "phone"]`.

2. **Write a cross-field rule with `@model_validator`.** Add a rule to `AccountIn` (or a new model of your own) that says: if `account_type` is `"investment"`, then `balance` must be at least some minimum you choose (say, 10000). This needs to see two fields at once — write it as a `@model_validator(mode="after")`, not a `@field_validator`, and explain in a comment why a `@field_validator` on `balance` alone couldn't express this rule.

3. **Add a field that must never be returned, and prove it.** Add a new field to `AccountIn` that a real account API plausibly wouldn't want to echo back (your choice — something like `internal_risk_score: Optional[float] = None` works fine). Confirm, with real captured output, that it comes through fine on account creation internally but is genuinely absent from the response. Then explain in writing: what could go wrong if, instead of a separate `response_model`, the route just did `return new_account_dict` with the sensitive field manually deleted by hand before returning?

4. **Turn on `extra="forbid"` for one of your own existing routes from doc 01**, and deliberately send an extra, unexpected field to it. Capture the real 422. Then explain, in writing, one concrete scenario at your actual job where silently-ignored extra fields (the default) could cause a real bug that would be hard to notice.

5. **Add your own `Enum` for something other than account type** — a `TransactionCategory` (e.g. `groceries`, `rent`, `entertainment`) used on a new field somewhere. Send one valid value and one invalid value, capture both real responses, and explain why you reached for `Enum` here instead of `Literal`, or vice versa, for your specific case.

### How to run the practice code and test

Same two options doc 01 walked through — copy this doc's section 2 demo app into a file in your `D:\interview prep\fast_api` folder, make the change the question asks for, then either:

**Option A — `TestClient`, no server needed.** Add this to the bottom of your file and run it directly with `python demo.py`:
```python
if __name__ == "__main__":
    from fastapi.testclient import TestClient
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/accounts", json={
        "holder": "Test",
        "balance": 100.0,
        "account_type": "checking",
        "address": {"city": "Pune", "state": "MH", "zip_code": "411001"},
    })
    print("status:", response.status_code)
    print("body:", response.json())
```

**Option B — a real running server**, with `uvicorn demo:app --reload`, then either `curl` or the `/docs` Swagger UI (see doc 01's companion walkthrough doc if you want a refresher on reading and using that page).

## How the output in this doc was actually captured

Same method as doc 01: a file was written with the full extended demo app from section 2 above, a separate script imported it, built a `TestClient(app, raise_server_exceptions=False)`, and fired one real request per scenario shown in this doc — nine calls total, covering type coercion, a nested validation failure, an invalid enum value, the `response_model` field-dropping behavior, both sides of `extra="forbid"` vs the default, and both sides of the `model_validator` cross-field check. Every status code and response body shown above is that script's real printed output, pasted in verbatim — nothing in this doc was typed from memory or reasoned out without running it.

---

*When you've worked through these, share your code and the real output you captured. Once this one's checked off, say "next" and I'll build the next doc.*
