import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
PAPER_FOLDER = "bpharm_bot_18"

semesters = {
    "1st Semester": ["Human Anatomy and Physiology I", "Pharmaceutical Analysis I", "Pharmaceutics I", "Pharmaceutical Inorganic Chemistry"]
}

app = Flask(__name__)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

def start(update, context):
    keyboard = [[InlineKeyboardButton(sem, callback_data=sem)] for sem in semesters]
    keyboard.append([InlineKeyboardButton("📩 Feedback", url="https://codecrafter02.github.io/Feedback02/")])
    update.message.reply_text("📚 Select Semester:", reply_markup=InlineKeyboardMarkup(keyboard))

def semester_selected(update, context):
    query = update.callback_query
    query.answer()
    sem = query.data
    context.user_data["semester"] = sem
    subjects = semesters.get(sem, [])
    keyboard = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in subjects]
    query.edit_message_text(f"📘 {sem} selected.\nSelect Subject:", reply_markup=InlineKeyboardMarkup(keyboard))

def subject_selected(update, context):
    query = update.callback_query
    query.answer()
    subject = query.data
    semester = context.user_data.get("semester")
    if semester is None:
        query.message.reply_text("❗Please select a semester first using /start.")
        return
    subject_file = subject.replace(" ", "_") + ".pdf"
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, subject_file)
    if os.path.exists(filepath):
        query.message.reply_document(open(filepath, "rb"), caption=f"📄 {subject}")
    else:
        query.message.reply_text("❌ File not found.")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(semester_selected, pattern="^(1st Semester)$"))
dispatcher.add_handler(CallbackQueryHandler(subject_selected))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"
