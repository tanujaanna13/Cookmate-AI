// =====================
// DARK MODE
// =====================
function toggleDarkMode() {
    document.body.classList.toggle("dark");
}

// =====================
// VOICE SEARCH
// =====================
function startVoice() {

    if (!('webkitSpeechRecognition' in window)) {
        alert("Voice Search is not supported in this browser.");
        return;
    }

    const recognition = new webkitSpeechRecognition();

    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.start();

    recognition.onresult = function (event) {
        document.querySelector('input[name="query"]').value =
            event.results[0][0].transcript;
    };

    recognition.onerror = function (event) {
        alert("Voice Error: " + event.error);
    };
}

// =====================
// CHATBOT (ASK CHEF)
// =====================
async function askChef(event) {

    if (event) event.preventDefault(); // IMPORTANT FIX

    let message = document.getElementById("message").value;

    if (!message.trim()) return;

    let response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: "message=" + encodeURIComponent(message)
    });

    let data = await response.json();

    let replyBox = document.getElementById("reply");

    replyBox.insertAdjacentHTML(
        "beforeend",
        `<p><b>You:</b> ${message}</p>
         <p><b>👨‍🍳 Chef:</b> ${data.reply}</p><hr>`
    );

    document.getElementById("message").value = "";
}