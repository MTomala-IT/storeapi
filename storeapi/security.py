"""
Password hashing
The hash algorithms in Passlib were explicitly designed, so they are as hard to reverse as possible:
you can hash a password, you can check if a password matches an existing hash, and that’s it.

JWT tokens
"""

import datetime
import logging
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, ExpiredSignatureError, JWTError

from storeapi.database import  database, user_table

logger = logging.getLogger(__name__)

SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp9eyJzdWIiOiIxMjM0NTY3ODkwFtZSI6G4gRG9lYWRtaW4iOnRydWV9"
ALGORITHM = "HS256"
# endpoint where user cas send credentials to get the token back.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"])


def create_credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
)


# expire fo making the tests easier
def access_token_expire_minutes() -> int:
    return 30


def confirm_token_expire_minutes() -> int:
    return 1440


# to create access token, get from user unique info such as ID or email in this case
def create_access_token(email: str):
    logger.debug("Creating access token", extra={email: email})
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=access_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_confirmation_token(email: str):
    logger.debug("Creating confirmation token", extra={email: email})
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=confirm_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "confirmation"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Literal module - thr value should be one of specified.
def get_subject_for_token_type(
    token: str, type: Literal["access", "confirmation"]
) -> str:
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError as e:
        raise create_credentials_exception("Token has expired") from e
    except JWTError as e:
        raise create_credentials_exception("Invalid token") from e

    email = payload.get("sub")
    if email is None:
        raise create_credentials_exception("Token is missing 'sub' field")

    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_credentials_exception(f"Token has incorrect type, expected '{type}'.")

    return email


# password already hashed can not be un-hash, stored safely in DB. unique hash even is you pass the same password twice
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# passlib has a tool to verify hash in compare to plain text and returns boolean.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_user(email: str):
    logger.debug("Fetching user from database", extra={"email": email})
    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)
    if result:
        return result


async def authenticate_user(email: str, password: str):
    logger.debug("Authenticating user", extra={"email": email})
    user = await get_user(email)
    if not user:
        raise create_credentials_exception("Invalid email ot password")
    if not verify_password(password, user.password):
        raise create_credentials_exception("Invalid email ot password")
    if not user.confirmed:
        raise create_credentials_exception("User has not confirmed email")
    return user


# decode the token, if expired - error, get user from DB , id not exists - error
# mark that 401 error comes from expired token.
# tokens are checked auto without calling them manually , thanks to depends and Annotated
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    email = get_subject_for_token_type(token, "access")
    user = await get_user(email=email)
    if user is None:
        raise create_credentials_exception("Could not find user for this token")
    return user

