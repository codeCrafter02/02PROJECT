import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
WEBHOOK_URL = f"https://zero2project-wutc.onrender.com/{TOKEN}"
PAPER_FOLDER = "bpharm_bot_18"

# Semester-Subject Mapping
semesters = {
    "1st Semester": [
        "Human Anatomy and Physiology I", "Pharmaceutical Analysis I", "Pharmaceutics I", "Pharmaceutical Inorganic Chemistry"
    ],
    "2nd Semester": [
        "Human Anatomy and Physiology II", "Pharmaceutical Organic Chemistry I", "Biochemistry", "Pathophysiology"
    ],
    "3rd Semester": [
        "Pharmaceutical Organic Chemistry II", "Physical Pharmaceutics I", "Pharmaceutical Microbiology", "Pharmaceutical Engineering", "Universal Human Values"
    ],
    "4th Semester": [
        "Pharmaceutical Organic Chemistry III", "Medicinal Chemistry I", "Physical Pharmaceutics II", "Pharmacology I", "Pharmacognosy I"
    ],
    "5th Semester": [
        "Medicinal Chemistry II", "Industrial Pharmacy I", "Pharmacology II", "Pharmacognosy and Phytochemistry", "Pharmaceutical Jurisprudence Theory"
    ],
    "6th Semester": [
        "Medicinal Chemistry III", "Pharmacology III", "Herbal Drug Technology Theory", "Biopharmaceutics and Pharmacokinetics Theory", "Pharmaceutical Biotechnology", "Quality Assurance Theory"
    ],
    "7th Semester": [
        "Instrumental Methods of Analysis", "Industrial Pharmacy II", "Pharmacy Practice", "Novel Drug Delivery System"
    ],
    "8th Semester": [
        "Biostatistics and Research Methodology", "Social and Preventive Pharmacy", "Pharma Marketing Management", "Cosmetic Science"
    ],
}

# Flask App
app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(sem, callback_data=sem)] for sem in semesters]
    keyboard.append([InlineKeyboardButton("📩 Feedback", url="https://codecrafter02.github.io/Feedback02/")])
    await update.message.reply_text("📚 Select Semester:", reply_markup=InlineKeyboardMarkup(keyboard))


async def semester_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sem = query.data
    context.user_data["semester"] = sem
    subjects = semesters.get(sem, [])
    keyboard = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in subjects]
    await query.edit_message_text(f"📘 {sem} selected.\nSelect Subject:", reply_markup=InlineKeyboardMarkup(keyboard))


async def subject_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data
    semester = context.user_data.get("semester")

    if semester is None:
        await query.message.reply_text("❗Please select a semester first using /start.")
        return

    subject_file = subject.replace(" ", "_") + ".pdf"
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, subject_file)

    if os.path.exists(filepath):
        await query.message.reply_document(open(filepath, "rb"), caption=f"📄 {subject}")
    else:
        await query.message.reply_text("❌ File not found.")


# Add handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(semester_selected, pattern="^(" + "|".join(semesters.keys()) + ")$"))
telegram_app.add_handler(CallbackQueryHandler(subject_selected))


# --- Webhook Endpoint ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"


# Health Check Route
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"


# --- Webhook Setup ---
@app.before_first_request
def set_webhook():
    bot.set_webhook(url=WEBHOOK_URL)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
