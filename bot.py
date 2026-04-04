import asyncio
import csv
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from pymongo import MongoClient

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# ================== MongoDB (SAFE CONNECT) ==================
try:
    client = MongoClient(MONGO_URI)
    db = client["sms_bot"]
    collection = db["numbers"]
    print("✅ Mongo Connected")
except Exception as e:
    print("❌ Mongo Error:", e)

# ================== Fake Server (Render fix) ==================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web).start()

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data='get_number')],
        [InlineKeyboardButton("💰 Balance", callback_data='balance')]
    ]

    await update.message.reply_text(
        "👋 Welcome to Number Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== BUTTON ==================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'get_number':
        try:
            number_data = collection.find_one({"status": "free"})

            if not number_data:
                await query.edit_message_text("❌ No number available")
                return

            collection.update_one(
                {"_id": number_data["_id"]},
                {"$set": {"status": "used"}}
            )

            await query.edit_message_text(
                f"✅ Service: {number_data['service']}\n"
                f"🌍 Country: {number_data['country']}\n"
                f"📱 Number: {number_data['number']}"
            )

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")

    elif query.data == 'balance':
        await query.edit_message_text("💰 Balance: 0")

# ================== ADD NUMBER ==================
async def add_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        service = context.args[0]
        country = context.args[1]
        number = context.args[2]

        if collection.find_one({"number": number}):
            await update.message.reply_text("⚠️ Already exists")
            return

        collection.insert_one({
            "number": number,
            "service": service,
            "country": country,
            "status": "free"
        })

        await update.message.reply_text("✅ Number Added")

    except:
        await update.message.reply_text("❌ Use: /add service country number")

# ================== CSV UPLOAD ==================
async def upload_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    document = update.message.document

    if not document or not document.file_name.endswith(".csv"):
        await update.message.reply_text("❌ Send CSV file")
        return

    file = await document.get_file()
    path = "numbers.csv"
    await file.download_to_drive(path)

    added = 0
    skipped = 0

    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            number = row["number"]

            if collection.find_one({"number": number}):
                skipped += 1
                continue

            collection.insert_one({
                "number": number,
                "service": row["service"],
                "country": row["country"],
                "status": "free"
            })
            added += 1

    await update.message.reply_text(
        f"✅ Added: {added}\n⚠️ Skipped: {skipped}"
    )

# ================== MAIN ==================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_number))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_csv))
    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 Bot Running Successfully...")
    await app.run_polling()

# ================== RUN ==================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        pass
