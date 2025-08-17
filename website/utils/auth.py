
import jwt
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
import os

JWT_SECRET = os.environ.get("JWT_SECRET")


def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        return None  # Not logged in
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        return None