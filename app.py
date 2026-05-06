# ==============================
# 📦 IMPORTS
# ==============================
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import datetime
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import pytesseract
from werkzeug.utils import secure_filename
import uuid

# ==============================
# 🔐 ENV
# ==============================
load_dotenv()

# ==============================
# ⚙️ APP SETUP
# ==============================
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
DB_FILE = "history.db"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# 🔑 API KEY CHECK (FIXED)
# ==============================
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("❌ OPENROUTER_API_KEY missing")

# ==============================
# 🔑 TESSERACT
# ==============================
tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# ==============================
# 🔒 FILE VALIDATION (SECURE)
# ==============================
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================
# 🗄️ DATABASE (✅ PAGE SUPPORT)
# ==============================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page TEXT,
                user TEXT,
                bot TEXT,
                time TEXT
            )
        """)
        conn.commit()

init_db()

def save_history(page, user, bot):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_history (page, user, bot, time) VALUES (?, ?, ?, ?)",
            (page, user, bot, str(datetime.datetime.now()))
        )
        conn.commit()

def load_history(page):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user, bot, time 
            FROM chat_history 
            WHERE page=? 
            ORDER BY id ASC
            LIMIT 100
        """, (page,))
        rows = c.fetchall()

    return [{"user": r[0], "bot": r[1], "time": r[2]} for r in rows]

# ==============================
# 🤖 OPENROUTER
# ==============================
client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

def vakil_ai(user_input):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "आप भारतीय कानूनी सहायक हैं। सरल और छोटा उत्तर दें।"},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=150
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI Error:", e)
        return "⚠️ AI सेवा अभी उपलब्ध नहीं है"

# ==============================
# 🖼️ OCR (SAFE)
# ==============================
def read_image_text(path):
    try:
        img = Image.open(path)
        img = img.convert("RGB")
        img = img.resize((800, 800))

        text = pytesseract.image_to_string(img, lang="eng+hin").strip()

        if not text:
            return "कोई टेक्स्ट नहीं मिला", ""

        answer = ""
        if len(text) < 1000:
            answer = vakil_ai("संक्षेप में समझाओ: " + text)

        return text, answer

    except Exception as e:
        print("OCR Error:", e)
        return "OCR काम नहीं कर रहा", ""

# ==============================
# 📄 FIR GENERATOR
# ==============================
def generate_fir_advanced(name, address, mobile, incident, date, time, police_station):
    today = datetime.date.today().strftime("%d-%m-%Y")

    return f"""
सेवा में,
थाना प्रभारी,
{police_station}

दिनांक: {today}

विषय: प्रथम सूचना रिपोर्ट (FIR) दर्ज कराने हेतु आवेदन

महोदय,

मैं {name}, निवासी {address}, मोबाइल नंबर {mobile},
आपके थाना क्षेत्र में घटित एक घटना के संबंध में यह आवेदन प्रस्तुत कर रहा/रही हूँ।

घटना का दिनांक: {date}
घटना का समय: {time}

घटना का विवरण:
{incident}

अतः आपसे निवेदन है कि उक्त घटना के संबंध में
उचित कानूनी कार्यवाही करने की कृपा करें।

मैं यह घोषणा करता/करती हूँ कि उपरोक्त जानकारी मेरे ज्ञान एवं विश्वास के अनुसार सत्य है।

धन्यवाद।

भवदीय,
{name}
{address}
मोबाइल: {mobile}
""".strip()

# ==============================
# 🌐 ROUTES
# ==============================
@app.route("/")
def home():
    return render_template("index.html")

# ==============================
# 💬 CHAT (✅ PAGE FIX)
# ==============================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}

        user_msg = data.get("message", "").strip()
        page = data.get("page", "main")   # ✅ IMPORTANT

        if not user_msg:
            return jsonify({"reply": "कृपया संदेश लिखें"})

        if user_msg.lower() in ["hi", "hello", "namaste"]:
            bot_reply = "नमस्ते! मैं आपकी कानूनी सहायता के लिए हूँ।"
        else:
            bot_reply = vakil_ai(user_msg)

        save_history(page, user_msg, bot_reply)   # ✅ IMPORTANT

        return jsonify({"reply": bot_reply})

    except Exception as e:
        print("Chat Error:", e)
        return jsonify({"reply": "Server Error"})

# ==============================
# 📜 HISTORY (✅ PAGE BASED)
# ==============================
@app.route("/history/<page>")
def history(page):
    return jsonify(load_history(page))

# ==============================
# 📎 UPLOAD (FULL SAFE)
# ==============================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files.get("file")

        if not file:
            return jsonify({"error": "File नहीं मिला"})

        filename = secure_filename(file.filename)

        if filename == "":
            return jsonify({"error": "Filename खाली है"})

        if not allowed_file(filename):
            return jsonify({"error": "❌ केवल image files allow हैं"})

        unique_name = str(uuid.uuid4()) + "_" + filename
        path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)

        file.save(path)

        text, answer = read_image_text(path)

        return jsonify({
            "image_url": f"/uploads/{unique_name}",
            "text": text,
            "answer": answer
        })

    except Exception as e:
        print("Upload Error:", e)
        return jsonify({"error": "Upload failed"})

# ==============================
# 📁 SERVE FILE
# ==============================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ==============================
# ⚖️ LAW
# ==============================
@app.route("/law", methods=["POST"])
def law():
    data = request.json or {}
    result = vakil_ai("भारतीय कानून समझाओ: " + data.get("query", ""))
    return jsonify({"result": result})

# ==============================
# 📄 FIR
# ==============================
@app.route("/fir", methods=["POST"])
def fir():
    data = request.json or {}

    return jsonify({
        "fir": generate_fir_advanced(
            data.get("name"),
            data.get("address"),
            data.get("mobile"),
            data.get("incident"),
            data.get("date"),
            data.get("time"),
            data.get("police_station"),
        )
    })

# ==============================
# 🚀 RUN
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
