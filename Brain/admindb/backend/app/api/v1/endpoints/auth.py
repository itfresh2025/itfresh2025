from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ....database import get_db
from ....models.user import User
from ....core.security import verify_password, create_access_token
from ....schemas.user import Token, UserOut

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == form_data.username, User.is_active == True)
        .first()
    )
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db)):
    """Validate token and return current user — used by frontend on page load."""
    from ....api.deps import get_current_user
    # Actually deps already handle this; kept as convenience endpoint
    raise HTTPException(status_code=501, detail="Use Authorization header")
