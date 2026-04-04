import os
from telegram import *
from telegram.ext import *
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["sms_bot"]
collection = db["numbers"]

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data="get_number"),
         InlineKeyboardButton("🌍 Available Country", callback_data="countries")],
        [InlineKeyboardButton("✅ Active Number", callback_data="active"),
         InlineKeyboardButton("☎️ Support", callback_data="support")]
    ]

    await update.message.reply_text(
        "Welcome! Choose your option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= GET NUMBER =================
async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    countries = collection.distinct("country")

    keyboard = []
    for c in countries:
        count = collection.count_documents({"country": c, "status": "free"})
        keyboard.append([
            InlineKeyboardButton(f"{c} ({count})", callback_data=f"country_{c}")
        ])

    await query.edit_message_text(
        "🌍 Select Country:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= SELECT COUNTRY =================
async def select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    country = query.data.split("_")[1]

    services = collection.distinct("service", {"country": country})

    keyboard = []
    for s in services:
        count = collection.count_documents({
            "country": country,
            "service": s,
            "status": "free"
        })

        keyboard.append([
            InlineKeyboardButton(f"{s} ({count})", callback_data=f"service_{country}_{s}")
        ])

    await query.edit_message_text(
        f"📡 Select Service ({country}):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= SELECT SERVICE =================
async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, country, service = query.data.split("_")

    data = collection.find_one({
        "country": country,
        "service": service,
        "status": "free"
    })

    if not data:
        await query.edit_message_text("❌ No number available")
        return

    collection.update_one({"_id": data["_id"]}, {"$set": {"status": "used"}})

    number = data["number"]

    keyboard = [
        [InlineKeyboardButton("📩 View OTP", url="https://t.me/your_group")],
        [
            InlineKeyboardButton("🔄 Change Number", callback_data=f"service_{country}_{service}"),
            InlineKeyboardButton("🌍 Change Country", callback_data="get_number")
        ]
    ]

    await query.edit_message_text(
        f"🌍 {country} {service} Number Assigned\n\n"
        f"📱 Number: `{number}`\n\n"
        f"⏳ Wait for OTP...",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= OTHER BUTTON =================
async def other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "countries":
        countries = collection.distinct("country")
        text = "\n".join(countries)
        await query.edit_message_text(f"🌍 Available Countries:\n{text}")

    elif query.data == "active":
        await query.edit_message_text("✅ No active number (demo)")

    elif query.data == "support":
        await query.edit_message_text("☎️ Contact: @your_username")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(get_number, pattern="get_number"))
    app.add_handler(CallbackQueryHandler(select_country, pattern="^country_"))
    app.add_handler(CallbackQueryHandler(select_service, pattern="^service_"))
    app.add_handler(CallbackQueryHandler(other))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()