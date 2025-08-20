from production_engine.routers import tengine as tengine_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Υπάρχοντες routers από το κύριο app
from routers import users, auth, me, dashboard, templates

# previews ζει στο production_engine/routers
from production_engine.routers import previews
from production_engine.routers import templates_engine as tengine  # ✅ ΠΡΟΣΘΗΚΗ

# assets: κάνε import απ’ όπου κι αν το έχεις (production_engine/routers ή ρίζα)
try:
    from production_engine.routers import assets as _assets_module  # προτιμώμενο
except ImportError:
    import assets as _assets_module  # fallback αν έχεις assets.py στη ρίζα

app = FastAPI()
# TEngine (preview/commit)
app.include_router(tengine_router.router)

# /static πρέπει να σερβίρει τον φάκελο production_engine/static
app.mount("/static", StaticFiles(directory="production_engine/static"), name="static")

templates_env = Jinja2Templates(directory="templates")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # σφίγγεις αργότερα
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (κύριο app)
app.include_router(users.router, prefix="/users")
app.include_router(auth.router, prefix="/auth")
app.include_router(me.router, prefix="/me")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(templates.router)

# Routers (production_engine + assets)
app.include_router(previews.router)
app.include_router(_assets_module.router, prefix="/assets")
app.include_router(tengine.router)  # ✅ ΠΡΟΣΘΗΚΗ

@app.get("/")
async def root():
    return {"message": "AutoPoster AI is running"}

# HTML endpoints
@app.get("/dashboard.html")
async def get_dashboard_html():
    return FileResponse("templates/dashboard.html")

@app.get("/auth.html")
async def get_auth_html():
    return FileResponse("templates/auth.html")

@app.get("/dashboard2.html")
async def get_dashboard2_html():
    from fastapi.responses import FileResponse
    return FileResponse("templates/dashboard.html")
    return FileResponse("templates/dashboard2.html")
