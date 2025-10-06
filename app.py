import os
import requests
import json
import hmac
import hashlib
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from flask import Flask, request
from contextlib import contextmanager
import traceback

TOKEN = os.getenv("BOT_TOKEN")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ CORRECT RENDER URL SET
RENDER_URL = "https://bpharmabot-rp6m.onrender.com"

WEBHOOK_PATH = "/webhook"
PAYMENT_WEBHOOK_PATH = "/payment_webhook"
PAYMENT_SUCCESS_PATH = "/payment_success"
WEBHOOK_URL = RENDER_URL + WEBHOOK_PATH
PAYMENT_WEBHOOK_URL = RENDER_URL + PAYMENT_WEBHOOK_PATH
PAPER_FOLDER = "bpharm_bot_18"

app = Flask(__name__)

# -------------------------
# Database Setup with Connection Pool
# -------------------------
db_pool = None

def init_db():
    """Initialize PostgreSQL database with connection pooling"""
    global db_pool
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1,
            20,
            DATABASE_URL
        )
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_payments (
                user_id BIGINT,
                semester TEXT,
                paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, semester)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id BIGINT PRIMARY KEY,
                semester TEXT,
                nav_message_id BIGINT
            )
        ''')
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        print("✅ PostgreSQL database initialized with connection pool")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        traceback.print_exc()

@contextmanager
def get_db():
    """Context manager for database connections from pool"""
    conn = None
    try:
        conn = db_pool.getconn()
        yield conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise
    finally:
        if conn:
            db_pool.putconn(conn)

def is_semester_paid(user_id, semester):
    """Check if user has paid for a semester"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_payments WHERE user_id = %s AND semester = %s",
                (user_id, semester)
            )
            result = cursor.fetchone()
            cursor.close()
            return result is not None
    except Exception as e:
        print(f"❌ Error checking payment: {e}")
        traceback.print_exc()
        return False

def mark_semester_paid(user_id, semester):
    """Mark semester as paid for user"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_payments (user_id, semester) VALUES (%s, %s) ON CONFLICT (user_id, semester) DO NOTHING",
                (user_id, semester)
            )
            conn.commit()
            cursor.close()
        print(f"✅ Marked {semester} as paid for user {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error marking payment: {e}")
        traceback.print_exc()
        return False

def save_user_session(user_id, semester, nav_message_id=None):
    """Save user session data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO user_sessions (user_id, semester, nav_message_id) 
                   VALUES (%s, %s, %s) 
                   ON CONFLICT (user_id) 
                   DO UPDATE SET semester = %s, nav_message_id = %s""",
                (user_id, semester, nav_message_id, semester, nav_message_id)
            )
            conn.commit()
            cursor.close()
    except Exception as e:
        print(f"❌ Error saving session: {e}")
        traceback.print_exc()

def get_user_session(user_id):
    """Get user session data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT semester, nav_message_id FROM user_sessions WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            if result:
                return {"semester": result[0], "nav_message_id": result[1]}
            return {}
    except Exception as e:
        print(f"❌ Error getting session: {e}")
        traceback.print_exc()
        return {}

# -------------------------
# Semester-subject mapping
# -------------------------
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
        print(f"❌ Error sending message: {e}")
        traceback.print_exc()
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
            
            print(f"⚠️ Edit message failed: {response_data}")
            return None
        
        return response_data
    except Exception as e:
        print(f"❌ Error editing message: {e}")
        traceback.print_exc()
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
        print(f"❌ Error sending document: {e}")
        traceback.print_exc()
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
        print(f"❌ Error answering callback: {e}")
        traceback.print_exc()
        return None

def create_razorpay_payment_link(amount, semester, user_id, chat_id):
    """Create Razorpay payment link with callback URL"""
    url = "https://api.razorpay.com/v1/payment_links"
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    
    callback_url = f"{RENDER_URL}{PAYMENT_SUCCESS_PATH}?user_id={user_id}&semester={semester}&chat_id={chat_id}"
    
    payload = {
        "amount": amount * 100,
        "currency": "INR",
        "description": f"{semester} - B.Pharm Study Material",
        "callback_url": callback_url,
        "callback_method": "get",
        "notes": {
            "semester": semester,
            "user_id": str(user_id),
            "chat_id": str(chat_id)
        }
    }
    
    try:
        response = requests.post(url, json=payload, auth=auth, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ Error creating payment link: {e}")
        traceback.print_exc()
        return None

def verify_razorpay_signature(payload, signature, secret):
    """Verify Razorpay webhook signature"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

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
    """Handle semester selection"""
    save_user_session(user_id, semester, message_id)
    
    if is_semester_paid(user_id, semester):
        show_subjects(chat_id, message_id, user_id, semester)
    else:
        show_payment_screen(chat_id, message_id, user_id, semester)

def show_payment_screen(chat_id, message_id, user_id, semester):
    """Show payment screen with Razorpay payment link"""
    payment_link_data = create_razorpay_payment_link(10, semester, user_id, chat_id)
    
    if not payment_link_data or "short_url" not in payment_link_data:
        send_message(chat_id, "❌ Error creating payment link. Please try again later.")
        return
    
    payment_url = payment_link_data["short_url"]
    
    keyboard = [
        [{"text": "💳 Pay ₹10 to Unlock", "url": payment_url}],
        [{"text": "✅ I've Completed Payment", "callback_data": f"CHECK_PAYMENT_{semester}"}],
        [{"text": "🔙 Back to Semesters", "callback_data": "BACK_SEMESTERS"}]
    ]
    reply_markup = {"inline_keyboard": keyboard}
    
    text = (
        f"🔒 *{semester}*\n\n"
        f"💰 Price: ₹10 (One-time payment)\n"
        f"✅ Lifetime access to all subjects\n"
        f"📚 Previous year papers + Guess papers\n\n"
        f"👇 Click below to pay, then return and click 'I've Completed Payment'"
    )
    
    result = edit_message(chat_id, message_id, text, reply_markup)
    
    if not result or not result.get('ok'):
        new_result = send_message(chat_id, text, reply_markup)
        if new_result and new_result.get('ok'):
            save_user_session(user_id, semester, new_result['result']['message_id'])

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
            save_user_session(user_id, semester, new_result['result']['message_id'])

def handle_subject_selection(chat_id, message_id, user_id, subject):
    """After subject selection, send files"""
    user_info = get_user_session(user_id)
    semester = user_info.get("semester")
    
    if not semester:
        send_message(chat_id, "❗Please select a semester first using /start")
        return

    if not is_semester_paid(user_id, semester):
        answer_callback_query(message_id, "❌ Please pay to unlock this semester first!")
        return

    edit_message(chat_id, message_id, f"✅ Selected: *{subject}*", None)

    loading_msg = send_message(chat_id, f"📂 Loading files for: *{subject}*...")

    base = make_base_filename(subject)
    folder = semester.replace(" ", "_")
    prev_path = os.path.join(PAPER_FOLDER, folder, f"{base}.pdf")
    guess_path = os.path.join(PAPER_FOLDER, folder, f"{base}_Guess.pdf")

    if os.path.exists(prev_path):
        send_document(chat_id, prev_path, f"📄 Previous Year • {subject}")
    else:
        send_message(chat_id, f"❌ Previous year file not found for {subject}!")

    if os.path.exists(guess_path):
        send_document(chat_id, guess_path, f"📝 Guess Paper • {subject}")
    else:
        send_message(chat_id, f"❌ Guess paper not found for {subject}!")

    keyboard = [
        [{"text": "⬅ Back to Subjects", "callback_data": "BACK_SUBJECTS"}],
        [{"text": "🔙 Back to Semesters", "callback_data": "BACK_SEMESTERS"}],
    ]
    
    nav_text = f"📂 Files sent for: *{subject}*\n\nChoose next action:"
    nav_result = send_message(chat_id, nav_text, {"inline_keyboard": keyboard})
    
    if nav_result and nav_result.get('ok'):
        save_user_session(user_id, semester, nav_result['result']['message_id'])

    if loading_msg and loading_msg.get('ok'):
        try:
            delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
            requests.post(delete_url, json={
                "chat_id": chat_id, 
                "message_id": loading_msg['result']['message_id']
            }, timeout=5)
        except:
            pass

def handle_check_payment(chat_id, message_id, user_id, semester, callback_query_id):
    """Check if payment has been completed"""
    print(f"🔍 Checking payment for user {user_id}, semester {semester}")
    
    if is_semester_paid(user_id, semester):
        answer_callback_query(callback_query_id, "✅ Payment verified!")
        show_subjects(chat_id, message_id, user_id, semester)
    else:
        answer_callback_query(callback_query_id, "❌ Payment not yet confirmed. Please wait a moment or complete payment first.")

def handle_back_to_subjects(chat_id, message_id, user_id):
    """Show subject list again"""
    info = get_user_session(user_id)
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
    
    info = get_user_session(user_id)
    nav_message_id = info.get("nav_message_id", message_id)
    
    result = edit_message(chat_id, nav_message_id, "📚 Select Semester:", reply_markup)
    
    if not result or not result.get('ok'):
        new_result = send_message(chat_id, "📚 Select Semester:", reply_markup)
        if new_result and new_result.get('ok'):
            save_user_session(user_id, info.get("semester"), new_result['result']['message_id'])

# -------------------------
# Flask routes
# -------------------------
@app.route("/")
def home():
    if not TOKEN:
        return "❌ BOT_TOKEN environment variable not set!", 500
    return "✅ Bot is Live on Render!", 200

@app.route(PAYMENT_SUCCESS_PATH, methods=["GET"])
def payment_success():
    """Handle successful payment redirect"""
    user_id = request.args.get('user_id')
    semester = request.args.get('semester')
    chat_id = request.args.get('chat_id')
    
    print(f"💰 Payment success callback: user={user_id}, semester={semester}, chat={chat_id}")
    
    if user_id and semester and chat_id:
        try:
            user_id = int(user_id)
            chat_id = int(chat_id)
            
            # Mark as paid
            success = mark_semester_paid(user_id, semester)
            
            if success:
                print(f"✅ Successfully marked semester {semester} as paid for user {user_id}")
                
                # Send confirmation to user
                success_text = (
                    f"✅ *Payment Successful!*\n\n"
                    f"🎉 *{semester} Unlocked!*\n\n"
                    f"📱 Click 'I've Completed Payment' button to access your materials."
                )
                send_message(chat_id, success_text)
            else:
                print(f"❌ Failed to mark payment for user {user_id}")
            
        except Exception as e:
            print(f"❌ Error processing payment: {e}")
            traceback.print_exc()
    else:
        print(f"⚠️ Missing parameters: user_id={user_id}, semester={semester}, chat_id={chat_id}")
    
    # Return success page
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Payment Successful</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                }
                .container {
                    text-align: center;
                    background: white;
                    padding: 50px 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 500px;
                    animation: slideIn 0.5s ease-out;
                }
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(-30px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                .checkmark {
                    font-size: 80px;
                    margin-bottom: 20px;
                    animation: bounce 0.6s ease-out;
                }
                @keyframes bounce {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.2); }
                }
                h1 {
                    color: #28a745;
                    margin-bottom: 20px;
                    font-size: 32px;
                    font-weight: 700;
                }
                p {
                    color: #555;
                    font-size: 18px;
                    margin: 15px 0;
                    line-height: 1.6;
                }
                .highlight {
                    background: #fff3cd;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    border-left: 4px solid #ffc107;
                }
                .btn {
                    display: inline-block;
                    margin-top: 30px;
                    padding: 15px 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: bold;
                    font-size: 18px;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                }
                .btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
                }
                .steps {
                    text-align: left;
                    margin: 25px 0;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 10px;
                }
                .steps ol {
                    margin-left: 20px;
                }
                .steps li {
                    margin: 10px 0;
                    color: #333;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✅</div>
                <h1>Payment Successful!</h1>
                <p><strong>Your semester has been unlocked!</strong></p>
                
                <div class="steps">
                    <p style="margin-bottom: 10px; font-weight: bold;">📱 Next Steps:</p>
                    <ol>
                        <li>Go back to Telegram</li>
                        <li>Click the <strong>"✅ I've Completed Payment"</strong> button</li>
                        <li>Access your study materials</li>
                    </ol>
                </div>
                
                <div class="highlight">
                    <p style="margin: 0;"><strong>💡 Tip:</strong> You now have lifetime access to all subjects!</p>
                </div>
                
                <a href="https://t.me/PharmaCrackBot" class="btn">Open Bot →</a>
            </div>
        </body>
    </html>
    """

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        print("📨 Webhook received")
        
        if not TOKEN:
            print("❌ Bot not initialized - TOKEN missing")
            return "ok", 200

        data = request.get_json()
        if not data:
            print("❌ No data received")
            return "ok", 200

        print(f"📦 Received data: {json.dumps(data, indent=2)}")

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]

            if "text" in message and str(message["text"]).startswith("/start"):
                print(f"🚀 Start command from chat_id: {chat_id}")
                handle_start(chat_id)

        elif "callback_query" in data:
            callback_query = data["callback_query"]
            callback_query_id = callback_query["id"]
            chat_id = callback_query["message"]["chat"]["id"]
            message_id = callback_query["message"]["message_id"]
            user_id = callback_query["from"]["id"]
            callback_data = callback_query["data"]

            print(f"🔔 Callback: {callback_data} from user: {user_id}")

            answer_callback_query(callback_query_id)

            if callback_data in semesters:
                handle_semester_selection(chat_id, message_id, user_id, callback_data)

            elif callback_data.startswith("CHECK_PAYMENT_"):
                semester = callback_data.replace("CHECK_PAYMENT_", "")
                handle_check_payment(chat_id, message_id, user_id, semester, callback_query_id)

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

        print("✅ Webhook processed successfully")
        return "ok", 200

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        traceback.print_exc()
        return "ok", 200

@app.route(PAYMENT_WEBHOOK_PATH, methods=["POST"])
def payment_webhook():
    """Handle Razorpay payment webhook"""
    try:
        payload = request.get_data()
        signature = request.headers.get('X-Razorpay-Signature')
        
        print(f"🔔 Payment webhook received")
        
        if not signature or not RAZORPAY_KEY_SECRET:
            print("❌ Missing signature or secret")
            return "ok", 200
        
        if not verify_razorpay_signature(payload, signature, RAZORPAY_KEY_SECRET):
            print("❌ Invalid signature")
            return "ok", 200
        
        data = request.get_json()
        event = data.get('event')
        print(f"📨 Event: {event}")
        
        if event == 'payment_link.paid':
            payment_link = data.get('payload', {}).get('payment_link', {}).get('entity', {})
            notes = payment_link.get('notes', {})
            
            user_id = notes.get('user_id')
            chat_id = notes.get('chat_id')
            semester = notes.get('semester')
            
            if user_id and semester and chat_id:
                user_id = int(user_id)
                chat_id = int(chat_id)
                
                mark_semester_paid(user_id, semester)
                
                success_text = (
                    f"✅ *Payment Confirmed!*\n\n"
                    f"🎉 *{semester} Unlocked!*\n\n"
                    f"Click 'I've Completed Payment' to access materials."
                )
                send_message(chat_id, success_text)
        
        return "ok", 200
        
    except Exception as e:
        print(f"❌ Payment webhook error: {e}")
        traceback.print_exc()
        return "ok", 200

# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    # Initialize database
    if DATABASE_URL:
        init_db()
    else:
        print("⚠️ WARNING: DATABASE_URL not set!")
    
    if TOKEN:
        try:
            # Delete old webhook first
            delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
            requests.post(delete_url, timeout=10)
            print("🗑️ Old webhook deleted")
            
            # Set new webhook
            webhook_api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
            response = requests.post(
                webhook_api_url, 
                json={
                    "url": WEBHOOK_URL,
                    "allowed_updates": ["message", "callback_query"]
                }, 
                timeout=10
            )
            print(f"🔗 Webhook setup: {response.json()}")
            
            # Verify webhook
            info_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
            info_response = requests.get(info_url, timeout=10)
            print(f"ℹ️ Webhook info: {info_response.json()}")
            
        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            traceback.print_exc()

    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
