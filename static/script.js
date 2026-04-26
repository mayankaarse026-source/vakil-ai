document.addEventListener("DOMContentLoaded", () => {

const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");

const sendBtn = document.getElementById("sendBtn");
const plusBtn = document.getElementById("plusBtn");
const soundBtn = document.getElementById("soundBtn");

const plusMenu = document.getElementById("plusMenu");

const uploadBtn = document.getElementById("uploadBtn");
const lawBtn = document.getElementById("lawBtn");
const firBtn = document.getElementById("firBtn");

const historyBtn = document.getElementById("historyBtn");
const addPageBtn = document.getElementById("addPageBtn");

const fileInput = document.getElementById("fileInput");
const voiceBtn = document.getElementById("voiceBtn");

// ===============================
// ⚡ STATE
// ===============================
let soundOn = true;
let isLoading = false;
let recognition = null;
let isListening = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// ===============================
// 🔽 MENU
// ===============================
function toggleMenu(menu) {
    document.querySelectorAll(".dropdown-content").forEach(m => {
        if (m !== menu) m.classList.remove("show");
    });
    menu.classList.toggle("show");
}

plusBtn.onclick = (e) => {
    e.stopPropagation();
    toggleMenu(plusMenu);
};

document.addEventListener("click", (e) => {
    if (!e.target.closest(".dropdown-content")) {
        document.querySelectorAll(".dropdown-content").forEach(m => {
            m.classList.remove("show");
        });
    }
});

// ===============================
// 💬 UI
// ===============================
function addMessage(text, type) {
    let div = document.createElement("div");

    div.className = "message-bubble " +
        (type === "user" ? "user-message" : "bot-message");

    div.innerHTML = text;

    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
    let div = document.createElement("div");
    div.id = "typing";
    div.className = "message-bubble bot-message";
    div.textContent = "Typing...";
    chatArea.appendChild(div);
}

function removeTyping() {
    let t = document.getElementById("typing");
    if (t) t.remove();
}

// ===============================
// 🔊 SPEECH (FIXED MOBILE)
// ===============================
function speakText(text) {

    if (!soundOn) return;

    window.speechSynthesis.cancel();

    let speech = new SpeechSynthesisUtterance(text);

    speech.lang = "hi-IN";
    speech.rate = 1;
    speech.pitch = 1;

    setTimeout(() => {
        window.speechSynthesis.speak(speech);
    }, 100);
}

soundBtn.onclick = () => {
    soundOn = !soundOn;

    if (!soundOn) window.speechSynthesis.cancel();

    soundBtn.innerText = soundOn ? "🔊 ON" : "🔇 OFF";
};

// ===============================
// 🚀 CHAT
// ===============================
async function sendMessage(msg) {

    if (!msg || isLoading) return;

    isLoading = true;

    addMessage(msg, "user");
    userInput.value = "";

    showTyping();

    try {
        let res = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({message: msg})
        });

        let data = await res.json();

        removeTyping();

        let reply = data.reply || "No response";

        addMessage(reply, "bot");
        speakText(reply);

    } catch (err) {
        removeTyping();
        addMessage("Server error ⚠️", "bot");
        console.error(err);
    }

    isLoading = false;
}

sendBtn.onclick = () => sendMessage(userInput.value);

userInput.addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage(userInput.value);
});

// ===============================
// 📜 HISTORY
// ===============================
historyBtn.onclick = async () => {
    try {
        let res = await fetch("/history");
        let data = await res.json();

        chatArea.innerHTML = "";

        data.reverse().forEach(c => {
            addMessage(c.user, "user");
            addMessage(c.bot, "bot");
        });

    } catch {
        addMessage("History load error", "bot");
    }
};

// ===============================
// ➕ PAGE
// ===============================
addPageBtn.onclick = () => {
    chatArea.innerHTML = "";
    addMessage("New Page Created", "bot");
};

// ===============================
// 📎 UPLOAD
// ===============================
uploadBtn.onclick = () => fileInput.click();

fileInput.onchange = async () => {

    let file = fileInput.files[0];
    if (!file) return;

    let form = new FormData();
    form.append("file", file);

    showTyping();

    try {
        let res = await fetch("/upload", {
            method: "POST",
            body: form
        });

        let data = await res.json();

        removeTyping();

        if (data.image_url) {
            let img = document.createElement("img");
            img.src = data.image_url;
            img.style.maxWidth = "220px";
            chatArea.appendChild(img);
        }

        if (data.text) addMessage(data.text, "bot");

        if (data.answer) {
            addMessage(data.answer, "bot");
            speakText(data.answer);
        }

    } catch {
        removeTyping();
        addMessage("Upload error", "bot");
    }
};

// ===============================
// ⚖️ LAW
// ===============================
lawBtn.onclick = async () => {
    let q = prompt("कानून पूछो:");
    if (!q) return;

    try {
        let res = await fetch("/law", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({query:q})
        });

        let data = await res.json();

        addMessage(data.result, "bot");
        speakText(data.result);

    } catch {
        addMessage("Law error", "bot");
    }
};

// ===============================
// 📄 FIR (FIXED BUG)
// ===============================
firBtn.onclick = async () => {

    let name = prompt("नाम:");
    let address = prompt("पता:");
    let mobile = prompt("मोबाइल नंबर:");
    let incident = prompt("घटना का विवरण:");
    let date = prompt("तारीख:");
    let time = prompt("समय:");
    let police_station = prompt("थाना:");
    let sections = prompt("धारा:");

    if (!name || !incident) return;

    try {
        let res = await fetch("/fir", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                name, address, mobile, incident, date, time, police_station, sections
            })
        });

        let data = await res.json();

        addMessage("<pre>" + data.fir + "</pre>", "bot");
        speakText(data.fir);

    } catch {
        addMessage("FIR error", "bot");
    }
};

// ===============================
// 🎤 VOICE (FULL FIXED)
// ===============================
function startVoice() {

    if (!SpeechRecognition) {
        alert("❌ Chrome use करो");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "hi-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        isListening = true;
        voiceBtn.innerText = "🛑";
        addMessage("🎤 Listening...", "bot");
    };

    recognition.onresult = (event) => {
        let text = event.results[0][0].transcript;
        addMessage(text, "user");
        sendMessage(text);
    };

    recognition.onerror = (e) => {
        addMessage("Mic error: " + e.error, "bot");
    };

    recognition.onend = () => {
        isListening = false;
        voiceBtn.innerText = "🎤";
    };

    recognition.start();
}

voiceBtn.onclick = async () => {

    if (isListening && recognition) {
        recognition.stop();
        isListening = false;
        voiceBtn.innerText = "🎤";
        return;
    }

    try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        startVoice();
    } catch {
        alert("Mic permission allow करो 🔒");
    }
};

});
