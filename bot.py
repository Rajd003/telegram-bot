import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient

# ========= ENV =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["bot"]
collection = db["numbers"]

# ========= Fake Server =========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot Running')

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web).start()

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📱 Get Number", "🌍 Available Country"],
        ["✅ Active Number", "☎️ Support"]
    ]

    await update.message.reply_text(
        "Welcome! Choose your option:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ========= GET NUMBER =========
async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = collection.distinct("country")

    buttons = []
    for c in countries:
        count = collection.count_documents({"country": c, "status": "free"})
        buttons.append([InlineKeyboardButton(f"{c} ({count})", callback_data=c)])

    await update.message.reply_text(
        "🌍 Select Country:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========= COUNTRY SELECT =========
async def country_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    country = query.data

    data = collection.find_one({"country": country, "status": "free"})

    if not data:
        await query.edit_message_text("❌ No number available")
        return

    collection.update_one({"_id": data["_id"]}, {"$set": {"status": "used"}})

    text = f"""
🌍 {country} Fresh Number Assigned

📱 Number:
`{data['number']}`

⏳ Wait for OTP...
"""

    buttons = [
        [InlineKeyboardButton("📩 View OTP", url="https://t.me/your_group")],
        [
            InlineKeyboardButton("🔄 Change Number", callback_data="change"),
            InlineKeyboardButton("🌍 Change Country", callback_data="back")
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# ========= BACK =========
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    countries = collection.distinct("country")

    buttons = []
    for c in countries:
        count = collection.count_documents({"country": c, "status": "free"})
        buttons.append([InlineKeyboardButton(f"{c} ({count})", callback_data=c)])

    await query.edit_message_text(
        "🌍 Select Country:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========= TEXT HANDLER =========
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📱 Get Number":
        await get_number(update, context)

    elif text == "🌍 Available Country":
        countries = collection.distinct("country")
        msg = "\n".join(countries)
        await update.message.reply_text(f"🌍 Countries:\n{msg}")

    elif text == "✅ Active Number":
        await update.message.reply_text("📭 No active number")

    elif text == "☎️ Support":
        await update.message.reply_text("Contact Admin")

# ========= MAIN =========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(country_select))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()