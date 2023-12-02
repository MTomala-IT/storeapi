import logging

from fastapi import APIRouter, HTTPException, status
from storeapi.models.user import UserIn
from storeapi.security import (
    get_user,
    get_password_hash,
    authenticate_user,
    create_access_token
)

from storeapi.database import database, user_table

logger = logging.getLogger(__name__)
router = APIRouter()


# takes UserIn object
@router.post("/register", status_code=201)
async def register(user: UserIn):
    if await get_user(user.email):
        raise HTTPException(
            # fastapi status module has all status code needed to raise errors
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists"
        )

# NEVER STORE plain passwords in a DB !
    hashed_password = get_password_hash(user.password)
    query = user_table.insert().values(email=user.email, password=hashed_password)

    logger.debug(query)

    await database.execute(query)
    return {"detail": "User Created."}


# takes username and password
@router.post("/token")
async def login(user: UserIn):
    user = await authenticate_user(user.email, user.password)
    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}
