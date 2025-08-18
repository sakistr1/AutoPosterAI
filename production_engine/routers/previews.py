from datetime import datetime
import os
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Body, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import insert, select, desc
from PIL import Image, ImageDraw, ImageFont

from production_engine.engine_database import engine, committed_posts_table
from production_engine.engine_database import pe_templates_table  # για resolve spec
from starlette.responses import JSONResponse

import httpx

# ΝΕΟ: ελληνικός renderer
from production_engine.services.greek_text_renderer import render_image_greek  # <-- προσθήκη

router = APIRouter()


# -----------------------------
# Models
# -----------------------------
class TextFields(BaseModel):
    __root__: dict


class RenderRequest(BaseModel):
    # Αν ΔΕΝ δώσεις template_id => simple compose (logo + extra)
    template_id: Optional[int] = None
    product_id: Optional[int] = None
    post_type: str = "image"
    mode: Optional[str] = None

    brand_logo_url: Optional[str] = None
    extra_images: List[str] = []
    text_fields: Optional[dict] = None  # {"title": "...", "price": "...", "cta": "..."}


class CommitRequest(BaseModel):
    preview_id: str = Field(..., description="Το preview_id που επέστρεψε το /previews/render")
    urls: List[str] = Field(..., description="Τελικές URLs που κάνουμε commit")


# -----------------------------
# Helpers
# -----------------------------
STATIC_ROOT = "production_engine/static"
GENERATED_DIR = os.path.join(STATIC_ROOT, "generated")
# ΝΕΟ: Μόνιμη θέση γραμματοσειρών (εκεί που έβαλες τα NotoSans)
FONTS_DIR = os.path.join("production_engine", "assets", "fonts")  # <-- προσθήκη

os.makedirs(GENERATED_DIR, exist_ok=True)


def _load_template_spec(template_id: int) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            select(
                pe_templates_table.c.id,
                pe_templates_table.c.spec_json
            ).where(pe_templates_table.c.id == template_id)
        ).mappings().first()
    if not row:
        return None
    try:
        return json.loads(row["spec_json"]) if row["spec_json"] else None
    except Exception:
        return None


def _open_image_from_static(url_path: str) -> Image.Image:
    """
    url_path: π.χ. "/static/uploads/brand/abc.png" ή "/static/generated/xyz.png"
    """
    if not url_path.startswith("/static/"):
        raise FileNotFoundError(f"Bad path: {url_path}")
    full = os.path.join("production_engine", url_path.lstrip("/"))
    if not os.path.exists(full):
        # fallback: ίσως είναι ήδη relative στο production_engine/static
        alt = os.path.join("production_engine/static", url_path.replace("/static/", ""))
        if os.path.exists(alt):
            full = alt
        else:
            raise FileNotFoundError(full)
    return Image.open(full).convert("RGBA")


def _paste_fit(img: Image.Image, slot: dict) -> Image.Image:
    # fit: "contain" (default) ή "cover"
    fit = slot.get("fit", "contain")
    x, y, w, h = slot["x"], slot["y"], slot["w"], slot["h"]
    target = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if fit == "cover":
        # scale to cover
        ratio = max(w / img.width, h / img.height)
    else:
        # contain
        ratio = min(w / img.width, h / img.height)

    new_w = max(1, int(img.width * ratio))
    new_h = max(1, int(img.height * ratio))
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    # center crop/pad
    offset_x = max(0, (w - new_w) // 2)
    offset_y = max(0, (h - new_h) // 2)
    target.alpha_composite(resized, (offset_x, offset_y))
    return target


def _draw_text(draw: ImageDraw.ImageDraw, slot: dict, text: str, font_dir: str):
    x, y, w, h = slot["x"], slot["y"], slot["w"], slot["h"]
    align = slot.get("align", "left")
    size = slot.get("font_size", 36)
    color = slot.get("color", "#ffffff")
    bold = slot.get("bold", False)

    # Φόρτωση font με ελληνικά (NotoSans στο assets/fonts)
    font_path = os.path.join(font_dir, "NotoSans-Regular.ttf")
    if bold:
        bold_path = os.path.join(font_dir, "NotoSans-Bold.ttf")
        if os.path.exists(bold_path):
            font_path = bold_path

    try:
        font = ImageFont.truetype(font_path, size=size)
    except Exception:
        font = ImageFont.load_default()

    # απλό draw (τα slots είναι single-line όπως πριν)
    tx = x
    anchor = "lt"
    if align == "center":
        tx = x + w // 2
        anchor = "mt"
    elif align == "right":
        tx = x + w
        anchor = "rt"
    draw.text((tx, y), text, font=font, fill=color, anchor=anchor)


# -----------------------------
# Routes
# -----------------------------
@router.post("/previews/render")
def render_image(payload: RenderRequest):
    """
    Αν υπάρχει template_id + spec: slot-based render.
    Αλλιώς: απλό compose (logo πάνω αριστερά + μέχρι 2 έξτρα εικόνες) -> (τροποποιήθηκε να καλεί ελληνικό renderer).
    Επιστρέφει path για την παραγόμενη εικόνα + preview_id.
    """
    canvas_w, canvas_h = 1080, 1080
    base = Image.new("RGBA", (canvas_w, canvas_h), (20, 20, 20, 255))

    spec = None
    if payload.template_id:
        spec = _load_template_spec(payload.template_id)

    if spec and "canvas_w" in spec and "canvas_h" in spec:
        canvas_w = int(spec["canvas_w"])
        canvas_h = int(spec["canvas_h"])
        base = Image.new("RGBA", (canvas_w, canvas_h), (20, 20, 20, 255))
        if spec.get("background"):
            try:
                bg = _open_image_from_static(spec["background"])
                base.alpha_composite(_paste_fit(bg, {"x": 0, "y": 0, "w": canvas_w, "h": canvas_h, "fit": "cover"}), (0, 0))
            except Exception:
                pass

        # slots
        # ΠΡΙΝ: font_dir = os.path.join(STATIC_ROOT, "fonts")
        font_dir = FONTS_DIR  # <-- Χρήση assets/fonts για ελληνικά
        draw = ImageDraw.Draw(base)
        extra_map = {}
        # source: "extra1"/"extra2"...
        for idx, p in enumerate(payload.extra_images, start=1):
            extra_map[f"extra{idx}"] = p

        for slot in spec.get("slots", []):
            kind = slot.get("kind")
            if kind in ("image", "logo"):
                src = None
                if kind == "logo" and payload.brand_logo_url:
                    src = payload.brand_logo_url
                elif kind == "image":
                    # from slot.source
                    src_key = slot.get("source")
                    if src_key and src_key in extra_map:
                        src = extra_map[src_key]
                if src:
                    try:
                        img = _open_image_from_static(src)
                        piece = _paste_fit(img, slot)
                        base.alpha_composite(piece, (slot["x"], slot["y"]))
                    except Exception:
                        continue
            elif kind == "text":
                text_key = slot.get("text_key")
                val = ""
                if payload.text_fields and text_key:
                    val = str(payload.text_fields.get(text_key, "") or "")
                _draw_text(draw, slot, val, font_dir)
    else:
        # simple compose -> Χρήση ελληνικού renderer με pixel-wrap
        text = (payload.text_fields or {}) if isinstance(payload.text_fields, dict) else {}
        title = str(text.get("title") or (f"Προϊόν #{payload.product_id}" if payload.product_id else "Promo"))
        price = str(text.get("price") or "")
        cta   = str(text.get("cta")   or "Αγόρασε τώρα")

        # brand_logo_url -> filesystem path αν είναι /static/...
        brand_logo_path = None
        if payload.brand_logo_url and isinstance(payload.brand_logo_url, str) and payload.brand_logo_url.startswith("/static/"):
            rel = payload.brand_logo_url[len("/static/"):]  # π.χ. uploads/brand/logo.png
            brand_logo_path = os.path.join(STATIC_ROOT, rel)

        # Ρεντάρουμε προσωρινό PNG και το χρησιμοποιούμε ως base
        tmp_name = f"tmp_{int(datetime.utcnow().timestamp()*1000)}.png"
        tmp_path = os.path.join(GENERATED_DIR, tmp_name)
        render_image_greek(
            tmp_path,
            title=title,
            price=price,
            cta=cta,
            brand_logo_path=brand_logo_path
        )
        base = Image.open(tmp_path).convert("RGBA")

    # save
    preview_id = f"prev_{int(datetime.utcnow().timestamp()*1000)}"
    out_path = os.path.join(GENERATED_DIR, f"{preview_id}.png")
    base.convert("RGB").save(out_path, "PNG")

    return {
        "preview_id": preview_id,
        "preview_url": f"/static/generated/{preview_id}.png"
    }


# -----------------------------
# Credits Guard
# -----------------------------
def credits_guard_should_skip() -> bool:
    return os.getenv("DISABLE_CREDITS_GUARD", "0") in ("1", "true", "True")


async def debit_one_credit(authorization: Optional[str]) -> None:
    """
    Καλεί το κεντρικό backend για χρέωση 1 credit.
    Προεπιλογή endpoint: POST http://localhost:8000/me/use-credit
    - Περνάμε το Authorization header 1:1
    - 200 => OK
    - 401/403 => Unauthorized
    - οτιδήποτε άλλο => αποτυχία χρέωσης
    """
    if credits_guard_should_skip():
        return

    debit_url = os.getenv("CREDITS_DEBIT_URL", "http://localhost:8000/me/use-credit")
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(debit_url, headers=headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Credits service unreachable: {str(e)}")

    if resp.status_code == 401 or resp.status_code == 403:
        raise HTTPException(status_code=401, detail="Unauthorized for credit debit")

    if resp.status_code != 200:
        # Προσπαθούμε να εξηγήσουμε
        try:
            data = resp.json()
        except Exception:
            data = {"detail": resp.text}
        raise HTTPException(status_code=402, detail=f"Credit debit failed: {data}")

    # OK


# -----------------------------
# Commit + History
# -----------------------------
@router.post("/previews/commit")
async def commit_preview(
    payload: CommitRequest,
    authorization: Optional[str] = Header(default=None, alias="Authorization")
):
    """
    1) Credits guard: debit 1 credit στο κεντρικό backend (αν δεν είναι disabled).
    2) Αν ΟΚ, γράφουμε committed_posts.
    """
    await debit_one_credit(authorization)

    now = datetime.utcnow()
    with engine.begin() as conn:
        res = conn.execute(
            insert(committed_posts_table).values(
                preview_id=payload.preview_id,
                urls_json=json.dumps(payload.urls),
                created_at=now
            )
        )
        new_id = res.inserted_primary_key[0]

    return {"post_id": int(new_id), "preview_id": payload.preview_id, "urls": payload.urls, "created_at": now.isoformat() + "Z"}


@router.get("/previews/committed")
def list_committed(limit: int = 20, offset: int = 0):
    """
    Επιστρέφει πρόσφατα commits με basic pagination.
    """
    limit = max(1, min(100, int(limit)))
    offset = max(0, int(offset))

    with engine.connect() as conn:
        rows = conn.execute(
            select(
                committed_posts_table.c.id,
                committed_posts_table.c.preview_id,
                committed_posts_table.c.urls_json,
                committed_posts_table.c.created_at
            ).order_by(desc(committed_posts_table.c.id))
             .limit(limit)
             .offset(offset)
        ).mappings().all()

    out = []
    for r in rows:
        try:
            urls = json.loads(r["urls_json"] or "[]")
        except Exception:
            urls = []
        out.append({
            "id": int(r["id"]),
            "preview_id": r["preview_id"],
            "urls": urls,
            "created_at": r["created_at"].isoformat() + "Z" if r.get("created_at") else None
        })
    return {"items": out, "limit": limit, "offset": offset, "count": len(out)}
