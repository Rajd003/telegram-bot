from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

TOKEN = "7241764201:AAF2QraxrJXWerLG0ayotQ8mzKoSyEgha8Y"

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data='get_number')],
        [InlineKeyboardButton("💰 Balance", callback_data='balance')]
    ]

    await update.message.reply_text(
        "Welcome 👋",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_click(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'get_number':
        await query.edit_message_text("📱 Get Number clicked")

    elif query.data == 'balance':
        await query.edit_message_text("💰 Balance: ₹0")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))

app.run_polling()