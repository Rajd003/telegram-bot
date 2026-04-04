from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import csv
import random

BOT_TOKEN = "YOUR_BOT_TOKEN"

# ===== MENU KEYBOARD (ONLY USED IN /start) =====
def menu_keyboard():
    keyboard = [
        ["📱 Get Number", "🌍 Available Country"],
        ["✅ Active Number", "☎️ Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== LOAD CSV DATA =====
def load_numbers():
    data = {}
    try:
        with open("numbers.csv", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                country = row["country"]
                service = row["service"]
                number = row["number"]

                if country not in data:
                    data[country] = {}

                if service not in data[country]:
                    data[country][service] = []

                data[country][service].append(number)
    except:
        pass

    return data

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Choose your option:",
        reply_markup=menu_keyboard()
    )

# ===== BUTTON HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = load_numbers()

    # 👉 GET NUMBER
    if text == "📱 Get Number":
        countries = list(data.keys())

        if not countries:
            await update.message.reply_text("❌ No country available")
            return

        buttons = []
        for c in countries:
            buttons.append([InlineKeyboardButton(c, callback_data=f"country_{c}")])

        await update.message.reply_text(
            "🌍 Select Country:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # 👉 AVAILABLE COUNTRY
    elif text == "🌍 Available Country":
        countries = list(data.keys())
        if countries:
            msg = "\n".join(countries)
        else:
            msg = "No country available"

        await update.message.reply_text(f"🌍 Available Countries:\n{msg}")

    # 👉 ACTIVE NUMBER
    elif text == "✅ Active Number":
        await update.message.reply_text("🚧 Feature coming soon")

    # 👉 SUPPORT
    elif text == "☎️ Support":
        await update.message.reply_text("📞 Contact: @yourusername")


# ===== CALLBACK HANDLER =====
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_numbers()

    # 👉 COUNTRY SELECT
    if query.data.startswith("country_"):
        country = query.data.split("_")[1]

        services = data.get(country, {})

        buttons = []
        for s in services:
            buttons.append([InlineKeyboardButton(s, callback_data=f"service_{country}_{s}")])

        await query.message.reply_text(
            f"📡 Select Service for {country}:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # 👉 SERVICE SELECT
    elif query.data.startswith("service_"):
        parts = query.data.split("_")
        country = parts[1]
        service = parts[2]

        numbers = data[country][service]

        if not numbers:
            await query.message.reply_text("❌ No number available")
            return

        number = random.choice(numbers)

        buttons = [
            [InlineKeyboardButton("📩 View OTP", url="https://t.me/yourgroup")],
            [
                InlineKeyboardButton("🔄 Change Number", callback_data=f"service_{country}_{service}"),
                InlineKeyboardButton("🌍 Change Country", callback_data="back_country")
            ]
        ]

        await query.message.reply_text(
            f"📲 {country} {service} Number:\n\n`+{number}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # 👉 BACK TO COUNTRY
    elif query.data == "back_country":
        countries = list(data.keys())

        buttons = []
        for c in countries:
            buttons.append([InlineKeyboardButton(c, callback_data=f"country_{c}")])

        await query.message.reply_text(
            "🌍 Select Country:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# ===== RUN BOT =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.ALL, lambda u, c: None))  # prevent duplicate

app.add_handler(
    MessageHandler(filters.UpdateType.CALLBACK_QUERY, button_click)
)

print("Bot running...")
app.run_polling()