from fastapi import APIRouter, HTTPException
from services.template_registry import REGISTRY

router = APIRouter(prefix="/templates", tags=["templates"])

@router.get("")
def list_templates():
    return REGISTRY.list_public()

@router.get("/{template_id}")
def get_template(template_id: str):
    try:
        rec = REGISTRY.get(template_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": rec.meta.id,
        "name": rec.meta.name,
        "version": rec.meta.version,
        "ratios": rec.meta.ratios,
        "fields": {
            k: {
                "type": v.type,
                "required": v.required,
                "max_chars": v.max_chars,
                "default": v.default,
                "format": v.format,
            } for k, v in rec.meta.fields.items()
        },
        "render": rec.meta.render,
        "thumb_url": REGISTRY.get_thumb_url(rec),
        "map": REGISTRY.get_map(rec),
    }

@router.post("/reload")
def reload_templates():
    REGISTRY.reload()
    return {"ok": True, "count": len(REGISTRY.list_public())}
