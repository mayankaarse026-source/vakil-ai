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
# 🔑 TESSERACT
# ==============================
tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# ==============================
# 🔒 FILE TYPES
# ==============================
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================
# 🗄️ DATABASE (FIXED)
# ==============================
def init_db():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                bot TEXT,
                time TEXT
            )
        """)
        conn.commit()

init_db()

def save_history(user, bot):
    try:
        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO chat_history (user, bot, time) VALUES (?, ?, ?)",
                (user, bot, str(datetime.datetime.now()))
            )
            conn.commit()
    except Exception as e:
        print("DB Save Error:", e)

def load_history():
    try:
        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user, bot, time
                FROM chat_history
                ORDER BY id DESC
                LIMIT 50
            """)
            rows = c.fetchall()

        return [{"user": r[0], "bot": r[1], "time": r[2]} for r in rows]

    except Exception as e:
        print("DB Load Error:", e)
        return []

# ==============================
# 🤖 OPENROUTER AI
# ==============================
api_key = os.getenv("OPENROUTER_API_KEY")

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
        return f"AI Error: {str(e)}"

# ==============================
# 🖼️ OCR
# ==============================
def read_image_text(path):
    try:
        img = Image.open(path)
        img = img.resize((800, 800))
        img = img.convert("L")

        text = pytesseract.image_to_string(img, lang="eng+hin").strip()

        if not text:
            return "कोई टेक्स्ट नहीं मिला", ""

        answer = ""
        if len(text) < 1000:
            answer = vakil_ai("संक्षेप में समझाओ: " + text)

        return text, answer

    except Exception as e:
        return "", f"OCR Error: {str(e)}"

# ==============================
# 📄 FIR GENERATOR
# ==============================
def generate_fir_advanced(name, address, mobile, incident, date, time, police_station, sections=""):
    today = datetime.date.today().strftime("%d-%m-%Y")

    return f"""
सेवा में,
थाना प्रभारी,
{police_station}

दिनांक: {today}

विषय: FIR दर्ज कराने हेतु आवेदन

महोदय,

मैं {name}, मोबाइल {mobile}, निवासी {address} हूँ।

घटना:
{incident}

दिनांक: {date}
समय: {time}

अतः आपसे निवेदन है कि कृपया इस मामले में FIR दर्ज कर उचित कानूनी कार्यवाही करने की कृपा करें।

{f"धाराएँ: {sections}" if sections else ""}

भवदीय,
{name}
""".strip()

# ==============================
# 🌐 ROUTES
# ==============================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"reply": "कृपया संदेश लिखें"})

    if user_msg.lower() in ["hi", "hello", "namaste"]:
        bot_reply = "नमस्ते! मैं आपकी कानूनी सहायता के लिए हूँ।"
    else:
        bot_reply = vakil_ai(user_msg)

    save_history(user_msg, bot_reply)

    return jsonify({"reply": bot_reply})

@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]

        filename = secure_filename(file.filename)
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
        return jsonify({"error": str(e)})

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/history")
def history():
    return jsonify(load_history())

@app.route("/law", methods=["POST"])
def law():
    data = request.json
    result = vakil_ai("भारतीय कानून समझाओ: " + data.get("query", ""))
    return jsonify({"result": result})

@app.route("/fir", methods=["POST"])
def fir():
    data = request.json

    return jsonify({
        "fir": generate_fir_advanced(
            data.get("name"),
            data.get("address"),
            data.get("mobile"),
            data.get("incident"),
            data.get("date"),
            data.get("time"),
            data.get("police_station"),
            data.get("sections", "")
        )
    })

# ==============================
# 🚀 RUN (RENDER FIXED)
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)