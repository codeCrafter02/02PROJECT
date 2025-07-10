import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")  # Set in Render environment variables
PAPER_FOLDER = "bpharm_bot_18"

# Complete B.Pharm Semester-Subject Mapping (PCI Syllabus)
semesters = {
    "1st Semester": [
        "Human Anatomy and Physiology I - Theory",
        "Pharmaceutical Analysis I - Theory",
        "Pharmaceutics I - Theory",
        "Pharmaceutical Inorganic Chemistry - Theory",
        "Communication Skills - Theory",
        "Remedial Biology - Theory",
        "Remedial Mathematics - Theory"
    ],
    "2nd Semester": [
        "Human Anatomy and Physiology II - Theory",
        "Pharmaceutical Organic Chemistry I - Theory",
        "Biochemistry - Theory",
        "Pathophysiology - Theory",
        "Computer Applications in Pharmacy - Theory",
        "Environmental Sciences - Theory"
    ],
    "3rd Semester": [
        "Pharmaceutical Organic Chemistry II - Theory",
        "Physical Pharmaceutics I - Theory",
        "Pharmaceutical Microbiology - Theory",
        "Pharmaceutical Engineering - Theory",
        "Pharmacognosy and Phytochemistry I - Theory",
        "Universal Human Values - Theory"
    ],
    "4th Semester": [
        "Pharmaceutical Organic Chemistry III - Theory",
        "Medicinal Chemistry I - Theory",
        "Physical Pharmaceutics II - Theory",
        "Pharmacology I - Theory",
        "Pharmacognosy and Phytochemistry II - Theory",
        "Pharmaceutical Jurisprudence - Theory"
    ],
    "5th Semester": [
        "Medicinal Chemistry II - Theory",
        "Industrial Pharmacy I - Theory",
        "Pharmacology II - Theory",
        "Pharmacognosy and Phytochemistry III - Theory",
        "Pharmaceutical Biotechnology - Theory"
    ],
    "6th Semester": [
        "Medicinal Chemistry III - Theory",
        "Pharmacology III - Theory",
        "Herbal Drug Technology - Theory",
        "Biopharmaceutics and Pharmacokinetics - Theory",
        "Pharmaceutical Quality Assurance - Theory",
        "Instrumental Methods of Analysis - Theory"
    ],
    "7th Semester": [
        "Instrumental Methods of Analysis - Theory",
        "Industrial Pharmacy II - Theory",
        "Pharmacy Practice - Theory",
        "Novel Drug Delivery System - Theory",
        "Biostatistics and Research Methodology - Theory"
    ],
    "8th Semester": [
        "Biostatistics and Research Methodology - Theory",
        "Social and Preventive Pharmacy - Theory",
        "Pharma Marketing Management - Theory",
        "Quality Control and Standardization of Herbals - Theory",
        "Computer-Aided Drug Design - Theory",
        "Cell and Molecular Biology - Theory"
    ]
}

def create_application():
    """Initialize Telegram Application"""
    application = Application.builder().token(TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(semester_selected, pattern="^(" + "|".join(semesters.keys()) + ")$"))
    application.add_handler(CallbackQueryHandler(subject_selected))
    
    return application

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send semester selection menu"""
    keyboard = [
        [InlineKeyboardButton(sem, callback_data=sem)] 
        for sem in sorted(semesters.keys())  # Sorted semesters
    ]
    keyboard.append([
        InlineKeyboardButton("📩 Feedback", url="https://codecrafter02.github.io/Feedback02/")
    ])
    await update.message.reply_text(
        "📚 B.Pharm Study Material (PCI Syllabus)\nSelect Semester:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def semester_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle semester selection"""
    query = update.callback_query
    await query.answer()
    sem = query.data
    context.user_data["semester"] = sem
    subjects = semesters[sem]
    
    keyboard = [
        [InlineKeyboardButton(subj, callback_data=subj)] 
        for subj in sorted(subjects)  # Sorted subjects
    ]
    await query.edit_message_text(
        f"📘 {sem} Subjects:\nSelect one:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def subject_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send PDF for selected subject"""
    query = update.callback_query
    await query.answer()
    
    subject = query.data
    semester = context.user_data.get("semester")
    
    if not semester:
        await query.message.reply_text("❗Please select a semester first using /start")
        return
    
    # Generate standardized filename
    filename = (subject.replace(" - ", "_")
                      .replace(" ", "_")
                      .replace("/", "_") + ".pdf")
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, filename)
    
    try:
        if os.path.exists(filepath):
            await query.message.reply_document(
                open(filepath, "rb"),
                caption=f"📄 {semester}\n{subject}"
            )
        else:
            await query.message.reply_text(f"❌ Material not available for:\n{subject}")
    except Exception as e:
        await query.message.reply_text(f"⚠️ Error loading file: {str(e)}")

@app.post("/webhook")
async def webhook():
    """Handle Telegram updates"""
    application = create_application()
    data = await request.get_json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "", 200

@app.get("/")
def home():
    return "B.Pharm Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
