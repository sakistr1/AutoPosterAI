from __future__ import annotations
from pathlib import Path
import json, re
from typing import Any, Dict, List, Optional, Tuple, Literal
from pydantic import BaseModel, validator
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Πού βρίσκονται τα templates
TEMPLATES_DIR = Path("assets/templates")
STATIC_ROOT   = Path("production_engine/static")

# ---------------- Models ----------------
class FieldDef(BaseModel):
    type: str                          # text|price|image|color|url
    required: bool = False
    max_chars: Optional[int] = None
    default: Optional[Any] = None
    format: Optional[str] = None
    @validator("type")
    def _type_ok(cls, v: str) -> str:
        allowed = {"text", "price", "image", "color", "url"}
        if v not in allowed:
            raise ValueError(f"Unsupported field type: {v}")
        return v

class TemplateMeta(BaseModel):
    id: str
    name: str
    version: str
    ratios: List[str]
    fields: Dict[str, FieldDef]
    render: Dict[str, Any] = {}

class Slot(BaseModel):
    kind: Literal["image", "text", "logo"]
    field: str
    x: float
    y: float
    w: float | None = None
    h: float | None = None
    fit: Literal["cover", "contain"] | None = None
    align: Literal["start", "middle", "end"] | None = None
    width_px: float | None = None
    max_lines: int | None = None
    line_height: float | None = None
    raw_tag: str | None = None

class TemplateRecord(BaseModel):
    meta: TemplateMeta
    dir: Path
    template_file: Path
    thumb_file: Optional[Path] = None
    slots: Dict[str, Slot] = {}
    class Config:
        arbitrary_types_allowed = True

# ---------------- Helpers ----------------
def _looks_like_hex_color(s: str) -> bool:
    if not isinstance(s, str): return False
    s = s.strip()
    return s.startswith("#") and len(s) in (4,7) and all(ch in "0123456789abcdefABCDEF" for ch in s[1:])

def _looks_like_url(s: str) -> bool:
    if not isinstance(s, str): return False
    s2 = s.strip().lower()
    return s2.startswith("http://") or s2.startswith("https://") or s2.startswith("/static/") or s2.startswith("/assets/")

_attr_re = re.compile(r'([a-zA-Z_:.-]+)\s*=\s*"([^"]*)"')

def _parse_attrs(tag: str) -> Dict[str, str]:
    return {k: v for k, v in _attr_re.findall(tag)}

def _scan_slots_from_svg(svg_text: str) -> Dict[str, Slot]:
    """
    Απλός scanner: βρίσκει elements που έχουν data-slot="image:field" / "text:field" / "logo:field"
    και διαβάζει x,y,width,height + extra data-* attributes.
    """
    slots: Dict[str, Slot] = {}
    for m in re.finditer(r'<\s*(rect|text|image|g)\b[^>]*>', svg_text, flags=re.IGNORECASE):
        tag = m.group(0)
        attrs = _parse_attrs(tag)
        data_slot = attrs.get("data-slot")
        if not data_slot:
            continue
        try:
            kind, field = data_slot.split(":", 1)
            kind = kind.strip().lower()
            field = field.strip()
            if kind not in ("image", "text", "logo"):
                continue
        except ValueError:
            continue

        def fget(name, cast=float, default=None):
            v = attrs.get(name)
            if v is None: return default
            try: return cast(v)
            except: return default

        slot = Slot(
            kind=kind,
            field=field,
            x=fget("x") or 0.0,
            y=fget("y") or 0.0,
            w=fget("width"),
            h=fget("height"),
            fit=attrs.get("data-fit"),
            align=attrs.get("data-align"),
            width_px=fget("data-width"),
            max_lines=fget("data-max-lines", int),
            line_height=fget("data-line-height", float),
            raw_tag=tag.split("<",1)[1].split()[0].lower()
        )
        slots[field] = slot
    return slots

# ---------------- Registry ----------------
class TemplateRegistry:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._records: Dict[str, TemplateRecord] = {}
        self._env_cache: Dict[Path, Environment] = {}
        self.reload()

    def reload(self) -> None:
        self._records.clear()
        if not self.base_dir.exists(): return
        for sub in self.base_dir.iterdir():
            if not sub.is_dir(): continue
            meta_path = sub / "meta.json"
            tpl_path  = sub / "template.svg.j2"
            if not meta_path.exists() or not tpl_path.exists(): continue
            try:
                meta = TemplateMeta.parse_obj(json.loads(meta_path.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"[template_registry] meta.json error in {sub.name}: {e}")
                continue
            try:
                svg_text = tpl_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                svg_text = tpl_path.read_text(encoding="latin-1", errors="ignore")
            rec = TemplateRecord(
                meta=meta,
                dir=sub,
                template_file=tpl_path,
                thumb_file=(sub / "thumb.png") if (sub / "thumb.png").exists() else None,
                slots=_scan_slots_from_svg(svg_text),
            )
            self._records[meta.id] = rec

    def list_public(self) -> List[Dict[str, Any]]:
        out = []
        for rec in self._records.values():
            out.append({
                "id": rec.meta.id,
                "name": rec.meta.name,
                "version": rec.meta.version,
                "ratios": rec.meta.ratios,
                "fields": {
                    k: {
                        "type": v.type, "required": v.required,
                        "max_chars": v.max_chars, "default": v.default, "format": v.format,
                    } for k, v in rec.meta.fields.items()
                },
                "thumb_url": self.get_thumb_url(rec),
                "has_map": bool(rec.slots),
            })
        return out

    def get(self, template_id: str) -> TemplateRecord:
        if template_id not in self._records:
            raise KeyError(f"Template '{template_id}' not found")
        return self._records[template_id]

    def get_thumb_url(self, rec: TemplateRecord) -> Optional[str]:
        if rec.thumb_file is None: return None
        try:
            rel = rec.thumb_file.relative_to(STATIC_ROOT)
            return f"/static/{rel.as_posix()}"
        except ValueError:
            rel = rec.thumb_file.relative_to(self.base_dir.parent)
            return f"/{rel.as_posix()}"

    def _env_for(self, rec_dir: Path) -> Environment:
        if rec_dir not in self._env_cache:
            self._env_cache[rec_dir] = Environment(
                loader=FileSystemLoader(str(rec_dir)),
                autoescape=select_autoescape(enabled_extensions=("svg", "svg.j2")),
            )
        return self._env_cache[rec_dir]

    def validate_and_merge(self, rec: TemplateRecord, payload: Dict[str, Any], ratio: Optional[str]) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        if ratio and ratio not in rec.meta.ratios:
            raise ValueError(f"Unsupported ratio '{ratio}' for template '{rec.meta.id}'. Allowed: {rec.meta.ratios}")

        ctx: Dict[str, Any] = {}
        # defaults
        for fname, fdef in rec.meta.fields.items():
            if fdef.default is not None:
                ctx[fname] = fdef.default
        # overrides
        for k, v in payload.items():
            ctx[k] = v

        # validation
        for fname, fdef in rec.meta.fields.items():
            present = fname in ctx and ctx[fname] not in (None, "")
            if fdef.required and not present:
                raise ValueError(f"Missing required field: '{fname}'")
            if not present: continue
            val = ctx[fname]
            if fdef.type == "text":
                if not isinstance(val, str): ctx[fname] = str(val)
                if fdef.max_chars and len(ctx[fname]) > fdef.max_chars:
                    ctx[fname] = ctx[fname][:fdef.max_chars]
                    warnings.append(f"{fname} truncated to {fdef.max_chars} chars")
            elif fdef.type == "price":
                if isinstance(val, (int, float)):
                    num = float(val)
                else:
                    try: num = float(str(val).replace(",", ".").replace("€", "").strip())
                    except: raise ValueError(f"Invalid price value for '{fname}': {val}")
                ctx[fname] = fdef.format.replace("{value}", f"{num:.2f}") if fdef.format else f"{num:.2f}"
            elif fdef.type in ("image", "url"):
                if not _looks_like_url(str(val)):
                    raise ValueError(f"Field '{fname}' must be a valid URL (/static, /assets or http(s))")
            elif fdef.type == "color":
                if not _looks_like_hex_color(str(val)):
                    raise ValueError(f"Field '{fname}' must be a hex color like #22c55e")
        if ratio: ctx["ratio"] = ratio
        return ctx, warnings

    def render_svg(self, rec: TemplateRecord, context: Dict[str, Any]) -> str:
        env = self._env_for(rec.dir)
        tpl = env.get_template("template.svg.j2")
        return tpl.render(**context, meta=rec.meta.dict())

    # -------- expose mapping --------
    def get_map(self, rec: TemplateRecord) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for fname, s in rec.slots.items():
            out[fname] = {
                "kind": s.kind, "x": s.x, "y": s.y, "w": s.w, "h": s.h,
                "fit": s.fit, "align": s.align, "width_px": s.width_px,
                "max_lines": s.max_lines, "line_height": s.line_height
            }
        return out

# singleton
REGISTRY = TemplateRegistry(TEMPLATES_DIR)
