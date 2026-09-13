from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostCreate(BaseModel):
    title: str
    content: str | None = None


class PostOut(BaseModel):
    id: int
    title: str
    content: str | None
    author_id: int
    community_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPosts(BaseModel):
    items: list[PostOut]
    total: int
    page: int
    page_size: int
