import firebase_admin
from firebase_admin import credentials, db
import os
import json
FIREBASE_DB_URL = os.environ.get("FIREBASE_DATABASE_URL")
FIREBASE_JSON = os.environ.get("FIREBASE_JSON")

def init_firebase():
    if not firebase_admin._apps:  # Prevent re-init
        cred = credentials.Certificate(json.loads(FIREBASE_JSON)) #PRODUCTION-FLAG
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
    return db

db = init_firebase()