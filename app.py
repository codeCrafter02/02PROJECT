import os
import requests
import json
import hmac
import hashlib
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
WEBHOOK_PATH = "/webhook"
PAYMENT_WEBHOOK_PATH = "/payment_webhook"
WEBHOOK_URL = "https://zero2project-wutc.onrender.com" + WEBHOOK_PATH
PAYMENT_WEBHOOK_URL = "https://zero2project-wutc.onrender.com" + PAYMENT_WEBHOOK_PATH
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

# Store user data in memory (user_id -> {"semester": ..., "paid_semesters": [...], ...})
user_data = {}

# Store payment data temporarily (order_id -> {"user_id": ..., "semester": ...})
pending_payments = {}

# -------------------------
# Utilities
# -------------------------
def make_base_filename(subject: str) -> str:
    return subject.replace(" ", "_").replace("-", "").replace("/", "")

def send_message(chat_id, text, reply_markup=None):
    """Send message using requests"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
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
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        if not response_data.get('ok'):
            error_code = response_data.get('error_code')
            error_description = response_data.get('description', '')
            
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

def answer_callback_query(callback_query_id, text=None):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
        data["show_alert"] = True
    try:
        response = requests.post(url, json=data, timeout=5)
        return response.json()
    except Exception as e:
        print(f"Error answering callback: {e}")
        return None

def create_razorpay_order(amount, semester, user_id):
    """Create Razorpay order"""
    url = "https://api.razorpay.com/v1/orders"
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    
    payload = {
        "amount": amount * 100,  # amount in paise
        "currency": "INR",
        "notes": {
            "semester": semester,
            "user_id": str(user_id)
        }
    }
    
    try:
        response = requests.post(url, json=payload, auth=auth, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error creating order: {e}")
        return None

def verify_razorpay_signature(payload, signature, secret):
    """Verify Razorpay webhook signature"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

def is_semester_paid(user_id, semester):
    """Check if user has paid for a semester"""
    user_info = user_data.get(user_id, {})
    paid_semesters = user_info.get("paid_semesters", [])
    return semester in paid_semesters

def mark_semester_paid(user_id, semester):
    """Mark semester as paid for user"""
    if user_id not in user_data:
        user_data[user_id] = {}
    if "paid_semesters" not in user_data[user_id]:
        user_data[user_id]["paid_semesters"] = []
    if semester not in user_data[user_id]["paid_semesters"]:
        user_data[user_id]["paid_semesters"].append(semester)

# -------------------------
# Handlers
# -------------------------
def handle_start(chat_id):
    """Handle /start command -> show semester list"""
    keyboard = [[{"text": sem, "callback_data": sem}] for sem in semesters.keys()]
    keyboard.append([{"text": "📩 Feedback", "url": "https://codecrafter02.github.io/Feedback02/"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    welcome_text = (
        "🎓 *Welcome to B.Pharm Study Material Bot!*\n\n"
        "📚 Select your semester to get started:\n\n"
        "💡 Each semester contains:\n"
        "   • Previous Year Papers\n"
        "   • Guess Papers\n"
        "   • All Subjects\n\n"
        "💰 One-time payment: ₹10/semester"
    )
    
    result = send_message(chat_id, welcome_text, reply_markup)
    return result

def handle_semester_selection(chat_id, message_id, user_id, semester):
    """Handle semester selection -> check payment and show subjects or payment button"""
    user_data[user_id] = {
        "semester": semester, 
        "nav_message_id": message_id
    }
    
    # Check if user has paid for this semester
    if is_semester_paid(user_id, semester):
        show_subjects(chat_id, message_id, user_id, semester)
    else:
        show_payment_screen(chat_id, message_id, user_id, semester)

def show_payment_screen(chat_id, message_id, user_id, semester):
    """Show payment screen with Razorpay payment button"""
    # Create Razorpay order
    order = create_razorpay_order(10, semester, user_id)
    
    if not order or "id" not in order:
        send_message(chat_id, "❌ Error creating payment. Please try again.")
        return
    
    order_id = order["id"]
    pending_payments[order_id] = {
        "user_id": user_id,
        "chat_id": chat_id,
        "semester": semester,
        "message_id": message_id
    }
    
    # Create payment link
    payment_link = f"https://api.razorpay.com/v1/checkout/embedded?key_id={RAZORPAY_KEY_ID}&order_id={order_id}"
    
    keyboard = [
        [{"text": "💳 Pay ₹10 to Unlock", "url": payment_link}],
        [{"text": "🔙 Back to Semesters", "callback_data": "BACK_SEMESTERS"}]
    ]
    reply_markup = {"inline_keyboard": keyboard}
    
    text = (
        f"🔒 *{semester}*\n\n"
        f"💰 Price: ₹10 (One-time payment)\n"
        f"✅ Lifetime access to all subjects\n"
        f"📚 Previous year papers + Guess papers\n\n"
        f"Click the button below to pay:"
    )
    
    result = edit_message(chat_id, message_id, text, reply_markup)
    
    if not result or not result.get('ok'):
        new_result = send_message(chat_id, text, reply_markup)
        if new_result and new_result.get('ok'):
            user_data[user_id]["nav_message_id"] = new_result['result']['message_id']

def show_subjects(chat_id, message_id, user_id, semester):
    """Show subjects for unlocked semester"""
    subjects = semesters[semester]
    keyboard = [[{"text": subject, "callback_data": subject}] for subject in subjects]
    keyboard.append([{"text": "🔙 Back to Semesters", "callback_data": "BACK_SEMESTERS"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    text = f"📘 *{semester}*\n✅ Unlocked\n\nSelect a subject:"
    
    result = edit_message(chat_id, message_id, text, reply_markup)
    
    if not result or not result.get('ok'):
        new_result = send_message(chat_id, text, reply_markup)
        if new_result and new_result.get('ok'):
            user_data[user_id]["nav_message_id"] = new_result['result']['message_id']

def handle_subject_selection(chat_id, message_id, user_id, subject):
    """After subject selection, send files and create NEW navigation message"""
    user_info = user_data.get(user_id, {})
    semester = user_info.get("semester")
    if not semester:
        send_message(chat_id, "❗Please select a semester first using /start")
        return

    # Check if semester is paid
    if not is_semester_paid(user_id, semester):
        answer_callback_query(message_id, "❌ Please pay to unlock this semester first!")
        return

    user_data.setdefault(user_id, {})["subject"] = subject

    edit_message(chat_id, message_id, f"✅ Selected: *{subject}*", None)

    loading_msg = send_message(chat_id, f"📂 Loading files for: *{subject}*...")

    base = make_base_filename(subject)
    folder = semester.replace(" ", "_")
    prev_path = os.path.join(PAPER_FOLDER, folder, f"{base}.pdf")
    guess_path = os.path.join(PAPER_FOLDER, folder, f"{base}_Guess.pdf")

    files_sent = 0
    if os.path.exists(prev_path):
        send_document(chat_id, prev_path, f"📄 Previous Year • {subject}")
        files_sent += 1
    else:
        send_message(chat_id, f"❌ Previous year file not found for {subject}!")

    if os.path.exists(guess_path):
        send_document(chat_id, guess_path, f"📝 Guess Paper • {subject}")
        files_sent += 1
    else:
        send_message(chat_id, f"❌ Guess paper not found for {subject}!")

    keyboard = [
        [{"text": "⬅ Back to Subjects", "callback_data": "BACK_SUBJECTS"}],
        [{"text": "🔙 Back to Semesters", "callback_data": "BACK_SEMESTERS"}],
    ]
    
    nav_text = f"📂 Files sent for: *{subject}*\n\nChoose next action:"
    nav_result = send_message(chat_id, nav_text, {"inline_keyboard": keyboard})
    
    if nav_result and nav_result.get('ok'):
        user_data[user_id]["nav_message_id"] = nav_result['result']['message_id']

    # Delete loading message
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

    if not is_semester_paid(user_id, semester):
        show_payment_screen(chat_id, message_id, user_id, semester)
        return

    show_subjects(chat_id, message_id, user_id, semester)

def handle_back_to_semesters(chat_id, message_id, user_id):
    """Show semester list again"""
    keyboard = [[{"text": sem, "callback_data": sem}] for sem in semesters.keys()]
    keyboard.append([{"text": "📩 Feedback", "url": "https://codecrafter02.github.io/Feedback02/"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    info = user_data.get(user_id, {})
    nav_message_id = info.get("nav_message_id", message_id)
    
    result = edit_message(chat_id, nav_message_id, "📚 Select Semester:", reply_markup)
    
    if not result or not result.get('ok'):
        new_result = send_message(chat_id, "📚 Select Semester:", reply_markup)
        if new_result and new_result.get('ok') and user_id in user_data:
            user_data[user_id]["nav_message_id"] = new_result['result']['message_id']

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

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]

            if "text" in message and str(message["text"]).startswith("/start"):
                handle_start(chat_id)

        elif "callback_query" in data:
            callback_query = data["callback_query"]
            callback_query_id = callback_query["id"]
            chat_id = callback_query["message"]["chat"]["id"]
            message_id = callback_query["message"]["message_id"]
            user_id = callback_query["from"]["id"]
            callback_data = callback_query["data"]

            answer_callback_query(callback_query_id)

            if callback_data in semesters:
                handle_semester_selection(chat_id, message_id, user_id, callback_data)

            elif callback_data == "BACK_SUBJECTS":
                handle_back_to_subjects(chat_id, message_id, user_id)

            elif callback_data == "BACK_SEMESTERS":
                handle_back_to_semesters(chat_id, message_id, user_id)

            else:
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

@app.route(PAYMENT_WEBHOOK_PATH, methods=["POST"])
def payment_webhook():
    """Handle Razorpay payment webhook"""
    try:
        payload = request.get_data()
        signature = request.headers.get('X-Razorpay-Signature')
        
        if not signature or not RAZORPAY_KEY_SECRET:
            return "Unauthorized", 401
        
        if not verify_razorpay_signature(payload, signature, RAZORPAY_KEY_SECRET):
            return "Invalid signature", 401
        
        data = request.get_json()
        event = data.get('event')
        
        if event == 'payment.captured':
            payment = data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment.get('order_id')
            
            if order_id in pending_payments:
                payment_info = pending_payments[order_id]
                user_id = payment_info['user_id']
                chat_id = payment_info['chat_id']
                semester = payment_info['semester']
                
                # Mark semester as paid
                mark_semester_paid(user_id, semester)
                
                # Send success message with WARNING (English only)
                warning_message = (
                    f"✅ *Payment Successful!*\n\n"
                    f"🎉 *{semester} Unlocked!*\n\n"
                    f"⚠️ *IMPORTANT WARNING:*\n\n"
                    f"🔴 Please *download all subject PDFs NOW!*\n\n"
                    f"❗ If you leave this page or the bot restarts, you will need to pay again.\n\n"
                    f"💾 Download all your files immediately by selecting subjects below 👇"
                )
                
                send_message(chat_id, warning_message)
                
                # Show subjects
                if user_id in user_data:
                    nav_message_id = user_data[user_id].get("nav_message_id")
                    if nav_message_id:
                        show_subjects(chat_id, nav_message_id, user_id, semester)
                
                # Remove from pending
                del pending_payments[order_id]
        
        return "ok", 200
        
    except Exception as e:
        print(f"Error processing payment webhook: {e}")
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
