from pydantic import BaseModel, ConfigDict


class UserPostIn(BaseModel):
    body: str


class UserPost(UserPostIn):
    # allows pydantic to deal with DB roll models as they are dicts
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class UserPostWithLikes(UserPost):
    likes: int

    class Config:
        orm_mode: True


class CommentIn(BaseModel):
    body: str
    post_id: int


class Comment(CommentIn):
    # allows pydantic to deal with DB roll models as they are dicts
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class UserPostWithComments(BaseModel):
    post: UserPostWithLikes
    comments: list[Comment]


# what 'post' like receives.
class PostLikeIn(BaseModel):
    post_id: int


# to display, post what is been liked, the like id, user id.
class PostLike(BaseModel):
    id: int
    user_id: int
