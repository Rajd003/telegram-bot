import asyncio
import csv
import os
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from pymongo import MongoClient

# 🔐 ENV VARIABLES
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MONGO_URI = os.getenv("MONGO_URI")

# 🔥 MongoDB
client = MongoClient(MONGO_URI)
db = client["sms_bot"]
collection = db["numbers"]

# 🔹 Start
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data='get_number')],
        [InlineKeyboardButton("💰 Balance", callback_data='balance')]
    ]

    await update.message.reply_text(
        "✨ Welcome 👋\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🔹 Button Click
async def button_click(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'get_number':

        numbers = list(collection.find({"status": "free"}))

        if not numbers:
            await query.edit_message_text("❌ No number available")
            return

        number_data = random.choice(numbers)

        # mark used
        collection.update_one(
            {"_id": number_data["_id"]},
            {"$set": {"status": "used"}}
        )

        try:
            await query.edit_message_text(
                f"✅ Service: {number_data['service']}\n"
                f"🌍 Country: {number_data['country']}\n"
                f"📱 Number: {number_data['number']}"
            )
        except:
            await query.message.reply_text("❌ Error showing number")

    elif query.data == 'balance':
        try:
            await query.edit_message_text("💰 Balance: ₹0")
        except:
            await query.message.reply_text("💰 Balance: ₹0")

# 🔹 Admin add single number
async def add_number(update, context):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        service = context.args[0]
        country = context.args[1]
        number = context.args[2]

        if collection.find_one({"number": number}):
            await update.message.reply_text("⚠️ Number already exists")
            return

        collection.insert_one({
            "number": number,
            "service": service,
            "country": country,
            "status": "free"
        })

        await update.message.reply_text("✅ Number added")

    except:
        await update.message.reply_text("❌ Use: /add service country number")

# 🔹 CSV Upload
async def upload_csv(update, context):
    if update.message.from_user.id != ADMIN_ID:
        return

    document = update.message.document

    if not document or not document.file_name.endswith(".csv"):
        await update.message.reply_text("❌ Please upload CSV file")
        return

    file = await document.get_file()
    path = "numbers.csv"
    await file.download_to_drive(path)

    added = 0
    skipped = 0

    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            number = row.get("number")
            service = row.get("service")
            country = row.get("country")

            if not number:
                continue

            if collection.find_one({"number": number}):
                skipped += 1
                continue

            collection.insert_one({
                "number": number,
                "service": service,
                "country": country,
                "status": "free"
            })
            added += 1

    await update.message.reply_text(
        f"✅ Added: {added}\n⚠️ Skipped: {skipped}"
    )

# 🔹 Main
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_number))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_csv))
    app.add_handler(CallbackQueryHandler(button_click))

    app.run_polling()


if __name__ == "__main__":
    main()
