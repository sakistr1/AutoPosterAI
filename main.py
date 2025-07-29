from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from routers import (
    users_router,
    me_router,
    auth_router,
    dashboard,
    templates_router,
)
from database import engine, Base
from models import User, Product, Post
from decouple import config

Base.metadata.create_all(bind=engine)

app = FastAPI()

print(f"[DEBUG main.py] Loaded Stripe Secret Key: {config('STRIPE_SECRET_KEY')[:10]}...")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/users")
app.include_router(auth_router, prefix="/auth")
app.include_router(me_router, prefix="/me")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(templates_router, prefix="/templates")

# Serve dashboard.html
@app.get("/dashboard.html")
async def get_dashboard():
    return FileResponse("templates/dashboard.html")

# Serve auth.html
@app.get("/auth.html")
async def get_auth():
    return FileResponse("templates/auth.html")
