from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.community import Community
from app.models.user import User
from app.schemas.community import CommunityCreate, CommunityOut

router = APIRouter(prefix="/communities", tags=["communities"])


@router.post("", response_model=CommunityOut, status_code=status.HTTP_201_CREATED)
def create_community(
    payload: CommunityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Community).filter(Community.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Community name already taken")

    community = Community(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(community)
    db.commit()
    db.refresh(community)
    return community


@router.get("", response_model=list[CommunityOut])
def list_communities(db: Session = Depends(get_db)):
    return db.query(Community).order_by(Community.name).all()
