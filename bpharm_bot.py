import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
PAPER_FOLDER = "bpharm_bot_18"

# Semester and subject mapping
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
    # ... [keep all other semesters as you have them]
}

# Flask app
app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

@app.route("/", methods=["GET"])
def health():
    return "✅ B.Pharm Bot is Live!"

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    if request.is_json:
        update = Update.de_json(await request.get_json(), telegram_app.bot)
        await telegram_app.process_update(update)
    return "OK"

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(sem, callback_data=sem)] for sem in semesters]
    keyboard.append([InlineKeyboardButton("📩 Feedback", url="https://codecrafter02.github.io/Feedback02/")])
    await update.message.reply_text(
        "📚 B.Pharm Study Material\nSelect Semester:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def semester_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):  # Fixed typo in function name
    query = update.callback_query
    await query.answer()
    sem = query.data
    context.user_data["semester"] = sem
    subjects = semesters[sem]
    keyboard = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in subjects]
    await query.edit_message_text(
        f"📘 {sem} Subjects:\nSelect one:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def subject_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data
    semester = context.user_data.get("semester")
    
    if not semester:
        await query.message.reply_text("❗Please select a semester first using /start")
        return
    
    # Improved filename handling
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
        await query.message.reply_text(f"⚠️ Error: {str(e)}")

# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(semester_selected, pattern="^(" + "|".join(semesters.keys()) + ")$"))  # Fixed function name
telegram_app.add_handler(CallbackQueryHandler(subject_selected))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
