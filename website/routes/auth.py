from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx
from datetime import datetime, timedelta
from jose import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import firebase_admin
from firebase_admin import credentials, db
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.environ.get("JWT_SECRET")
FIREBASE_DB_URL = os.environ.get("FIREBASE_DATABASE_URL")
FIREBASE_JSON = os.environ.get("FIREBASE_JSON")


if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_JSON) #change it in production remind me
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

REDIRECT_URI = "http://localhost:8000/auth/callback"
ALGORITHM = "HS256"

@router.get("/login")
def login():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    # Proper async POST request without async with
    async_client = httpx.AsyncClient()
    token_response = await async_client.post(token_url, data=data)
    await async_client.aclose()

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get token from Google")

    tokens = token_response.json()
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="ID token missing from response")

    try:
        idinfo = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Invalid ID token: {str(e)}")

    user_id = idinfo["sub"]
    email = idinfo.get("email")
    name = idinfo.get("name", "")

    user_ref = db.reference(f"users/{user_id}")
    user_ref.update({
        "email": email,
        "name": name,
        "last_login": datetime.utcnow().isoformat()
    })

    payload = {
    "sub": user_id,
    "email": email,
    "name": name,  # Add the user's name here
    "exp": datetime.utcnow() + timedelta(days=30)
    }   
    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

    response = RedirectResponse(url="http://localhost:8000/dashboard")  # Your frontend URL here
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=False,  # Change to True in production with HTTPS
        samesite="lax",
        max_age=30 * 24 * 3600,  # 30 days in seconds
        path="/"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    # Remove the cookie by setting it to empty and expire immediately
    response.delete_cookie("access_token", path="/")
    return response