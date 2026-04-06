import asyncio
import csv
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from pymongo import MongoClient

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# ================== Mongo ==================
client = MongoClient(MONGO_URI)
db = client["sms_bot"]
numbers_col = db["numbers"]
users_col = db["users"]

print("✅ Mongo Connected")

# ================== Fake Web Server ==================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot running')

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web).start()

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data="get")],
        [InlineKeyboardButton("🌍 Available Country", callback_data="country")],
        [InlineKeyboardButton("📞 Active Number", callback_data="active")],
        [InlineKeyboardButton("☎️ Support", callback_data="support")]
    ]

    await update.message.reply_text(
        "👋 Welcome! Choose your option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(" ", reply_markup=ReplyKeyboardRemove())

# ================== COPY NUMBER ==================
async def copy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    num = query.data.split("_")[1]

    await query.answer(text=f"Copied: {num}", show_alert=True)

# ================== GET COUNTRY ==================
async def get_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    countries = numbers_col.distinct("country")
    buttons = []

    for c in countries:
        count = numbers_col.count_documents({"country": c, "status": "free"})
        buttons.append([InlineKeyboardButton(f"{c} ({count})", callback_data=f"country_{c}")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])

    await query.edit_message_text(
        "🌍 Select Country:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================== SELECT COUNTRY ==================
async def select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    country = query.data.split("_")[1]

    number = numbers_col.find_one({"country": country, "status": "free"})
    if not number:
        await query.edit_message_text("❌ No number available")
        return

    numbers_col.update_one({"_id": number["_id"]}, {"$set": {"status": "used"}})

    users_col.update_one(
        {"user_id": query.from_user.id},
        {"$set": {"number_id": number["_id"]}},
        upsert=True
    )

    num = number['number']

    keyboard = [
        [InlineKeyboardButton("📋 Copy Number", callback_data=f"copy_{num}")],
        [InlineKeyboardButton("📩 View OTP", url="https://t.me/otpbossrahul")],
        [
            InlineKeyboardButton("🔄 Change Number", callback_data=f"change_{country}"),
            InlineKeyboardButton("🌍 Change Country", callback_data="get")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]

    await query.edit_message_text(
        f"✅ {country} Number Assigned\n\n📱 `{num}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== CHANGE NUMBER ==================
async def change_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    country = query.data.split("_")[1]

    number = numbers_col.find_one({"country": country, "status": "free"})
    if not number:
        await query.edit_message_text("❌ No new number")
        return

    numbers_col.update_one({"_id": number["_id"]}, {"$set": {"status": "used"}})

    num = number['number']

    keyboard = [
        [InlineKeyboardButton("📋 Copy Number", callback_data=f"copy_{num}")],
        [InlineKeyboardButton("📩 View OTP", url="https://t.me/otpbossrahul")],
        [
            InlineKeyboardButton("🔄 Change Number", callback_data=f"change_{country}"),
            InlineKeyboardButton("🌍 Change Country", callback_data="get")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]

    await query.edit_message_text(
        f"🔄 New Number:\n\n📱 `{num}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== ACTIVE NUMBER ==================
async def active_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = users_col.find_one({"user_id": query.from_user.id})
    if not user:
        await query.edit_message_text("❌ No active number")
        return

    number = numbers_col.find_one({"_id": user["number_id"]})

    await query.edit_message_text(f"📱 Active Number:\n{number['number']}")

# ================== SUPPORT ==================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("📞 Contact: @your_username")

# ================== BACK ==================
async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data="get")],
        [InlineKeyboardButton("🌍 Available Country", callback_data="country")],
        [InlineKeyboardButton("📞 Active Number", callback_data="active")],
        [InlineKeyboardButton("☎️ Support", callback_data="support")]
    ]

    await query.edit_message_text(
        "🏠 Main Menu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== CSV UPLOAD ==================
async def upload_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    file = await update.message.document.get_file()
    await file.download_to_drive("data.csv")

    added = 0

    with open("data.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            if "number" not in row or "country" not in row:
                continue

            if not numbers_col.find_one({"number": row["number"]}):
                numbers_col.insert_one({
                    "number": row["number"],
                    "country": row["country"],
                    "status": "free"
                })
                added += 1

    await update.message.reply_text(f"✅ Added {added} numbers")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(get_country, pattern="^get$"))
    app.add_handler(CallbackQueryHandler(get_country, pattern="^country$"))
    app.add_handler(CallbackQueryHandler(select_country, pattern="^country_"))
    app.add_handler(CallbackQueryHandler(change_number, pattern="^change_"))
    app.add_handler(CallbackQueryHandler(active_number, pattern="^active$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(copy_number, pattern="^copy_"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_csv))

    print("🤖 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()