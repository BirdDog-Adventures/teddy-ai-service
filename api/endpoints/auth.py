"""
Authentication endpoints
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from api.core.config import settings
from api.core.dependencies import get_db
from api.core.security import verify_password, get_password_hash, get_current_active_user
from api.models import database as models
from api.models import schemas

router = APIRouter()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=schemas.UserResponse)
def register(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(models.User).filter(
            models.User.email == user_data.email
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        db_user = models.User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role.value if hasattr(user_data.role, 'value') else user_data.role,  # Handle enum
            is_active=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return schemas.UserResponse(
            id=str(db_user.id),
            email=db_user.email,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            role=db_user.role,
            is_active=db_user.is_active,
            created_at=db_user.created_at
        )
    except Exception as e:
        import traceback
        print(f"Registration error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and receive access token"""
    # Authenticate user
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "user_id": str(current_user.id)},
        expires_delta=access_token_expires
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(
    current_user: models.User = Depends(get_current_active_user)
):
    """Get current user information"""
    return schemas.UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
