# routers/me.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os, json, uuid, time

from database import get_db
from models import User, Post
from token_module import get_current_user

from cairosvg import svg2png  # να είναι εγκατεστημένο

router = APIRouter(prefix="/me", tags=["me"])

# ---------- Schemas ----------
class WooCreds(BaseModel):
    url: str | None = None
    ck: str | None = None
    cs: str | None = None
    sync_url: str | None = None

# ---------- Credits ----------
@router.get("/credits")
def credits(current_user: User = Depends(get_current_user)):
    return {"credits": int(current_user.credits or 0)}

# ---------- Woo credentials ----------
@router.get("/woocommerce-credentials")
def get_wc(current_user: User = Depends(get_current_user)):
    return {
        "url": current_user.woocommerce_url,
        "ck": current_user.consumer_key,
        "cs": current_user.consumer_secret,
        "sync_url": current_user.sync_url,
        "has_credentials": bool(
            current_user.woocommerce_url and current_user.consumer_key and current_user.consumer_secret
        ),
    }

@router.post("/woocommerce-credentials")
def set_wc(body: WooCreds, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.woocommerce_url = body.url
    current_user.consumer_key = body.ck
    current_user.consumer_secret = body.cs
    current_user.sync_url = body.sync_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"ok": True}

# ---------- Posts list ----------
@router.get("/posts")
def my_posts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Post)
        .filter(Post.owner_id == current_user.id)
        .order_by(Post.id.desc())
        .limit(50)
        .all()
    )
    out = []
    for p in rows:
        try:
            media = json.loads(p.media_urls) if isinstance(p.media_urls, str) else (p.media_urls or [])
        except Exception:
            media = []
        out.append({
            "id": p.id,
            "title": getattr(p, "title", "") or "Autoposter Post",
            "type": getattr(p, "type", "image"),
            "status": getattr(p, "status", "pending"),
            "created_at": getattr(p, "created_at", None),
            "media_urls": media,
        })
    return out

# ---------- PNG από SVG finals ----------
@router.get("/posts/{post_id}/png")
def post_png(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = db.query(Post).filter(Post.id == post_id, Post.owner_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="post not found")

    try:
        media = json.loads(p.media_urls) if isinstance(p.media_urls, str) else (p.media_urls or [])
    except Exception:
        media = []
    if not media:
        raise HTTPException(status_code=404, detail="no media")

    svg_url = media[0]
    if not svg_url.startswith("/static/"):
        raise HTTPException(status_code=400, detail="invalid media url")

    # Βρες το static directory από το main app
    from main import app as main_app
    static_dir = None
    for r in main_app.routes:
        try:
            if getattr(r, "path", None) == "/static" and hasattr(r.app, "directory"):
                static_dir = r.app.directory
                break
        except Exception:
            pass
    if not static_dir:
        raise HTTPException(status_code=500, detail="static mount not found")

    svg_path = os.path.join(static_dir, svg_url[len("/static/"):].lstrip("/"))
    if not os.path.isfile(svg_path):
        raise HTTPException(status_code=404, detail="svg not found")

    out_dir = os.path.join(static_dir, "generated", "png")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"post_{post_id}.png")
    svg2png(url=svg_path, write_to=out_path)
    return FileResponse(out_path, media_type="image/png", filename=f"post_{post_id}.png")

# ---------- Upload logo (με ελέγχους) ----------
@router.post("/upload-logo")
def upload_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # MIME & μέγεθος
    allowed = {"image/png", "image/jpeg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    contents = file.file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 2MB)")

    # Verify με Pillow
    from PIL import Image
    import io
    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    # Βρες static dir
    from main import app as main_app
    static_dir = None
    for r in main_app.routes:
        try:
            if getattr(r, "path", None) == "/static" and hasattr(r.app, "directory"):
                static_dir = r.app.directory
                break
        except Exception:
            pass
    if not static_dir:
        raise HTTPException(status_code=500, detail="static mount not found")

    # Save ως PNG
    uploads = os.path.join(static_dir, "uploads", "logos")
    os.makedirs(uploads, exist_ok=True)
    fname = f"logo_{current_user.id}_{int(time.time())}.png"
    fpath = os.path.join(uploads, fname)

    img = Image.open(io.BytesIO(contents)).convert("RGBA")
    img.save(fpath, format="PNG")

    rel = os.path.relpath(fpath, static_dir).replace(os.sep, "/")
    return {"url": f"/static/{rel}", "logo_url": f"/static/{rel}"}
