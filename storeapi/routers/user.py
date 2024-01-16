import logging

from fastapi import APIRouter, BackgroundTasks,HTTPException, status, Request
from storeapi.models.user import UserIn
from storeapi.security import (
    get_user,
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_subject_for_token_type,
    create_confirmation_token,
)
from storeapi import tasks
from storeapi.database import database, user_table

logger = logging.getLogger(__name__)
router = APIRouter()


# Background tasks can run any function in aa background.
# takes UserIn object
@router.post("/register", status_code=201)
async def register(user: UserIn, background_tasks: BackgroundTasks, request: Request):
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
    # first arg is a function to run, then arguments for this function.
    background_tasks.add_task(
        tasks.send_user_registration_email,
        user.email,
        confirmation_url=request.url_for(
            "confirm_email", token=create_confirmation_token(user.email)
        ),
    )
    return {
        "detail": "User Created. Please confirm your email.",
    }


# takes username and password
@router.post("/token")
async def login(user: UserIn):
    user = await authenticate_user(user.email, user.password)
    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirm/{token}")
async def confirm_email(token: str):
    email = get_subject_for_token_type(token, "confirmation")
    query = (
        user_table.update().where(user_table.c.email == email).values(confirmed=True)
    )

    logger.debug(query)

    await database.execute(query)
    return {"detail": "User confirmed"}
