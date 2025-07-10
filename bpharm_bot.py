import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ApplicationBuilder,
    ContextTypes,
)

# Initialize Flask app
app = Flask(__name__)

# Bot token from environment
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("No BOT_TOKEN environment variable set")

# PDF folder
PAPER_FOLDER = "bpharm_bot_18"

# Semester -> Subjects
semesters = {
    "1st Semester": [
        "Human Anatomy and Physiology I",
        "Pharmaceutical Analysis I",
        "Pharmaceutics I",
        "Pharmaceutical Inorganic Chemistry",
    ],
    "2nd Semester": [
        "Human Anatomy and Physiology II",
        "Pharmaceutical Organic Chemistry I",
        "Biochemistry",
        "Pathophysiology",
    ],
    "3rd Semester": [
        "Pharmaceutical Organic Chemistry II",
        "Physical Pharmaceutics I",
        "Pharmaceutical Microbiology",
        "Pharmaceutical Engineering",
        "Universal Human Values",
    ],
    "4th Semester": [
        "Pharmaceutical Organic Chemistry III",
        "Medicinal Chemistry I",
        "Physical Pharmaceutics II",
        "Pharmacology I",
        "Pharmacognosy I",
    ],
    "5th Semester": [
        "Medicinal Chemistry II",
        "Industrial Pharmacy I",
        "Pharmacology II",
        "Pharmacognosy and Phytochemistry",
        "Pharmaceutical Jurisprudence Theory",
    ],
    "6th Semester": [
        "Medicinal Chemistry III",
        "Pharmacology III",
        "Herbal Drug Technology Theory",
        "Biopharmaceutics and Pharmacokinetics Theory",
        "Pharmaceutical Biotechnology",
        "Quality Assurance Theory",
    ],
    "7th Semester": [
        "Instrumental Methods of Analysis",
        "Industrial Pharmacy II",
        "Pharmacy Practice",
        "Novel Drug Delivery System",
    ],
    "8th Semester": [
        "Biostatistics and Research Methodology",
        "Social and Preventive Pharmacy",
        "Pharma Marketing Management",
        "Cosmetic Science",
    ],
}

# Create application
application = ApplicationBuilder().token(TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(sem, callback_data=sem)] for sem in semesters]
    keyboard.append([InlineKeyboardButton("📩 Feedback", url="https://codecrafter02.github.io/Feedback02/")])
    await update.message.reply_text(
        "📚 Select Semester:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Semester selection
async def semester_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sem = query.data
    context.user_data["semester"] = sem
    subjects = semesters.get(sem, [])
    keyboard = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in subjects]
    await query.edit_message_text(
        f"📘 {sem} selected.\nSelect Subject:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Subject selection
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
        await query.message.reply_document(
            open(filepath, "rb"), 
            caption=f"📄 {subject}"
        )
    else:
        await query.message.reply_text("❌ File not found.")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(semester_selected, pattern="^(" + "|".join(semesters.keys()) + ")$"))
application.add_handler(CallbackQueryHandler(subject_selected))

# Flask webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

# Health check
@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
