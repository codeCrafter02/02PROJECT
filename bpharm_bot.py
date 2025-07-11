import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, ContextTypes
)
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://zero2project-wutc.onrender.com" + WEBHOOK_PATH
PAPER_FOLDER = "bpharm_bot_18"

app = Flask(__name__)

# Initialize bot
bot = Bot(token=TOKEN)

# Semester-subject mapping
semesters = {
    "1st Semester": [
        "Human Anatomy and Physiology I - Theory",
        "Pharmaceutical Analysis I - Theory",
        "Pharmaceutics I - Theory",
        "Pharmaceutical Inorganic Chemistry - Theory",
        "Communication Skills - Theory",
        "Remedial Biology/Mathematics - Theory"
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
        "Pharmacognosy and Phytochemistry I - Theory"
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

# Store user data in memory (since we can't use Application context)
user_data = {}

# Handlers
async def start(update: Update, context=None):
    keyboard = [
        [InlineKeyboardButton(sem, callback_data=sem)] for sem in semesters
    ]
    keyboard.append([InlineKeyboardButton("📩 Feedback", url="https://codecrafter02.github.io/Feedback02/")])
    await update.message.reply_text("📚 Select Semester:", reply_markup=InlineKeyboardMarkup(keyboard))

async def semester_selected(update: Update, context=None):
    query = update.callback_query
    await query.answer()
    sem = query.data
    
    # Store user data
    user_id = query.from_user.id
    user_data[user_id] = {"semester": sem}
    
    subjects = semesters[sem]
    keyboard = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in subjects]
    await query.edit_message_text(f"📘 {sem} Subjects:\nSelect one:", reply_markup=InlineKeyboardMarkup(keyboard))

async def subject_selected(update: Update, context=None):
    query = update.callback_query
    await query.answer()
    subject = query.data
    user_id = query.from_user.id
    
    # Get user's semester
    user_info = user_data.get(user_id, {})
    semester = user_info.get("semester")
    
    if not semester:
        await query.message.reply_text("❗Please select a semester first using /start")
        return

    filename = subject.replace(" ", "_").replace("-", "").replace("/", "") + ".pdf"
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, filename)

    if os.path.exists(filepath):
        with open(filepath, "rb") as doc:
            await query.message.reply_document(doc, caption=f"📄 {subject}")
    else:
        await query.message.reply_text("❌ File not found!")

async def handle_update(update: Update):
    """Handle different types of updates"""
    try:
        if update.message and update.message.text and update.message.text.startswith('/start'):
            await start(update)
        elif update.callback_query:
            query_data = update.callback_query.data
            if query_data in semesters:
                await semester_selected(update)
            else:
                await subject_selected(update)
    except Exception as e:
        logger.error(f"Error handling update: {e}")

@app.route("/")
def home():
    return "Bot is Live on Render!"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        json_data = request.get_json()
        if not json_data:
            return "Bad Request", 400
            
        update = Update.de_json(json_data, bot)
        
        # Create a new event loop for this request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(handle_update(update))
        finally:
            loop.close()
        
        return "ok", 200
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

async def set_webhook():
    """Set up webhook for the bot"""
    try:
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

if __name__ == "__main__":
    # Setup webhook
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(set_webhook())
    finally:
        loop.close()
    
    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
