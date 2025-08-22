# main.py — include routers από routers.* ΚΑΙ production_engine.routers.*
from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from importlib import import_module

app = FastAPI(title="Autoposter AI")

# Static & Templates
app.mount("/static", StaticFiles(directory="production_engine/static"), name="static")
# ΝΕΟ: σερβίρουμε τα αρχεία templates (thumbs κ.λπ.)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

# ---------------- HTML pages ----------------
@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard_html(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/auth.html", response_class=HTMLResponse)
async def auth_html(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/dashboard.html")

# ------------- Dynamic include routers (με dedupe, 2 namespaces) -------------
def include_all_routers(module_name: str, seen_ids: set[int], namespace: str):
    """
    Κάνει import <namespace>.<module_name> και κάνει include ΚΑΘΕ attribute που είναι APIRouter.
    """
    try:
        mod = import_module(f"{namespace}.{module_name}")
    except Exception:
        return
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, APIRouter):
            oid = id(obj)
            if oid in seen_ids:
                continue
            app.include_router(obj)
            seen_ids.add(oid)

seen: set[int] = set()

# modules που μας νοιάζουν
modules = (
    "auth", "users", "me", "tengine", "dashboard", "templates",
    "products", "posts", "sync", "mock_woocommerce",
)

# ψάξε πρώτα στο παλιό namespace
for name in modules:
    include_all_routers(name, seen, "routers")

# και μετά στο production_engine.routers (εκεί βρίσκεται ο tengine)
for name in modules:
    include_all_routers(name, seen, "production_engine.routers")

# Υγεία
@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"ok": True}
