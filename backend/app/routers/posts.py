from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.community import Community
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PaginatedPosts, PostCreate, PostOut

router = APIRouter(tags=["posts"])


def _get_community_or_404(db: Session, community_id: int) -> Community:
    community = db.get(Community, community_id)
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community


@router.post(
    "/communities/{community_id}/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED
)
def create_post(
    community_id: int,
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_community_or_404(db, community_id)

    post = Post(
        title=payload.title,
        content=payload.content,
        author_id=current_user.id,
        community_id=community_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/communities/{community_id}/posts", response_model=PaginatedPosts)
def list_posts(
    community_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _get_community_or_404(db, community_id)

    base_query = db.query(Post).filter(Post.community_id == community_id)
    total = base_query.count()

    items = (
        base_query.order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedPosts(items=items, total=total, page=page, page_size=page_size)
