import random
import string
import firebase_admin
from datetime import datetime, timedelta
from firebase_admin import firestore, credentials

# Initialize Firebase Admin SDK with Firestore
cred = credentials.Certificate("topflostays-firebase-adminsdk-5mnwq-02576eca36.json")
firebase_admin.initialize_app(cred)

db = firestore.client()  # Firestore client

def generate_access_token():
    """Generates a unique access token for managers."""
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return token

def store_access_token(manager_id):
    """Store token and validity in database after payment."""
    token = generate_access_token()
    expiration_date = datetime.now() + timedelta(days=30)  # 30 days validity

    db.collection('managers').document(manager_id).set({
        'token': token,
        'status': 'active',
        'expiry': expiration_date
    })
    print(token)
    return token

