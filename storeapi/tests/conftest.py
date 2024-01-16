import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, Request, Response


# overwrites the .env file to set test environment.
os.environ["ENV_STATE"] = "test"
from storeapi.database import database, user_table  # noqa: E402
from storeapi.main import app  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)


# after disconnecting the DB it's going to roll back everything. thanks to our settings 'config.py'.
# this will happen before each test case, connect -> yield will run test case ->then disconnect.
@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    await database.connect()
    yield
    await database.disconnect()


@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    async with AsyncClient(app=app, base_url=client.base_url) as ac:
        yield ac


# pass saved as a plain text, later to deal with it !
# gives us registered user with ID for testing.
@pytest.fixture()
async def registered_user(async_client: AsyncClient) -> dict:
    user_details = {"email": "test@example.net", "password": "1234"}
    await async_client.post("/register", json=user_details)
    query = user_table.select().where(user_table.c.email == user_details["email"])
    user = await database.fetch_one(query)
    user_details["id"] = user.id
    return user_details


# take registered user and confirm it.
@pytest.fixture()
async def confirmed_user(registered_user: dict) -> dict:
    query = (
        user_table.update()
        .where(user_table.c.email == registered_user["email"])
        .values(confirmed=True)
    )
    await database.execute(query)
    return registered_user


@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, confirmed_user: dict) -> str:
    response = await async_client.post("/token", json=confirmed_user)
    return response.json()["access_token"]


# disable mailgun sending the emails when the tests run.
@pytest.fixture(autouse=True)
async def mock_httpx_client(mocker):
    mocked_client = mocker.patch("storeapi.tasks.httpx.AsyncClient")

    mocked_async_client = Mock()
    response = Response(status_code=200, content="", request=Request("POST", "//"))
    mocked_async_client.post = AsyncMock(return_value=response)
    # __aenter__ runs when you do Async with httpx.AsyncxClient()
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client
