document.addEventListener("DOMContentLoaded", () => {

    // ===============================
    // 🎯 ELEMENTS
    // ===============================
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
    let currentPage = "main";
    let pageCount = 1; // ✅ FIXED (only once)

    // ===============================
    // 🔽 MENU
    // ===============================
    function toggleMenu(menu) {
        document.querySelectorAll(".dropdown-content").forEach(m => {
            if (m !== menu) m.classList.remove("show");
        });
        menu.classList.toggle("show");
    }

    if (plusBtn) {
        plusBtn.onclick = (e) => {
            e.stopPropagation();
            toggleMenu(plusMenu);
        };
    }

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".dropdown-content")) {
            document.querySelectorAll(".dropdown-content").forEach(m => {
                m.classList.remove("show");
            });
        }
    });

    // ===============================
    // 💬 MESSAGE UI
    // ===============================
    function addMessage(text, type) {
        let div = document.createElement("div");

        div.className = "message-bubble " +
            (type === "user" ? "user-message" : "bot-message");

        div.textContent = text;

        chatArea.appendChild(div);
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function addFIR(text) {
        let pre = document.createElement("pre");
        pre.className = "message-bubble bot-message";
        pre.textContent = text;

        chatArea.appendChild(pre);
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
    // 🔊 SPEECH
    // ===============================
    function speakText(text) {
        if (!soundOn) return;

        window.speechSynthesis.cancel();

        let speech = new SpeechSynthesisUtterance(text);
        speech.lang = "hi-IN";
        speech.rate = 1;

        window.speechSynthesis.speak(speech);
    }

    if (soundBtn) {
        soundBtn.onclick = () => {
            soundOn = !soundOn;

            if (!soundOn) window.speechSynthesis.cancel();

            soundBtn.innerText = soundOn ? "🔊 ON" : "🔇 OFF";
        };
    }

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
                body: JSON.stringify({
                    message: msg,
                    page: currentPage
                })
            });

            let data = await res.json();

            removeTyping();

            addMessage(data.reply || "No response", "bot");
            speakText(data.reply || "No response");

        } catch (err) {
            removeTyping();
            addMessage("Server error ⚠️", "bot");
            console.error(err);
        }

        isLoading = false;
    }

    if (sendBtn) {
        sendBtn.onclick = () => sendMessage(userInput.value);
    }

    if (userInput) {
        userInput.addEventListener("keypress", e => {
            if (e.key === "Enter") sendMessage(userInput.value);
        });
    }

    // ===============================
    // 📜 HISTORY
    // ===============================
    if (historyBtn) {
        historyBtn.onclick = async () => {
            try {
                let res = await fetch(`/history/${currentPage}`);
                let data = await res.json();

                chatArea.innerHTML = "";

                data.forEach(c => {
                    addMessage(c.user, "user");
                    addMessage(c.bot, "bot");
                });

            } catch {
                addMessage("History load error", "bot");
            }
        };
    }

    // ===============================
    // ➕ PAGE SYSTEM
    // ===============================
    if (addPageBtn) {
        addPageBtn.onclick = () => {

            pageCount++;
            currentPage = "page_" + pageCount;

            chatArea.innerHTML = "";
            addMessage(`📄 New Page Created (${currentPage})`, "bot");
        };
    }

    // ===============================
    // 📎 UPLOAD
    // ===============================
    if (uploadBtn && fileInput) {
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

                if (data.error) {
                    addMessage(data.error, "bot");
                    return;
                }

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
    }

    // ===============================
    // ⚖️ LAW
    // ===============================
    if (lawBtn) {
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
    }

    // ===============================
    // 📄 FIR
    // ===============================
    if (firBtn) {
        firBtn.onclick = async () => {

            let name = prompt("नाम:");
            let address = prompt("पता:");
            let mobile = prompt("मोबाइल नंबर:");
            let incident = prompt("घटना का विवरण:");
            let date = prompt("घटना की तारीख:");
            let time = prompt("समय:");
            let police_station = prompt("थाना नाम:");

            if (!name || !incident) return;

            try {
                let res = await fetch("/fir", {
                    method:"POST",
                    headers:{"Content-Type":"application/json"},
                    body: JSON.stringify({
                        name,
                        address,
                        mobile,
                        incident,
                        date,
                        time,
                        police_station
                    })
                });

                let data = await res.json();

                addFIR(data.fir);

            } catch {
                addMessage("FIR error", "bot");
            }
        };
    }

    // ===============================
    // 🎤 VOICE
    // ===============================
    let recognition = null;
    let isListening = false;

    function startVoice() {

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert("❌ Browser support नहीं है");
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = "hi-IN";

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

        recognition.onend = () => {
            isListening = false;
            voiceBtn.innerText = "🎤";
        };

        recognition.start();
    }

    if (voiceBtn) {
        voiceBtn.onclick = async () => {

            if (isListening && recognition) {
                recognition.stop();
                return;
            }

            try {
                await navigator.mediaDevices.getUserMedia({ audio: true });
                startVoice();
            } catch {
                alert("Mic permission denied");
            }
        };
    }

});
