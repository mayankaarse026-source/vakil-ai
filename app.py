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
import pyttsx3
import threading   # ✅ NEW (for speed)

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
# 🔊 VOICE OUTPUT (NON-BLOCKING)
# ==============================
engine = pyttsx3.init()

def speak(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except:
        pass

def speak_async(text):
    threading.Thread(target=speak, args=(text,)).start()   # ✅ FAST

# ==============================
# 🔑 TESSERACT
# ==============================
tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# ==============================
# 🔒 FILE CHECK
# ==============================
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================
# 🗄️ DATABASE
# ==============================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_history (user, bot, time) VALUES (?, ?, ?)",
            (user, bot, str(datetime.datetime.now()))
        )
        conn.commit()

def load_history():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT user, bot, time FROM chat_history ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()

    return [{"user": r[0], "bot": r[1], "time": r[2]} for r in rows]

# ==============================
# 🤖 OPENROUTER
# ==============================
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("OPENROUTER_API_KEY missing")

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

# ==============================
# 🧠 AI FUNCTION (FASTER)
# ==============================
def vakil_ai(user_input):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "आप भारतीय कानूनी सहायक हैं। छोटा और स्पष्ट जवाब दें।"},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,      # ✅ faster + stable
            max_tokens=150        # ✅ faster
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"AI Error: {str(e)}"

# ==============================
# 🖼️ OCR (OPTIMIZED + FAST)
# ==============================
def read_image_text(path):
    try:
        img = Image.open(path)

        # ✅ resize for speed
        img = img.resize((800, 800))
        img = img.convert("L")

        text = pytesseract.image_to_string(img, lang="eng+hin").strip()

        if not text:
            return "कोई टेक्स्ट नहीं मिला", ""

        # ✅ skip AI if text too big
        answer = ""
        if len(text) < 1000:
            answer = vakil_ai("संक्षेप में समझाओ: " + text)

        return text, answer

    except Exception as e:
        return "", f"OCR Error: {str(e)}"

# ==============================
# 📄 FIR
# ==============================
def generate_fir_advanced(name, address, mobile, incident, date, time, police_station, sections=""):
    today = datetime.date.today().strftime("%d-%m-%Y")

    return f"""
सेवा में,
थाना प्रभारी,  
{police_station}

दिनांक: {today}

विषय: प्रथम सूचना रिपोर्ट (FIR) दर्ज कराने हेतु आवेदन

महोदय,

मैं {name}, निवासी {address}, मोबाइल नंबर {mobile}, 
आपके थाना क्षेत्र में घटित एक घटना के संबंध
 में यह आवेदन प्रस्तुत कर रहा/रही हूँ।

घटना का दिनांक: {date}  
घटना का समय: {time}  

घटना का विवरण:  
{incident}

अतः आपसे निवेदन है कि उक्त घटना के संबंध में 
उचित धाराओं में मामला दर्ज कर आवश्यक कानूनी कार्यवाही करने की कृपा करें।

{f"लागू धाराएँ (यदि ज्ञात हों): {sections}" if sections else ""}

मैं यह घोषणा करता/करती हूँ
 कि उपरोक्त दी गई जानकारी मेरे ज्ञान एवं विश्वास के अनुसार सत्य है।

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
# 💬 CHAT (FAST)
# ==============================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message", "").strip()

        if not user_msg:
            return jsonify({"reply": "कृपया संदेश लिखें"})

        if user_msg.lower() in ["hi", "hello", "namaste"]:
            bot_reply = "नमस्ते! मैं आपकी कानूनी सहायता के लिए हूँ।"
        else:
            bot_reply = vakil_ai(user_msg)

        save_history(user_msg, bot_reply)

        speak_async(bot_reply)   # ✅ NON-BLOCKING

        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"})

# ==============================
# 📎 UPLOAD (FAST)
# ==============================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "File नहीं मिला"})

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Filename खाली है"})

        if not allowed_file(file.filename):
            return jsonify({"error": "सिर्फ PNG/JPG allowed है"})

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

# ==============================
# 📂 IMAGE ROUTE
# ==============================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ==============================
# 📜 HISTORY
# ==============================
@app.route("/history", methods=["GET"])
def history():
    return jsonify(load_history())

# ==============================
# ⚖️ LAW
# ==============================
@app.route("/law", methods=["POST"])
def law():
    data = request.json
    query = data.get("query", "")

    result = vakil_ai("भारतीय कानून में समझाओ: " + query)
    return jsonify({"result": result})

# ==============================
# 📄 FIR API
# ==============================
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
# 🚀 RUN
# ==============================
if __name__ == "__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=10000, debug=False)
