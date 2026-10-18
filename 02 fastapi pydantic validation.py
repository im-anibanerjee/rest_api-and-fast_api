from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

app =FastAPI(title='Demo Accounts API V2')

accounts: dict[int, dict] = {
    1: {"id": 1, "holder": "Ravi Kumar", "balance": 5000.00},
    2: {"id": 2, "holder": "Priya Shah", "balance": 3000.00},
}
next_id = 3

class AccountType(str, Enum):
    checking = 'checking'
    savings = 'savings'
    investment = 'investment'

class Address(BaseModel):
    city: str
    state: str
    zip_code: str = Field(pattern=r'^\d{6}$')

class PhoneNumber(BaseModel):
    number: str = Field(pattern=r'^\d{10}$')

class AccountIn(BaseModel):
    holder: str
    balance: float = Field(ge=0) # field_validator not required; see doc
    account_type: AccountType
    address: Address
    phone_number: PhoneNumber
    internal_notes: Optional[str] = None
    internal_risk_score: Optional[float] = None # added for Q3

    # this model validator is used in Q2
    @model_validator(mode='after')
    def investmentBalanceCheck(self):
        if self.account_type=='investment':
            if self.balance<10000:
                raise ValueError('balance for investment account must be min 10000')
        return self

class AccountOut(BaseModel):
    id: int
    holder: str
    balance: float
    account_type: AccountType
    address: Address

# this is used in Q4
class StrictAccountIn(AccountIn):
    model_config = ConfigDict(extra="forbid")

#1. Add a second nested model and break it on purpose
@app.post('/accounts/')
def createAccount(account: AccountIn):
    global next_id
    new_account = {
        "id": next_id,
        "holder": account.holder,
        "balance": account.balance,
        "account_type": account.account_type,
        "address": account.address,
    }
    accounts[next_id] = new_account
    next_id = next_id+1
    return new_account
'''
try_it_out 1:
    request body:
    {
        "holder": "string",
        "balance": 0,
        "account_type": "checking",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "837589"
        },
        "phone_number": {
            "number": "529"
        },
        "internal_notes": "string"
    }   --> execute
    
    curl: 
        curl -X 'POST' \
        'http://127.0.0.1:8000/accounts/' \
        -H 'accept: */*' \
        -H 'Content-Type: application/json' \
        -d '{
                "holder": "string",
                "balance": 0,
                "account_type": "checking",
                "address": {
                    "city": "string",
                    "state": "string",
                    "zip_code": "837589"
                },
                "phone_number": {
                    "number": "529"
                },
                "internal_notes": "string"
            }'
    
    request url: http://127.0.0.1:8000/accounts/
    response body (422; Error: Unprocessable Entity): 
    {
        "detail": [
            {
                "type": "string_pattern_mismatch",
                "loc": [
                    "body",
                    "phone_number",
                    "number"
                ],
                "msg": "String should match pattern '^\\d{10}$'",
                "input": "529",
                "ctx": {
                    "pattern": "^\\d{10}$"
                }
            }
        ]
    }

try_it_out 2:
    request body:
    {
        "holder": "string",
        "balance": 0,
        "account_type": "abcdef",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "837589"
        },
        "phone_number": {
            "number": "6050157644"
        },
        "internal_notes": "string"
    }   --> execute
    
    curl: 
        curl -X 'POST' \
        'http://127.0.0.1:8000/accounts/' \
        -H 'accept: */*' \
        -H 'Content-Type: application/json' \
        -d '{
                "holder": "string",
                "balance": 0,
                "account_type": "checking",
                "address": {
                    "city": "string",
                    "state": "string",
                    "zip_code": "837589"
                },
                "phone_number": {
                    "number": "6050157644"
                },
                "internal_notes": "string"
            }'
    
    request url: http://127.0.0.1:8000/accounts/
    response body (422; Error: Unprocessable Entity): 
    {
        "detail": [
            {
                "type": "enum",
                "loc": [
                    "body",
                    "account_type"
                ],
                "msg":  "Input should be 'checking', 'savings' or 'investment'",
                "input": "abcdef",
                "ctx": {
                    "expected": "'checking', 'savings' or 'investment'"
                }
            }
        ]
    }
'''

#2. Write a cross-field rule with @model_validator.
@app.post('/accounts/accounts/', response_model=AccountOut)
def createAccount_2(account: AccountIn):
    global next_id
    new_account = {
        "id": next_id,
        "holder": account.holder,
        "balance": account.balance,
        "account_type": account.account_type,
        "address": account.address,
    }
    accounts[next_id] = new_account
    next_id = next_id+1
    return new_account
'''
when you open the SwaggerUI, you will see 2 post requests:
    * post  /accounts/   Createaccount
    * post  /accounts/accounts/   Createaccount2

try_it_out 1:
    request body:
    {
        "holder": "string",
        "balance": 0,
        "account_type": "investment",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "018022"
        },
        "phone_number": {
            "number": "4757514493"
        },
        "internal_notes": "string"
    }   --> execute
    
    curl: 
        curl -X 'POST' \
        'http://127.0.0.1:8000/accounts/' \
        -H 'accept: */*' \
        -H 'Content-Type: application/json' \
        -d '{
                "holder": "string",
                "balance": 0,
                "account_type": "investment",
                "address": {
                    "city": "string",
                    "state": "string",
                    "zip_code": "018022"
                },
                "phone_number": {
                    "number": "4757514493"
                },
                "internal_notes": "string"
            }'
    
    request url: http://127.0.0.1:8000/accounts/accounts/
    response body (422; Error: Unprocessable Entity): 
    {
        "detail": [
            {
                "type": "string_pattern_mismatch",
                "loc": [
                    "body"
                ],
                "msg": "Value error, balance for investment account must be min 10000",
                "input": {
                    "holder": "string",
                    "balance": 0,
                    "account_type": "investment",
                    "address": {
                        "city": "string",
                        "state": "string",
                        "zip_code": "018022"
                    },
                    "phone_number": {
                        "number": "4757514493"
                    },
                    "internal_notes": "string"
                },
                "ctx": {
                    "pattern": "^\\d{10}$"
                }
            }
        ]
    }

try_it_out 2:
    request body:
    {
        "holder": "string",
        "balance": 10000,
        "account_type": "investment",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "018022"
        },
        "phone_number": {
            "number": "4757514493"
        },
        "internal_notes": "string"
    }   --> execute
    
    curl: 
        curl -X 'POST' \
        'http://127.0.0.1:8000/accounts/' \
        -H 'accept: */*' \
        -H 'Content-Type: application/json' \
        -d '{
                "holder": "string",
                "balance": 10000,
                "account_type": "investment",
                "address": {
                    "city": "string",
                    "state": "string",
                    "zip_code": "018022"
                },
                "phone_number": {
                    "number": "4757514493"
                },
                "internal_notes": "string"
            }'
    
    request url: http://127.0.0.1:8000/accounts/accounts/
    response body (422; Error: Unprocessable Entity): 
    {
        "id": 3,
        "holder": "string",
        "balance": 10000,
        "account_type": "investment",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "637073"
        }
    }
'''

#3. Add a field that must never be returned, and prove it
@app.post('/accounts/accounts/accounts/', response_model=AccountOut)
def createAccount_3(account: AccountIn):
    global next_id
    new_account = {
        "id": next_id,
        "holder": account.holder,
        "balance": account.balance,
        "account_type": account.account_type,
        "address": account.address,
    }
    accounts[next_id] = new_account
    next_id = next_id+1
    return new_account
'''
when you open the SwaggerUI, you will see 2 post requests:
    * post  /accounts/   Createaccount
    * post  /accounts/accounts/   Createaccount2
    * post  /accounts/accounts/accounts/   Createaccount3
try_it_out:
    request body:
    {
        "holder": "string",
        "balance": 0,
        "account_type": "checking",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "814610"
        },
        "phone_number": {
            "number": "8848384638"
        },
        "internal_notes": "good customer",
        "internal_risk_score": 99
    }   --> execute

    curl:
        curl -X 'POST' \
        'http://127.0.0.1:8000/accounts/accounts/accounts/' \
        -H 'accept: */*' \
        -H 'Content-Type: application/json' \
        -d '{
                "holder": "string",
                "balance": 0,
                "account_type": "checking",
                "address": {
                    "city": "string",
                    "state": "string",
                    "zip_code": "814610"
                },
                "phone_number": {
                    "number": "8848384638"
                },
                "internal_notes": "good customer",
                "internal_risk_score": 99
            }'

    request url: http://127.0.0.1:8000/accounts/accounts/accounts/
    response body (200): 
    {
        "id": 3,
        "holder": "string",
        "balance": 0,
        "account_type": "checking",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "814610"
        }
    }

'''

#4. Turn on extra="forbid" for one of your own existing routes 
@app.post('/accounts/strict', status_code=201)
def createAccountStrict(account:StrictAccountIn):
    return {'accepted': account.model_dump()}
'''
when you open the SwaggerUI, you will see 2 post requests:
    * post  /accounts/   Createaccount
    * post  /accounts/accounts/   Createaccount2
    * post  /accounts/accounts/accounts/   Createaccount3
    * post  /accounts/strict/   Createaccountstrict

try_it_out:
    request body:
    {
        "holder": "string",
        "balance": 0,
        "account_type": "checking",
        "address": {
            "city": "string",
            "state": "string",
            "zip_code": "352472"
        },
        "phone_number": {
            "number": "3296776575"
        },
        "internal_notes": "string",
        "internal_risk_score": 0,
        "xyz":3
    }   --> execute

    curl:
        curl -X 'POST' \
        'http://127.0.0.1:8000/accounts/strict' \
        -H 'accept: */*' \
        -H 'Content-Type: application/json' \
        -d '{
                "holder": "string",
                "balance": 0,
                "account_type": "checking",
                "address": {
                    "city": "string",
                    "state": "string",
                    "zip_code": "352472"
                },
                "phone_number": {
                    "number": "3296776575"
                },
                "internal_notes": "string",
                "internal_risk_score": 0,
                "xyz":3
            }
    
    response body (422; Error: Unprocessable Entity):
    {
        "detail": [
            {
                "type": "extra_forbidden",
                "loc": [
                    "body",
                    "xyz"
                ],
                "msg": "Extra inputs are not permitted",
                "input": 3
            }
        ]
    }
'''
#5. Add your own Enum for something other than account type
'''
did not add a brand new enum field, reused the existing account_type enum and its try_it_out output from Q1 as the demonstration (checking/savings/investment valid, abcdef rejected)

part 2 - why enum was used here instead of literal:
    account_type is the exact same enum referenced in two separate places, AccountIn and AccountOut
    enum lets both models point at the one AccountType class instead of each writing out the list of allowed strings on its own
    
    if literal was used instead, the list checking/savings/investment would need to be typed out separately wherever this type is needed, 
    and if those separate lists ever drifted apart, that mismatch would be a real bug that is hard to notice

    enum also gives a real named, importable type, AccountType.investment autocompletes in the editor and can be reused anywhere else in the codebase that needs this same set of values
    a literal has no name, it only exists inline exactly where it was typed
    literal is the lighter, better choice only when the set of values is a true one off, used in exactly one place with no reuse anywhere else
    that is not the case for account_type here, so enum was the right call
'''

'''
to run the code and try the execution:
   PS D:\interview prep\fast_api> uvicorn "02 fastapi pydantic validation:app" --reload
    INFO:     Will watch for changes in these directories: ['D:\\interview prep\\fast_api']
    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [27600] using StatReload
    INFO:     Started server process [27180]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.

    open http://127.0.0.1:8000/docs -> SwaggerUI (http://127.0.0.1:8000/docs#/)
'''