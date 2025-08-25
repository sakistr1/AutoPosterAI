from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# ίδια Session / User με την app
from database import SessionLocal
from models.user import User

# ΠΟΛΥ ΣΗΜΑΝΤΙΚΟ: ίδιο module με τα υπόλοιπα endpoints
from token_module import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def _auth_core(db: Session, username: str, password: str) -> dict:
    user = db.query(User).filter((User.email == username) | (User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        {"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # γύρνα "Bearer" (κεφαλαίο Β) για να είμαστε safe με client-side
    return {"access_token": token, "token_type": "Bearer"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return _auth_core(db, form_data.username, form_data.password)

@router.post("/token")
def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 password grant συμβατό
    return _auth_core(db, form_data.username, form_data.password)
