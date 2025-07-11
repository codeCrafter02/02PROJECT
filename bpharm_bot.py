import os
import requests
import json
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://zero2project-wutc.onrender.com" + WEBHOOK_PATH
PAPER_FOLDER = "bpharm_bot_18"

app = Flask(__name__)

# Semester-subject mapping
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

# Store user data in memory
user_data = {}

def send_message(chat_id, text, reply_markup=None):
    """Send message using requests"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Edit message using requests"""
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error editing message: {e}")
        return None

def send_document(chat_id, file_path, caption=None):
    """Send document using requests"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    
    try:
        with open(file_path, "rb") as doc:
            files = {"document": doc}
            response = requests.post(url, data=data, files=files, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error sending document: {e}")
        return None

def answer_callback_query(callback_query_id):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_query_id}
    try:
        response = requests.post(url, json=data, timeout=5)
        return response.json()
    except Exception as e:
        print(f"Error answering callback: {e}")
        return None

def handle_start(chat_id):
    """Handle /start command"""
    keyboard = []
    for sem in semesters:
        keyboard.append([{"text": sem, "callback_data": sem}])
    
    keyboard.append([{"text": "📩 Feedback", "url": "https://codecrafter02.github.io/Feedback02/"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    send_message(chat_id, "📚 Select Semester:", reply_markup)

def handle_semester_selection(chat_id, message_id, user_id, semester):
    """Handle semester selection"""
    user_data[user_id] = {"semester": semester}
    
    subjects = semesters[semester]
    keyboard = []
    for subject in subjects:
        keyboard.append([{"text": subject, "callback_data": subject}])
    
    reply_markup = {"inline_keyboard": keyboard}
    edit_message(chat_id, message_id, f"📘 {semester} Subjects:\nSelect one:", reply_markup)

def handle_subject_selection(chat_id, user_id, subject):
    """Handle subject selection"""
    user_info = user_data.get(user_id, {})
    semester = user_info.get("semester")
    
    if not semester:
        send_message(chat_id, "❗Please select a semester first using /start")
        return
    
    filename = subject.replace(" ", "_").replace("-", "").replace("/", "") + ".pdf"
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, filename)
    
    if os.path.exists(filepath):
        send_document(chat_id, filepath, f"📄 {subject}")
    else:
        send_message(chat_id, "❌ File not found!")

@app.route("/")
def home():
    if not TOKEN:
        return "❌ BOT_TOKEN environment variable not set!"
    return "✅ Bot is Live on Render!"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        if not TOKEN:
            return "Bot not initialized - check BOT_TOKEN", 500
            
        data = request.get_json()
        if not data:
            return "Bad Request", 400
        
        # Handle message
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            
            if "text" in message and message["text"].startswith("/start"):
                handle_start(chat_id)
        
        # Handle callback query
        elif "callback_query" in data:
            callback_query = data["callback_query"]
            callback_query_id = callback_query["id"]
            chat_id = callback_query["message"]["chat"]["id"]
            message_id = callback_query["message"]["message_id"]
            user_id = callback_query["from"]["id"]
            callback_data = callback_query["data"]
            
            # Answer callback query
            answer_callback_query(callback_query_id)
            
            # Handle the callback
            if callback_data in semesters:
                handle_semester_selection(chat_id, message_id, user_id, callback_data)
            else:
                handle_subject_selection(chat_id, user_id, callback_data)
        
        return "ok", 200
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    # Set webhook
    if TOKEN:
        try:
            webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
            response = requests.post(webhook_url, json={"url": WEBHOOK_URL})
            print(f"Webhook setup: {response.json()}")
        except Exception as e:
            print(f"Error setting webhook: {e}")
    
    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
