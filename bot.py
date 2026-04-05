from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import csv
import random

BOT_TOKEN = "8660826415:AAHsDMwGFatbX-x1kYxO_5mm-oKr2HKiRpk"

# ===== MENU =====
def menu_keyboard():
    keyboard = [
        ["📱 Get Number", "🌍 Available Country"],
        ["✅ Active Number", "☎️ Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== LOAD CSV =====
def load_numbers():
    data = {}
    try:
        with open("numbers.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                country = row["country"]
                service = row["service"]
                number = row["number"]

                data.setdefault(country, {}).setdefault(service, []).append(number)
    except Exception as e:
        print("CSV Error:", e)

    return data

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Choose your option:",
        reply_markup=menu_keyboard()
    )

# ===== MAIN BUTTON HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = load_numbers()

    # GET NUMBER
    if text == "📱 Get Number":
        countries = list(data.keys())

        if not countries:
            await update.message.reply_text("❌ No country available")
            return

        buttons = [[InlineKeyboardButton(c, callback_data=f"country|{c}")] for c in countries]

        await update.message.reply_text(
            "🌍 Select Country:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # AVAILABLE COUNTRY
    elif text == "🌍 Available Country":
        countries = list(data.keys())
        msg = "\n".join(countries) if countries else "No country available"

        await update.message.reply_text(f"🌍 Available Countries:\n{msg}")

    # ACTIVE NUMBER
    elif text == "✅ Active Number":
        await update.message.reply_text("🚧 Coming soon")

    # SUPPORT
    elif text == "☎️ Support":
        await update.message.reply_text("📞 Contact: @yourusername")

# ===== CALLBACK HANDLER =====
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_numbers()

    # COUNTRY SELECT
    if query.data.startswith("country|"):
        country = query.data.split("|")[1]

        services = data.get(country, {})

        if not services:
            await query.message.reply_text("❌ No service available")
            return

        buttons = [
            [InlineKeyboardButton(s, callback_data=f"service|{country}|{s}")]
            for s in services
        ]

        await query.message.reply_text(
            f"📡 Select Service ({country}):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # SERVICE SELECT
    elif query.data.startswith("service|"):
        _, country, service = query.data.split("|")

        numbers = data.get(country, {}).get(service, [])

        if not numbers:
            await query.message.reply_text("❌ No number available")
            return

        number = random.choice(numbers)

        buttons = [
            [InlineKeyboardButton("📩 View OTP", url="https://t.me/yourgroup")],
            [
                InlineKeyboardButton("🔄 Change Number", callback_data=f"service|{country}|{service}"),
                InlineKeyboardButton("🌍 Change Country", callback_data="back")
            ]
        ]

        await query.message.reply_text(
            f"📲 {country} {service} Number:\n\n`+{number}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # BACK BUTTON
    elif query.data == "back":
        countries = list(data.keys())

        buttons = [[InlineKeyboardButton(c, callback_data=f"country|{c}")] for c in countries]

        await query.message.reply_text(
            "🌍 Select Country:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# ===== RUN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_click))

print("Bot running...")
app.run_polling(drop_pending_updates=True)