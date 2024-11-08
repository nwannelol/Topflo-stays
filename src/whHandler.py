import datetime
import hmac
import hashlib
import os
from flask import Flask, request, jsonify
from firebase_admin import firestore
from utils import store_access_token

app = Flask(__name__)
db = firestore.client()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Verify Paystack payment and update Firestore for the manager."""
    payload = request.get_data()
    signature = request.headers.get("x-paystack-signature")

    # Verify webhook signature
    computed_signature = hmac.new(PAYSTACK_SECRET_KEY.encode("utf-8"), payload, hashlib.sha512).hexdigest()
    if computed_signature != signature:
        return jsonify({"status": "error", "message": "Invalid signature"}), 403

    # Handle the event
    event = request.json
    if event["event"] == "charge.success":
        manager_email = event["data"]["customer"]["email"]

        # Update Firestore for this manager
        manager_ref = db.collection("managers").where("email", "==", manager_email).get()
        if manager_ref:
            manager_id = manager_ref[0].id
            store_access_token(manager_id)  # Store access token with expiration

            db.collection("managers").document(manager_id).update({
                "status": "active",
                "expiry": datetime.now() + datetime.timedelta(days=30)
            })

    return jsonify({"status": "success"}), 200
