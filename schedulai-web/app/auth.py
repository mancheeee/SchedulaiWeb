from pymongo import MongoClient
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from app.config import SCOPES, REDIRECT_URI
import os
from dotenv import load_dotenv

router = APIRouter()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# In-memory token store (optional)
user_tokens = {}

load_dotenv()
# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["schedulai_db"]
users_collection = db["users"]


@router.get("/auth/login")
def login():
    flow = Flow.from_client_secrets_file(
        "credentials.json", scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
def auth_callback(request: Request):
    flow = Flow.from_client_secrets_file(
        "credentials.json", scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    user_id = "demo_user"

    cred_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"credentials": cred_dict}},
        upsert=True,
    )

    user_tokens[user_id] = cred_dict

    response = RedirectResponse(url="/static/index.html")
    response.set_cookie(key="access_token", value=credentials.token, httponly=True)
    return response


@router.get("/auth/check")
def auth_check(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="❌ Not authenticated")
    return {"status": "✅ Authenticated"}
