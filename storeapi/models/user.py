from pydantic import BaseModel


# when yser created will not give an id, when is retrieved then will give ID
class User(BaseModel):
    id: int | None = None
    email: str


# don't want to return the password when returning the user !
class UserIn(User):
    password: str
