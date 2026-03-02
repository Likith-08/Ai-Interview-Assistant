/* ==============================
   GLOBAL VARIABLES
============================== */

let currentIndex = 0;
let timeLeft = 60;
let timerInterval;

let questions = typeof questionList !== "undefined" ? questionList : [];

let mediaRecorder;
let audioChunks = [];
let currentStream = null;

let recordingIndicator;
let transcriptElement;
let recognition;

/* ==============================
   INITIALIZE
============================== */

window.addEventListener("DOMContentLoaded", function () {

    transcriptElement = document.getElementById("status");
    recordingIndicator = document.getElementById("recordingIndicator");

    if (!transcriptElement) return; // Prevent crash if not on interview page

    initializeInterview();
});

function initializeInterview() {
    updateProgress();
    startTimer();
    setupRecording();
}

/* ==============================
   TIMER
============================== */

function startTimer() {
    clearInterval(timerInterval);

    timerInterval = setInterval(() => {
        timeLeft--;

        const timeEl = document.getElementById("time");
        if (timeEl) timeEl.innerText = timeLeft;

        if (timeLeft <= 0) {
            nextQuestion();
        }
    }, 1000);
}

/* ==============================
   NEXT QUESTION
============================== */

function nextQuestion() {

    clearInterval(timerInterval);

    if (currentIndex >= questions.length - 1) {
        window.location.href = "/result";
        return;
    }

    currentIndex++;

    const questionBox = document.getElementById("questionText");
    if (questionBox) {
        questionBox.style.opacity = "0";
        setTimeout(() => {
            questionBox.innerText = questions[currentIndex];
            questionBox.style.opacity = "1";
        }, 200);
    }

    if (transcriptElement) {
        transcriptElement.innerText = "Not recorded yet";
    }

    const currentQ = document.getElementById("currentQuestion");
    if (currentQ) currentQ.innerText = currentIndex + 1;

    timeLeft = 60;

    updateProgress();
    startTimer();
}

/* ==============================
   PROGRESS BAR
============================== */

function updateProgress() {
    const progressFill = document.getElementById("progressFill");
    if (!progressFill || questions.length === 0) return;

    let percent = (currentIndex / questions.length) * 100;
    progressFill.style.width = percent + "%";
}

/* ==============================
   RECORDING
============================== */

function setupRecording() {

    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");

    if (!startBtn || !stopBtn) return;

    let recognition;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onresult = function (event) {
            let liveTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {
                liveTranscript += event.results[i][0].transcript;
            }

            if (transcriptElement)
                transcriptElement.innerText = liveTranscript;
        };
    }

    startBtn.onclick = async () => {

        try {

            currentStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            mediaRecorder = new MediaRecorder(currentStream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {

                if (recordingIndicator)
                    recordingIndicator.style.display = "none";

                if (recognition)
                    recognition.stop();

                if (transcriptElement)
                    transcriptElement.innerText = "⏳ Processing...";

                const blob = new Blob(audioChunks, { type: "audio/webm" });
                const formData = new FormData();
                formData.append("audio", blob);

                try {
                    const response = await fetch("/upload_audio", {
                        method: "POST",
                        body: formData
                    });

                    const data = await response.json();

                    if (transcriptElement) {
                        if (data.transcript && data.transcript.trim() !== "") {
                            transcriptElement.innerText = "✅ Answer Recorded Successfully";
                            transcriptElement.style.color = "#00f5d4";
                        } else {
                            transcriptElement.innerText = "❌ No speech detected";
                            transcriptElement.style.color = "#ff4d6d";
                        }
                    }

                } catch (error) {
                    console.error(error);
                    if (transcriptElement)
                        transcriptElement.innerText = "Error processing audio";
                }

                if (currentStream) {
                    currentStream.getTracks().forEach(track => track.stop());
                }

                startBtn.disabled = false;
                stopBtn.disabled = true;
            };

            mediaRecorder.start();

            if (recognition)
                recognition.start();   // 🔥 LIVE TEXT STARTS HERE

            if (recordingIndicator)
                recordingIndicator.style.display = "block";

            if (transcriptElement)
                transcriptElement.innerText = "🔴 Recording...";

            startBtn.disabled = true;
            stopBtn.disabled = false;

        } catch (error) {
            alert("Microphone access denied.");
            console.error(error);
        }
    };

    stopBtn.onclick = () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        }
    };
}

// ===== Browser Camera Start =====
async function startBrowserCamera() {
    const video = document.getElementById("video");

    if (!video) return;  // Only run on interview page

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: true
        });

        video.srcObject = stream;

    } catch (error) {
        console.error("Camera access denied:", error);
    }
}

// ===== Emotion Detection Start =====
function startEmotionDetection() {

    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");

    if (!video || !canvas) return;

    const context = canvas.getContext("2d");

    setInterval(async () => {

        if (video.videoWidth === 0) return;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        context.drawImage(video, 0, 0);

        const imageData = canvas.toDataURL("image/jpeg");

        try {
            const response = await fetch("/predict_emotion", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: imageData })
            });

            const data = await response.json();

            document.querySelector(".emotion-pill").innerText =
                "Emotion: " + data.emotion;

            document.querySelector(".confidence-pill").innerText =
                "Confidence: " + data.confidence + "%";

        } catch (error) {
            console.error("Emotion error:", error);
        }

    }, 1500);
}


// Automatically start when page loads
document.addEventListener("DOMContentLoaded", function () {
    startBrowserCamera();
    startEmotionDetection();
});
