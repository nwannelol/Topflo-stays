import random
import string
import os
import firebase_admin
from datetime import datetime, timedelta
from firebase_admin import firestore, credentials

# Initialize Firebase Admin SDK with Firestore, tolerating missing credentials locally
_db = None
try:
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "topflostays-firebase-adminsdk-5mnwq-02576eca36.json")
    if os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to default app (e.g., GOOGLE_APPLICATION_CREDENTIALS)
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
    _db = firestore.client()
except Exception:
    _db = None

db = _db  # Firestore client (may be None if not configured)

def generate_access_token():
    """Generates a unique access token for managers."""
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return token

def store_access_token(manager_id):
    """Store token and validity in database after payment."""
    token = generate_access_token()
    expiration_date = datetime.now() + timedelta(days=30)  # 30 days validity

    if db is None:
        raise RuntimeError("Firestore is not configured. Set FIREBASE_SERVICE_ACCOUNT or GOOGLE_APPLICATION_CREDENTIALS.")

    db.collection('managers').document(manager_id).set({
        'token': token,
        'status': 'active',
        'expiry': expiration_date
    })
    print(token)
    return token

