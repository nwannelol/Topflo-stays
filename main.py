from typing import Final
from manager import generate_access_token
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from firebase_admin import credentials, firestore


# Parameters
TOKEN: Final = '8136364110:AAHVzxRNRZ7OFj_osz9IZCLAsrl_v15BzwY'
BOT_USERNAME: Final = 'nwanne1bot'
MANAGER_ACCESS_CODE: Final = generate_access_token()


# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a start message with role selection when the /start command is issued."""
    context.user_data["history"] = [] 
    await send_role_selection(update)                                               



async def send_role_selection(update: Update) -> None:
    """Display role selection options to the user."""
    keyboard = [
        [InlineKeyboardButton("I am a Topflo stays Manager", callback_data="manager")], # Add emojis to the manager and client
        [InlineKeyboardButton("I am a Topflo stays Client", callback_data="client")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to Topflo stays! Please select your role to continue:",
        reply_markup=reply_markup
    )



async def handle_role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the role selection and prompt for access code if manager."""
    query = update.callback_query
    await query.answer()
    
    # Track the pages in history
    context.user_data['history'].append('role_selection')

    if query.data == "manager":
        # Prompt for access code and include a back button
        await query.edit_message_text(
            "Please enter your manager access code to unlock property management tools.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])
        )
        context.user_data['history'].append('manager_access')
        context.user_data["role"] = "manager"  # Track role in user data
    elif query.data == "client":
        # Display client options with a back button
        await query.edit_message_text(
            "Welcome, Client! How can I assist you today? Type /help to see what I can do for you.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])
        )
        context.user_data["history"].append("client_menu")
        context.user_data["role"] = "client"  # Track role in user data

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Back' button to navigate to the previous page."""
    query = update.callback_query
    await query.answer()

    # Remove the current page from history
    if context.user_data["history"]:
        context.user_data["history"].pop()

    # Go back to the last page in history
    if context.user_data["history"]:
        last_page = context.user_data["history"].pop()
        if last_page == "role_selection":
            await send_role_selection(query)
        elif last_page == "manager_access":
            await query.edit_message_text(
                "Please enter your manager access code to unlock property management tools.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])
            )
            context.user_data["history"].append("manager_access")
        elif last_page == "client_menu":
            await query.edit_message_text(
                "Welcome, Client! How can I assist you today? Type /help to see what I can do for you.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])
            )
            context.user_data["history"].append("client_menu")






async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide a list of available commands."""
    await update.message.reply_text(
        "/start - Welcome message\n"
        "/help - List of commands\n"
        "/bookings_today - View today's bookings\n"
        "/availability - Check property availability\n"
        "/price_recommendation - Get pricing recommendations\n"
    )



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general messages."""
    text = update.message.text.lower()
    response = "I'm sorry, I don't understand that command. Type /help to see available commands."
    
    # Respond based on the message content
    if 'hello' in text:
        response = "Hello! How can I assist you with property management today?"

    await update.message.reply_text(response)



def main() -> None:
    """Start the bot."""
    # Initialize the application
    application = Application.builder().token(TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_role_selection, pattern="^(manager|client)$"))
    application.add_handler(CallbackQueryHandler(handle_back, pattern="^back$"))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()

