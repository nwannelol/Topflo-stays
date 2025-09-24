import random
import string
import firebase_admin
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from src.utils import generate_access_token, store_access_token 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from firebase_admin import firestore, credentials

# Initialize Firestore if not already initialized via utils
db = firestore.client()

#Load environmental variables
load_dotenv()

#Environmental variables
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

async def verify_access_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify the access code for managers and grant access if correct."""
    if context.user_data.get("role") == "manager":
        entered_code = update.message.text
        manager_id = update.effective_user.id
        doc_ref = db.collection('managers').document(str(manager_id))
        doc = doc_ref.get()

        if doc.exists:
            stored_token = doc.to_dict().get("token")
            if entered_code == stored_token:
                await update.message.reply_text(
                    "✅ Access granted! You now have access to the property management tools. Type /help to get started."
                )
                context.user_data["status"] = 'Active'  # Mark user as active
            else:
                await update.message.reply_text("❌ Invalid access code. Please try again.")
        else:
            await update.message.reply_text("No access token found. Please generate an access code.")
    else:
        await update.message.reply_text("I'm sorry, I don't understand that command. Type /help for assistance.")

async def verify_paid_access(manager_id):
    """Verify if manager has paid and has valid access."""
    doc_ref = db.collection('managers').document(str(manager_id))
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        if data['status'] == 'active' and data['expiry'] > datetime.now():
            return True
    return False        

def generate_payment_link(manager_email: str, amount: int):
    """Create a payment session and get the payment link."""
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": manager_email,
        "amount": amount * 100,  # Amount in kobo (smallest currency unit)
        "callback_url": "https://your-ngrok-url.ngrok-free.app/webhook"  # This is where Paystack will confirm payment
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        payment_link = response.json()["data"]["authorization_url"]
        return payment_link
    else:
        raise Exception(f"Error generating payment link: {response.json()}")

async def access_management_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grant access to management tools if the user is a paid manager."""
    manager_id = update.effective_user.id  # Assuming the user's ID is used as manager ID

    if await verify_paid_access(manager_id):
        await update.message.reply_text("✅ Access granted to management tools.")
        # Proceed to show management features here
    else:
        await update.message.reply_text(
            "🚫 Access denied. Please complete payment to access management tools."
        )
