from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

# HTTPBearer reads the "Authorization: Bearer <token>" header for us --
# missing header -> FastAPI auto-rejects with 401 before get_current_user even runs
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        claims = decode_token(credentials.credentials)
    except ValueError:
        raise credentials_error

    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise credentials_error

    return user
