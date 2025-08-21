from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from database import get_db
from token_module import get_current_user
from models import Post

router = APIRouter(prefix="/me", tags=["posts"])

def _media_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    try:
        return json.loads(v)
    except Exception:
        return [str(v)]

@router.get("/posts")
def list_posts(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    q = db.query(Post).filter(Post.owner_id == current_user.id).order_by(Post.created_at.desc())
    out = []
    for p in q.all():
        out.append({
            "id": p.id,
            "title": getattr(p, "title", None),
            "type": getattr(p, "type", None),
            "status": getattr(p, "status", None),
            "created_at": getattr(p, "created_at", None),
            "media_urls": _media_list(getattr(p, "media_urls", None)),
        })
    return out

@router.get("/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    p = db.query(Post).filter(Post.id == post_id, Post.owner_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": p.id,
        "title": getattr(p, "title", None),
        "content": getattr(p, "content", None),
        "type": getattr(p, "type", None),
        "status": getattr(p, "status", None),
        "created_at": getattr(p, "created_at", None),
        "media_urls": _media_list(getattr(p, "media_urls", None)),
    }
