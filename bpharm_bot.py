import os
import json
import asyncio
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ----------------- CONFIG -----------------
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://zero2project-wutc.onrender.com/webhook"
PAPER_FOLDER = "bpharm_bot_18"
UPI_ID = "9452200292@naviaxis"
ADMIN_IDS = [7287370169]  # Apni Telegram user ID yaha daalo (multiple admins add kar sakte ho)

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
    
    if update.message:
        await update.message.reply_text("📚 Choose Semester:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.edit_message_text("📚 Choose Semester:", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------- ADMIN COMMAND - APPROVE PAYMENT -----------------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You are not authorized to use this command.")
        return
    
    # Command format: /approve user_id semester_name
    # Example: /approve 123456789 1st Semester
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /approve <user_id> <semester_name>\n"
                "Example: /approve 123456789 1st Semester"
            )
            return
        
        target_user_id = args[0]
        semester = " ".join(args[1:])
        
        if semester not in semesters:
            await update.message.reply_text(f"⚠️ Invalid semester: {semester}")
            return
        
        if target_user_id not in user_data:
            user_data[target_user_id] = {"paid_semesters": [], "pending": []}
        
        if semester not in user_data[target_user_id]["paid_semesters"]:
            user_data[target_user_id]["paid_semesters"].append(semester)
        
        # Remove from pending if exists
        if "pending" in user_data[target_user_id] and semester in user_data[target_user_id]["pending"]:
            user_data[target_user_id]["pending"].remove(semester)
        
        save_user_data()
        
        await update.message.reply_text(f"✅ Approved {semester} for user {target_user_id}")
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=int(target_user_id),
                text=f"✅ Your payment for **{semester}** has been verified!\n\nYou can now access all subjects. Use /start to continue.",
                parse_mode="Markdown"
            )
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# ----------------- ADMIN COMMAND - VIEW PENDING PAYMENTS -----------------
async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You are not authorized to use this command.")
        return
    
    pending_list = []
    for uid, data in user_data.items():
        if "pending" in data and data["pending"]:
            for sem in data["pending"]:
                pending_list.append(f"User: {uid}\nSemester: {sem}\n")
    
    if pending_list:
        message = "📋 **Pending Payment Verifications:**\n\n" + "\n".join(pending_list)
        message += "\n\nTo approve: /approve <user_id> <semester_name>"
    else:
        message = "✅ No pending payment verifications."
    
    await update.message.reply_text(message, parse_mode="Markdown")

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
        
        # Payment verification pending - ask for screenshot
        keyboard = [
            [InlineKeyboardButton("📤 Submit Payment Screenshot", callback_data=f"submit_{semester}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]
        await query.edit_message_text(
            "📸 Please send your payment screenshot to verify.\n\n"
            "After sending the screenshot, an admin will verify and unlock access within 24 hours.\n\n"
            f"Or contact admin: @youradminusername",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ----- Submit Payment Request -----
    elif data.startswith("submit_"):
        semester = data.split("_", 1)[1]
        
        # Store pending payment request
        if user_id not in user_data:
            user_data[user_id] = {"paid_semesters": [], "pending": []}
        
        if "pending" not in user_data[user_id]:
            user_data[user_id]["pending"] = []
        
        if semester not in user_data[user_id]["pending"]:
            user_data[user_id]["pending"].append(semester)
            save_user_data()
        
        await query.edit_message_text(
            "✅ Payment request submitted!\n\n"
            "Please send your payment screenshot now. Admin will verify within 24 hours.\n\n"
            "You will receive a notification once verified."
        )

    # ----- Cancel -----
    elif data == "cancel":
        await query.edit_message_text("❌ Payment cancelled.")

    # ----- Back to Semesters -----
    elif data == "back_semesters":
        keyboard = [[InlineKeyboardButton(sem, callback_data=f"sem_{sem}")] for sem in semesters.keys()]
        await query.edit_message_text("📚 Choose Semester:", reply_markup=InlineKeyboardMarkup(keyboard))

    # ----- Subject Selection -----
    elif data.startswith("sub_"):
        subject = data.split("_", 1)[1]
        base = subject.replace(" ", "_")
        semester_folder = None
        current_semester = None
        
        # Find folder and semester
        for sem, subs in semesters.items():
            if subject in subs:
                semester_folder = sem.replace(" ", "_")
                current_semester = sem
                break

        # Check if user has paid for this semester
        if user_id not in user_data or current_semester not in user_data[user_id].get("paid_semesters", []):
            await query.message.reply_text("⚠️ Please purchase this semester first to access subjects!")
            return

        if semester_folder:
            file_path = os.path.join(PAPER_FOLDER, semester_folder, f"{base}.pdf")
            guess_path = os.path.join(PAPER_FOLDER, semester_folder, f"{base}_Guess.pdf")

            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await query.message.reply_document(f, caption=f"📄 {subject}")
            else:
                await query.message.reply_text("⚠️ Previous year file not found!")

            if os.path.exists(guess_path):
                with open(guess_path, "rb") as g:
                    await query.message.reply_document(g, caption=f"📝 Guess Paper {subject}")
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

# ----------------- TELEGRAM APPLICATION -----------------
application = None

async def setup_application():
    global application
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("pending", pending))
    application.add_handler(CallbackQueryHandler(button))
    
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    await application.start()

# ----------------- FLASK ROUTES -----------------
@app.route("/")
def index():
    return "Bot is running with payment system!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        return "ok"
    except Exception as e:
        print(f"Error processing update: {e}")
        return "error", 500

# ----------------- MAIN -----------------
if __name__ == "__main__":
    # Setup bot
    asyncio.run(setup_application())
    
    # Run Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
