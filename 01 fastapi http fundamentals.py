from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

# creating fast-api object
app = FastAPI(title="Demo Accounts API")

accounts: dict[int, dict] = {
    1: {"id": 1, "holder": "Ravi Kumar", "balance": 5000.00},
    2: {"id": 2, "holder": "Priya Shah", "balance": 3000.00},
}
next_id = 3

class AccountIn(BaseModel):
    holder: str
    balance: float

# the field validator added for this model is used in Q2
class AccountUpdate(BaseModel):
    balance: float = Field(ge=0)

    @field_validator('balance')
    @classmethod
    def not_neg_balanace(cls, value:int):
        if value<0:
            raise ValueError('balance cannot be negetive')

# this model is used in Q4
class Bonus(BaseModel):
    divisor:float

    @field_validator('divisor')
    @classmethod
    def not_neg_increment(cls, value:int):
        if value<0:
            raise ValueError('bonus cannot be negetive')

#1. Predict, then verify.
@app.patch("/accounts/{account_id}/holder", status_code=201)
def update_holder_name(account_id: int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail='account not found')
    accounts[account_id]['holder'] = 'Anirruddha'
    return accounts[account_id]
'''
yes, it will be idempotent; just updating the same name twice. there is no global variable that is gets updated

'''
#2. Add a validation rule and trigger the real error.
@app.put('/accounts/{account_id}')
def update_balance(account_id:int, update:AccountUpdate):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail='account not found')
    accounts[account_id]['balance'] = update.balance
    return accounts[account_id]

#3. Confirm 404 is consistent.
@app.get('/accounts/{account_id}')
def get_account(account_id:int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail='account not found')
    return accounts[account_id]

@app.delete('/accounts/{account_id}', status_code=204)
def delete_account(account_id:int):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail='account not found')
    del accounts[account_id]
    return None

#4. Cause a genuine 500 on purpose, on a different endpoint than /boom.
@app.post('/accounts/{account_id}/apply-bonus', status_code=201)
def divide_balance(account_id:int, payload:Bonus, staus_code=201):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail='account not found')
    accounts[account_id]['balance'] = accounts[account_id]['balance']/payload.divisor
    return accounts[account_id]

#5. Explain the 401 vs 403 decision tree in your own words, in writing.
'''
secure_list() checks two separate questions, in this exact order

first check: is there an x-api-key header at all
    missing entirely -> 401, because the server does not even know who is asking yet

second check: only reached if a key was actually sent, is it the correct key
    wrong value -> 403, because the server knows who sent it, it is just not allowed in

401 means "you have not identified yourself"
403 means "you identified yourself, and that identity is not allowed"

why the order matters, concretely
    if the wrong-key check ran first, it would compare whatever was sent against
    'secret-admin-key' before ever checking if anything was sent at all
    a request with no header at all would still reach that comparison, none against
    the real key, fail it, and come back as 403 instead of 401
    that collapses two different situations into one response, "no key" and "wrong key"
    would look identical from outside, both 403

why that is a real security mistake, not just a labeling nitpick
    401 and 403 are supposed to tell the caller different things
    401 says "try again with credentials"
    403 says "you already tried, this identity is not enough, do not just retry the same way"
    merging them into always-403 hides which situation actually happened, which makes it
    harder for a legitimate client to debug why it is failing, and gives an attacker no
    extra information either way, but it quietly breaks the whole point of having two
    different codes in the first place

checking "is there a key" before "is it the right key" keeps the two failure reasons
distinct, and matches how the rest of this doc's 401 vs 403 section explained it:
401 is about missing identity, 403 is about identity that is not permitted
'''

'''
to run the code and try the execution:
   PS D:\interview prep\fast_api> uvicorn "01 fastapi http fundamentals:app" --reload
    INFO:     Will watch for changes in these directories: ['D:\\interview prep\\fast_api']
    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [27600] using StatReload
    INFO:     Started server process [27180]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.

    open http://127.0.0.1:8000/docs -> SwaggerUI (http://127.0.0.1:8000/docs#/)
'''
