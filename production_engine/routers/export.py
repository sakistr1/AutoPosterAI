from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os, json

from database import get_db
from token_module import get_current_user
from models import Post

try:
    from cairosvg import svg2png
except Exception as e:
    svg2png = None

router = APIRouter(prefix="/me", tags=["export"])

@router.get("/posts/{post_id}/png")
def export_post_png(post_id: int,
                    db: Session = Depends(get_db),
                    current_user = Depends(get_current_user)):
    if svg2png is None:
        raise HTTPException(500, "cairosvg not available")

    post = db.query(Post).filter(
        Post.id == post_id, Post.owner_id == current_user.id
    ).first()
    if not post:
        raise HTTPException(404, "Post not found")

    # Πάρε πρώτο media URL (το SVG που φτιάξαμε στο commit)
    media_urls = []
    v = getattr(post, "media_urls", None)
    if isinstance(v, str):
        try:
            media_urls = json.loads(v)
        except Exception:
            media_urls = []
    elif isinstance(v, list):
        media_urls = v

    if not media_urls:
        raise HTTPException(400, "No media on post")

    svg_url = media_urls[0]
    if not svg_url.startswith("/static/"):
        raise HTTPException(400, "Unsupported media path")

    # Μετέτρεψε /static/... σε πραγματικό path κάτω από production_engine/static
    rel = svg_url.split("/static/", 1)[1]
    svg_path = os.path.join("production_engine", "static", rel)
    if not os.path.exists(svg_path):
        raise HTTPException(404, "SVG file missing")

    png_path = os.path.splitext(svg_path)[0] + ".png"
    with open(svg_path, "rb") as f:
        svg2png(bytestring=f.read(), write_to=png_path)

    return FileResponse(png_path, media_type="image/png",
                        filename=os.path.basename(png_path))
