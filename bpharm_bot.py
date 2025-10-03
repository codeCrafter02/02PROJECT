import os
import json
import requests
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ----------------- CONFIG -----------------
TOKEN = os.getenv("BOT_TOKEN")  # Render me set karo
WEBHOOK_URL = "https://zero2project-wutc.onrender.com/webhook"  # apna Render URL
PAPER_FOLDER = "bpharm_bot_18"
UPI_ID = "9452200292@naviaxis"  # apna UPI ID yaha daalna

app = Flask(__name__)

# ----------------- USER DATA -----------------
USER_DATA_FILE = "user_data.json"

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f)

user_data = load_user_data()

# ----------------- SEMESTERS & SUBJECTS -----------------
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

# ----------------- START COMMAND -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(sem, callback_data=f"sem_{sem}")] for sem in semesters.keys()]
    await update.message.reply_text("📚 Choose Semester:", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------- CALLBACK HANDLER -----------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    # ----- Semester Selection -----
    if data.startswith("sem_"):
        semester = data.split("_", 1)[1]

        # Check payment
        if user_id in user_data and semester in user_data[user_id].get("paid_semesters", []):
            await show_subjects(query, semester)
        else:
            keyboard = [
                [InlineKeyboardButton("✅ I have Paid", callback_data=f"paid_{semester}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]
            await query.edit_message_text(
                f"💰 To unlock **{semester}**, please pay ₹10 to this UPI ID:\n\n`{UPI_ID}`\n\n"
                "After payment, click ✅ *I have Paid*.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    # ----- Payment Confirmation -----
    elif data.startswith("paid_"):
        semester = data.split("_", 1)[1]

        if user_id not in user_data:
            user_data[user_id] = {"paid_semesters": []}

        if semester not in user_data[user_id]["paid_semesters"]:
            user_data[user_id]["paid_semesters"].append(semester)
            save_user_data()

        await query.edit_message_text("✅ Payment verified! Access unlocked.")
        await show_subjects(query, semester)

    # ----- Cancel -----
    elif data == "cancel":
        await query.edit_message_text("❌ Payment cancelled.")

    # ----- Subject Selection -----
    elif data.startswith("sub_"):
        subject = data.split("_", 1)[1]
        base = subject.replace(" ", "_")
        semester_folder = None
        # Find folder
        for sem, subs in semesters.items():
            if subject in subs:
                semester_folder = sem.replace(" ", "_")
                break

        if semester_folder:
            file_path = os.path.join(PAPER_FOLDER, semester_folder, f"{base}.pdf")
            guess_path = os.path.join(PAPER_FOLDER, semester_folder, f"{base}_Guess.pdf")

            if os.path.exists(file_path):
                await query.message.reply_document(open(file_path, "rb"), caption=f"📄 {subject}")
            else:
                await query.message.reply_text("⚠️ Previous year file not found!")

            if os.path.exists(guess_path):
                await query.message.reply_document(open(guess_path, "rb"), caption=f"📝 Guess Paper {subject}")
            else:
                await query.message.reply_text("⚠️ Guess paper not found!")

        else:
            await query.message.reply_text("⚠️ Subject folder not found!")

# ----------------- SHOW SUBJECTS FUNCTION -----------------
async def show_subjects(query, semester):
    subs = semesters.get(semester)
    if not subs:
        await query.edit_message_text("⚠️ No subjects found.")
        return

    keyboard = [[InlineKeyboardButton(sub, callback_data=f"sub_{sub}")] for sub in subs]
    keyboard.append([InlineKeyboardButton("🔙 Back to Semesters", callback_data="back_semesters")])
    await query.edit_message_text(f"📖 Subjects in {semester}:", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------- BACK TO SEMESTERS -----------------
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(query, context)

# ----------------- FLASK ROUTES -----------------
@app.route("/")
def index():
    return "Bot is running with payment system!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), context.bot)
    context.application.process_update(update)
    return "ok"

# ----------------- MAIN -----------------
if __name__ == "__main__":
    app_telegram = ApplicationBuilder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CallbackQueryHandler(button, pattern=".*"))

    context = type("obj", (object,), {"bot": app_telegram.bot, "application": app_telegram})()

    # Set webhook
    requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", {"url": WEBHOOK_URL})

    # Run Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
