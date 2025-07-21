from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import router as auth_router
from app.chat import router as chat_router
from models import ChatMessage
from app.mongo_client import chat_collection
from fastapi.middleware.cors import CORSMiddleware

import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000"
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include routers
app.include_router(auth_router)
app.include_router(chat_router)

# Serve static files (e.g., styles, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates directory
templates = Jinja2Templates(directory="static")


# 🔥 Serve login page at "/"
@app.get("/", response_class=HTMLResponse)
async def serve_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# Optional: Serve app only for authenticated users
def serve_or_authenticate(request: Request):
    if not request.cookies.get("access_token"):
        return RedirectResponse("/auth/login")
    return FileResponse(os.path.join("static", "index.html"))


# 🔁 Store a chat message
@app.post("/log")
async def log_message(msg: ChatMessage):
    result = await chat_collection.insert_one(msg.dict())
    return {"inserted_id": str(result.inserted_id)}


# 🔁 Retrieve messages by session
@app.get("/messages/")
async def get_messages(session_id: str):
    messages = await chat_collection.find({"session_id": session_id}).to_list(100)
    return messages


@app.get("/chat", response_class=HTMLResponse)
async def chat_home(request: Request):
    if not request.cookies.get("access_token"):
        return RedirectResponse("/auth/login")
    return FileResponse(os.path.join("static", "index.html"))
