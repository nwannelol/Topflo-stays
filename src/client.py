from telegram import Update
from telegram.ext import ContextTypes

async def handle_client_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").lower()
    if "help" in text:
        await update.message.reply_text("You can ask about availability, pricing, and amenities. Try typing 'availability'.")
    else:
        await update.message.reply_text("Tell me what you're looking for: dates, location, budget, or amenities.")
