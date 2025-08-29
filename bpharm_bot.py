import os
import requests
import json
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://zero2project-wutc.onrender.com" + WEBHOOK_PATH
PAPER_FOLDER = "bpharm_bot_18"

app = Flask(__name__)

# Semester-subject mapping (same as before)
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

# Store user data in memory with message IDs
user_data = {}

# -------------------------
# Utilities
# -------------------------
def make_base_filename(subject: str) -> str:
    return subject.replace(" ", "_").replace("-", "").replace("/", "")

def send_message(chat_id, text, reply_markup=None):
    """Send message using requests"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Edit message using requests with better error handling"""
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        # Check for specific Telegram errors
        if not response_data.get('ok'):
            error_code = response_data.get('error_code')
            error_description = response_data.get('description', '')
            
            # If message is not modified (same content), it's still OK for our purposes
            if error_code == 400 and "message is not modified" in error_description:
                return {"ok": True}
            
            print(f"Edit message failed: {response_data}")
            return None
        
        return response_data
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
            response = requests.post(url, data=data, files=files, timeout=60)
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

# -------------------------
# Handlers
# -------------------------
def handle_start(chat_id):
    """Handle /start command -> show semester list"""
    keyboard = [[{"text": sem, "callback_data": sem}] for sem in semesters.keys()]
    keyboard.append([{"text": "📩 Feedback", "url": "https://codecrafter02.github.io/Feedback02/"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    result = send_message(chat_id, "📚 Select Semester:", reply_markup)
    return result

def handle_semester_selection(chat_id, message_id, user_id, semester):
    """Handle semester selection -> save and show subjects"""
    # Store both semester and current navigation message ID
    user_data[user_id] = {
        "semester": semester, 
        "nav_message_id": message_id
    }
    
    subjects = semesters[semester]
    keyboard = [[{"text": subject, "callback_data": subject}] for subject in subjects]
    keyboard.append([{"text": "🔙 Back to Semester", "callback_data": "BACK_SEMESTERS"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    # Try to edit the message, if it fails, send a new one
    result = edit_message(chat_id, message_id, f"📘 {semester} Subjects:\nSelect one:", reply_markup)
    
    if not result or not result.get('ok'):
        # If edit fails, send new message and update the message ID
        new_result = send_message(chat_id, f"📘 {semester} Subjects:\nSelect one:", reply_markup)
        if new_result and new_result.get('ok'):
            user_data[user_id]["nav_message_id"] = new_result['result']['message_id']

def handle_subject_selection(chat_id, message_id, user_id, subject):
    """After subject selection, send files and create NEW navigation message"""
    user_info = user_data.get(user_id, {})
    semester = user_info.get("semester")
    if not semester:
        send_message(chat_id, "❗Please select a semester first using /start")
        return

    # Save chosen subject
    user_data.setdefault(user_id, {})["subject"] = subject

    # Edit current message to show selection
    edit_message(chat_id, message_id, f"✅ Selected: {subject}", None)

    # Send loading message
    loading_msg = send_message(chat_id, f"📂 Loading files for: {subject}...")

    base = make_base_filename(subject)
    folder = semester.replace(" ", "_")
    prev_path = os.path.join(PAPER_FOLDER, folder, f"{base}.pdf")
    guess_path = os.path.join(PAPER_FOLDER, folder, f"{base}_Guess.pdf")

    # Send files
    files_sent = 0
    if os.path.exists(prev_path):
        send_document(chat_id, prev_path, f"📄 Previous Year • {subject}")
        files_sent += 1
    else:
        send_message(chat_id, "❌ Previous year file not found!")

    if os.path.exists(guess_path):
        send_document(chat_id, guess_path, f"📝 Guess Paper • {subject}")
        files_sent += 1
    else:
        send_message(chat_id, "❌ Guess paper not found!")

    # Create NEW navigation message (not editing the old one)
    keyboard = [
        [{"text": "⬅️ Back to Subjects", "callback_data": "BACK_SUBJECTS"}],
        [{"text": "🔙 Back to Semester", "callback_data": "BACK_SEMESTERS"}],
    ]
    
    nav_text = f"📂 Files sent for: {subject}\n\nChoose next action:"
    nav_result = send_message(chat_id, nav_text, {"inline_keyboard": keyboard})
    
    # Update navigation message ID
    if nav_result and nav_result.get('ok'):
        user_data[user_id]["nav_message_id"] = nav_result['result']['message_id']

    # Delete loading message if it was sent successfully
    if loading_msg and loading_msg.get('ok'):
        try:
            delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
            requests.post(delete_url, json={
                "chat_id": chat_id, 
                "message_id": loading_msg['result']['message_id']
            }, timeout=5)
        except:
            pass

def handle_back_to_subjects(chat_id, message_id, user_id):
    """Show subject list again for the saved semester"""
    info = user_data.get(user_id, {})
    semester = info.get("semester")
    if not semester:
        send_message(chat_id, "❗Please select a semester first using /start")
        return

    subjects = semesters[semester]
    keyboard = [[{"text": subj, "callback_data": subj}] for subj in subjects]
    keyboard.append([{"text": "🔙 Back to Semester", "callback_data": "BACK_SEMESTERS"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    # Use the stored navigation message ID
    nav_message_id = info.get("nav_message_id", message_id)
    
    result = edit_message(chat_id, nav_message_id, f"📘 {semester} Subjects:\nSelect one:", reply_markup)
    
    if not result or not result.get('ok'):
        # If edit fails, send new message
        new_result = send_message(chat_id, f"📘 {semester} Subjects:\nSelect one:", reply_markup)
        if new_result and new_result.get('ok'):
            user_data[user_id]["nav_message_id"] = new_result['result']['message_id']

def handle_back_to_semesters(chat_id, message_id, user_id):
    """Show semester list again"""
    keyboard = [[{"text": sem, "callback_data": sem}] for sem in semesters.keys()]
    keyboard.append([{"text": "📩 Feedback", "url": "https://codecrafter02.github.io/Feedback02/"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    # Use the stored navigation message ID if available
    info = user_data.get(user_id, {})
    nav_message_id = info.get("nav_message_id", message_id)
    
    result = edit_message(chat_id, nav_message_id, "📚 Select Semester:", reply_markup)
    
    if not result or not result.get('ok'):
        # If edit fails, send new message
        new_result = send_message(chat_id, "📚 Select Semester:", reply_markup)
        if new_result and new_result.get('ok') and user_id in user_data:
            user_data[user_id]["nav_message_id"] = new_result['result']['message_id']

# Rest of the utility functions remain the same...
def send_previous_year(chat_id, user_id):
    info = user_data.get(user_id, {})
    semester = info.get("semester")
    subject = info.get("subject")
    if not semester or not subject:
        send_message(chat_id, "❗Please select a semester and subject first using /start")
        return
    base = make_base_filename(subject)
    folder = semester.replace(" ", "_")
    filepath = os.path.join(PAPER_FOLDER, folder, f"{base}.pdf")
    if os.path.exists(filepath):
        send_document(chat_id, filepath, f"📄 Previous Year • {subject}")
    else:
        send_message(chat_id, "❌ Previous year file not found!")

def send_guess_paper(chat_id, user_id):
    info = user_data.get(user_id, {})
    semester = info.get("semester")
    subject = info.get("subject")
    if not semester or not subject:
        send_message(chat_id, "❗Please select a semester and subject first using /start")
        return
    base = make_base_filename(subject)
    folder = semester.replace(" ", "_")
    guess_path = os.path.join(PAPER_FOLDER, folder, f"{base}_Guess.pdf")
    if os.path.exists(guess_path):
        send_document(chat_id, guess_path, f"📝 Guess Paper • {subject}")
    else:
        send_message(chat_id, "❌ Guess paper not found!")

# -------------------------
# Flask routes
# -------------------------
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

            if "text" in message and str(message["text"]).startswith("/start"):
                handle_start(chat_id)

        # Handle callback query
        elif "callback_query" in data:
            callback_query = data["callback_query"]
            callback_query_id = callback_query["id"]
            chat_id = callback_query["message"]["chat"]["id"]
            message_id = callback_query["message"]["message_id"]
            user_id = callback_query["from"]["id"]
            callback_data = callback_query["data"]

            # Answer callback to remove 'loading' on Telegram UI
            answer_callback_query(callback_query_id)

            # Routing
            if callback_data in semesters:
                handle_semester_selection(chat_id, message_id, user_id, callback_data)

            elif callback_data == "BACK_SUBJECTS":
                handle_back_to_subjects(chat_id, message_id, user_id)

            elif callback_data == "BACK_SEMESTERS":
                handle_back_to_semesters(chat_id, message_id, user_id)

            elif callback_data.startswith("PY::"):
                send_previous_year(chat_id, user_id)

            elif callback_data.startswith("GP::"):
                send_guess_paper(chat_id, user_id)

            else:
                # Check if it's a valid subject
                all_subjects = []
                for sem_subjects in semesters.values():
                    all_subjects.extend(sem_subjects)
                
                if callback_data in all_subjects:
                    handle_subject_selection(chat_id, message_id, user_id, callback_data)
                else:
                    send_message(chat_id, "❗Unknown command. Please use /start to begin.")

        return "ok", 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    if TOKEN:
        try:
            webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
            response = requests.post(webhook_url, json={"url": WEBHOOK_URL}, timeout=10)
            print(f"Webhook setup: {response.json()}")
        except Exception as e:
            print(f"Error setting webhook: {e}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
