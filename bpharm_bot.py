import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot Token (from environment or hardcoded for testing)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8123918229:AAHNBboV8HhgMoOj-wOhZCw94bK3Z2ZoM-0")
WEBHOOK_URL = f"https://zero2project-wutc.onrender.com/{BOT_TOKEN}"

# PDF Folder Path
PAPER_FOLDER = "bpharm_bot_18"

# Semester -> Subjects
semesters = {
    "1st Semester": ["Human Anatomy and Physiology I", "Pharmaceutical Analysis I", "Pharmaceutics I", "Pharmaceutical Inorganic Chemistry"],
    "2nd Semester": ["Human Anatomy and Physiology II", "Pharmaceutical Organic Chemistry I", "Biochemistry", "Pathophysiology"],
    "3rd Semester": ["Pharmaceutical Organic Chemistry II", "Physical Pharmaceutics I", "Pharmaceutical Microbiology", "Pharmaceutical Engineering", "Universal Human Values"],
    "4th Semester": ["Pharmaceutical Organic Chemistry III", "Medicinal Chemistry I", "Physical Pharmaceutics II", "Pharmacology I", "Pharmacognosy I"],
    "5th Semester": ["Medicinal Chemistry II", "Industrial Pharmacy I", "Pharmacology II", "Pharmacognosy and Phytochemistry", "Pharmaceutical Jurisprudence Theory"],
    "6th Semester": ["Medicinal Chemistry III", "Pharmacology III", "Herbal Drug Technology Theory", "Biopharmaceutics and Pharmacokinetics Theory", "Pharmaceutical Biotechnology", "Quality Assurance Theory"],
    "7th Semester": ["Instrumental Methods of Analysis", "Industrial Pharmacy II", "Pharmacy Practice", "Novel Drug Delivery System"],
    "8th Semester": ["Biostatistics and Research Methodology", "Social and Preventive Pharmacy", "Pharma Marketing Management", "Cosmetic Science"]
}

# Flask App
app = Flask(__name__)

# Telegram Application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(sem, callback_data=sem)] for sem in semesters]
    keyboard.append([InlineKeyboardButton("\ud83d\udce9 Feedback", url="https://codecrafter02.github.io/Feedback02/")])
    await update.message.reply_text("\ud83d\udcda Select Semester:", reply_markup=InlineKeyboardMarkup(keyboard))

# Semester selected
async def semester_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sem = query.data
    context.user_data["semester"] = sem
    subjects = semesters.get(sem, [])
    keyboard = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in subjects]
    await query.edit_message_text(f"\ud83d\udcd8 {sem} selected.\nSelect Subject:", reply_markup=InlineKeyboardMarkup(keyboard))

# Subject selected
async def subject_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data
    semester = context.user_data.get("semester")

    if not semester:
        await query.message.reply_text("\u2757Please select a semester first using /start.")
        return

    subject_file = subject.replace(" ", "_") + ".pdf"
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, subject_file)

    if os.path.exists(filepath):
        with open(filepath, "rb") as file:
            await query.message.reply_document(document=file, caption=f"\ud83d\udcc4 {subject}")
    else:
        await query.message.reply_text("\u274c File not found.")

# Add handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(semester_selected, pattern="^(" + "|".join(semesters.keys()) + ")$"))
telegram_app.add_handler(CallbackQueryHandler(subject_selected))

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"

# Health check route
@app.route("/")
def home():
    return "Bot is running!"

# Set webhook when starting app (only once)
if __name__ == '__main__':
    import requests
    set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    requests.post(set_url, data={"url": WEBHOOK_URL})
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
