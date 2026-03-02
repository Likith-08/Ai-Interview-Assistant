from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, Response, request, jsonify, send_file, redirect, url_for, session
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import cv2
import whisper
import os
import subprocess
import sqlite3
import base64
import numpy as np
from datetime import datetime
from collections import Counter

# ===== ReportLab =====
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
app = Flask(__name__)
app.secret_key = "super_secret_key_123"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        score REAL,
        emotion TEXT,
        confidence REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= MODELS =================

whisper_model = whisper.load_model("base")

# 🔥 FIRST DEFINE THE CLASS
class EmotionCNN(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv_layers = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )

        self.fc_layers = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 6 * 6, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 7)
        )

    def forward(self, x):
        return self.fc_layers(self.conv_layers(x))


# 🔥 THEN CREATE MODEL
model = EmotionCNN()
model.load_state_dict(torch.load("model/face_emotion_model.pth", map_location="cpu"))
model.eval()

# ===== IMAGE TRANSFORM =====
transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((48, 48)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

# ===== EMOTION LABELS =====
emotion_labels = [
    'Angry',
    'Disgust',
    'Fear',
    'Happy',
    'Sad',
    'Surprise',
    'Neutral'
]

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)


latest_emotion = "Neutral"
latest_confidence = 0.0
emotion_history=[]

questions = [
    "Tell me about yourself.",
    "Why should we hire you?",
    "Describe a challenging project you worked on.",
    "What are your strengths?",
    "What is your biggest weakness?",
    "Explain a time you worked in a team.",
    "How do you handle pressure?",
    "Describe a failure and what you learned.",
    "What technologies are you strongest in?",
    "Where do you see yourself in 5 years?"
]

python_questions = [
    "What is Python?",
    "Explain list vs tuple.",
    "What is OOPS in Python?",
    "What are decorators?",
    "What is exception handling?",
    "What is Flask?",
    "What is a generator?",
    "Explain lambda function.",
    "What is inheritance?",
    "What is multithreading?"
]

dsa_questions = [
    "What is time complexity?",
    "Explain Big-O notation.",
    "What is a stack?",
    "What is recursion?",
    "What is binary search?",
    "Difference between array and linked list?",
    "What is a queue?",
    "Explain BFS and DFS.",
    "What is dynamic programming?",
    "What is hashing?"
]

hr_questions = [
    "Tell me about yourself.",
    "Why should we hire you?",
    "What are your strengths?",
    "What is your weakness?",
    "Where do you see yourself in 5 years?",
    "Describe a challenge you faced.",
    "What motivates you?",
    "How do you handle pressure?",
    "Why our company?",
    "Explain your final year project."
]

sql_questions = [
    "What is SQL?",
    "What is JOIN?",
    "Difference between WHERE and HAVING?",
    "What is normalization?",
    "What is indexing?",
    "What is GROUP BY?",
    "What is a primary key?",
    "Difference between DELETE and TRUNCATE?",
    "What is subquery?",
    "What is UNION?"
]

# ================= AUTH =================
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template("register.html", error="Username already exists")

        cursor.execute("INSERT INTO users (username,password) VALUES (?,?)",(username,password))
        conn.commit()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?",(username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2],password):
            session.clear()
            session["user"] = user[1]
            session["role"] = user[3]  
            session["answers"] = []
            if user[3] == "admin":
                return redirect(url_for("admin_panel"))
            else:
                return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================= DASHBOARD =================
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username=?", (session["user"],))
    user_id = cursor.fetchone()[0]

    cursor.execute("SELECT score FROM interviews WHERE user_id=?", (user_id,))
    scores = [r[0] for r in cursor.fetchall()]
    conn.close()

    avg_score = round(sum(scores)/len(scores),2) if scores else 0

    return render_template(
        "dashboard.html",
        avg_score=avg_score,
        total_interviews=len(scores),
        last_score=scores[-1] if scores else 0,
        best_score=max(scores) if scores else 0,
        worst_score=min(scores) if scores else 0,
        performance_level="Excellent" if avg_score >= 80 else "Good" if avg_score >= 60 else "Needs Improvement",
        score_history=scores
    )

# ================= INTERVIEW =================
@app.route("/interview", methods=["GET", "POST"])
def interview():

    if "user" not in session:
        return redirect(url_for("login"))

    global interview_data
    interview_data = {"answers": [], "emotions": [], "confidences": []}

    if request.method == "POST":

        category = request.form.get("category")

        if category == "python":
            selected_questions = python_questions
        elif category == "dsa":
            selected_questions = dsa_questions
        elif category == "hr":
            selected_questions = hr_questions
        elif category == "sql":
            selected_questions = sql_questions
        else:
            selected_questions = []

        session["questions"] = selected_questions

        return render_template(
            "interview.html",
            emotion=latest_emotion,
            confidence=latest_confidence,
            questions=selected_questions
        )

    return render_template("select_category.html")

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        audio = request.files.get("audio")

        if not audio:
            return jsonify({"transcript": "No audio received"})

        webm_path = "temp_audio.webm"
        wav_path = "temp_audio.wav"

        audio.save(webm_path)

        # Convert to wav
        subprocess.run([
            r"C:\ffmpeg\bin\ffmpeg.exe",
            "-y",
            "-i", webm_path,
            "-ar", "16000",
            "-ac", "1",
            "-af","volume=2.0",
            wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        result = whisper_model.transcribe(
            wav_path,
            fp16=False,
            language="en",
            temperature=0,
        )

        # Check file size
        if os.path.getsize(wav_path) < 5000:
            return jsonify({"transcript": "Audio too short. Speak clearly."})

        result = whisper_model.transcribe(wav_path, fp16=False)
        transcript = result.get("text", "").strip()

        if transcript == "":
            transcript = "No speech detected. Please speak louder."

        # Save answers
        answers = session.get("answers", [])
        answers.append(transcript)
        session["answers"] = answers

        os.remove(webm_path)
        os.remove(wav_path)

        return jsonify({"transcript": transcript})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"transcript": "Audio processing error"})

# ================= RESULT =================
@app.route("/result")
def result():
    final_emotion = "Neutral"
    if "user" not in session:
        return redirect(url_for("login"))

    answers = session.get("answers", [])

    final_score = min(100, len(" ".join(answers)) * 2)  # simple scoring logic
    confidence = final_score

    grade = "Excellent" if final_score >= 80 else \
            "Good" if final_score >= 60 else \
            "Needs Improvement"
    
    # ===== AI FEEDBACK LOGIC =====
    if final_score >= 80:
        feedback = "Excellent performance! You demonstrated strong confidence and good communication skills during the interview."
    elif final_score >= 60:
        feedback = "Good performance. You showed decent confidence, but there is room for improvement in clarity and consistency."
    else:
        feedback = "Your confidence level was lower during the interview. Try to speak more clearly and maintain steady emotional control."

    # Add emotion-based suggestion
    if final_emotion in ["Sad", "Fear"]:
        feedback += " Try to maintain a more positive and confident facial expression."
    elif final_emotion == "Angry":
        feedback += " Maintain a calm and composed expression during interviews."
    elif final_emotion == "Neutral":
        feedback += " Adding more expressive engagement can improve your presence."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (session["user"],))
    user_id = cursor.fetchone()[0]

    from collections import Counter

    if emotion_history:
        emotion_counts = Counter(emotion_history)
        final_emotion = emotion_counts.most_common(1)[0][0]
    else:
        emotion_counts = {"Neutral": 1}
        final_emotion = "Neutral"
    emotion_history.clear()

    # ===== AI Feedback Logic =====
    feedback = ""

    if final_emotion in ["Sad", "Fear"]:
        feedback = "You appeared slightly nervous. Try to relax and maintain confident expressions."
    elif final_emotion in ["Happy", "Surprise"]:
        feedback = "Great energy and positive presence! Keep maintaining this confidence."
    elif final_emotion == "Angry":
        feedback = "Maintain a calm and composed expression during interviews."
    elif final_emotion == "Neutral":
        feedback = "Adding more expressive engagement can improve your overall presence."
    else:
        feedback = "Good effort. Keep improving your communication and confidence."
    session["feedback"] = feedback

    cursor.execute("""
        INSERT INTO interviews (user_id, score, emotion, confidence)
        VALUES (?, ?, ?, ?)
      """, (user_id, final_score, final_emotion, confidence))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        emotion=final_emotion,
        confidence=confidence,
        final_score=final_score,
        grade=grade,
        answers=answers,
        emotion_counts=emotion_counts,
        answer_score=final_score,
        emotion_score=confidence,
        feedback=feedback
    )

# ================= PDF =================
@app.route("/download_report")
def download_report():
    if "user" not in session:
        return redirect(url_for("login"))

    file_path = "report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

        # ===== Extra Report Details =====
    date_now = datetime.now().strftime("%d %B %Y - %I:%M %p")
    candidate_name = session.get("user", "Candidate")
    answers_list = session.get("answers", [])
    total_questions = len(answers_list)

    # Performance Level Logic
    final_score = session.get("latest_report", {}).get("final_score", 0)

    if final_score >= 80:
        performance = "Top Performer"
    elif final_score >= 60:
        performance = "Strong Candidate"
    else:
        performance = "Needs Practice"

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor("#0f766e"),
        spaceAfter=20,
        alignment=1  # center
    )

    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        textColor=colors.HexColor("#065f46"),
        spaceAfter=10
    )

    normal_style = styles['Normal']

    elements.append(Paragraph("AI Interview Report",title_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Candidate: {candidate_name}", styles["Normal"]))
    elements.append(Paragraph(f"Date: {date_now}", styles["Normal"]))
    elements.append(Paragraph(f"Performance Level: {performance}", styles["Normal"]))
    elements.append(Paragraph(f"Total Questions Answered: {total_questions}", styles["Normal"]))
    elements.append(Spacer(1, 20))

        # Connect DB
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get user id
    cursor.execute("SELECT id FROM users WHERE username=?", (session["user"],))
    user_id = cursor.fetchone()[0]

    # Get latest interview only
    cursor.execute("""
        SELECT score, emotion, confidence, date
        FROM interviews
        WHERE user_id=?
        ORDER BY date DESC
        LIMIT 1
    """, (user_id,))

    latest = cursor.fetchone()

    conn.close()

    if latest:

        elements.append(Paragraph("Interview Summary:", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        data = [
            ["Final Score", str(latest[0])],
            ["Dominant Emotion", latest[1]],
            ["Confidence", f"{latest[2]}%"],
            ["Date", latest[3]]
        ]

        table = Table(data, colWidths=[180, 250])

        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 25))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 20))
        
        # ===== AI Feedback Section =====
        feedback = session.get("feedback", "No feedback available.")

        elements.append(Paragraph("AI Performance Feedback", styles["Heading2"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(feedback, styles["Normal"]))
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 20))

        for i, ans in enumerate(session.get("answers", []), start=1):
            elements.append(Paragraph(f"Q{i} Answer: {ans}", styles["Normal"]))
            elements.append(Spacer(1, 5))
    else:
        elements.append(Paragraph("No interview data found.", styles["Normal"]))

    print("Session answers at download:", session.get("answers"))

    doc.build(elements)
    return send_file(file_path, as_attachment=True)

@app.route("/admin")
def admin_panel():

    if "user" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("interview"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM interviews")
    total_interviews = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(score) FROM interviews")
    avg_score = cursor.fetchone()[0]
    avg_score = round(avg_score, 2) if avg_score else 0

    cursor.execute("""
        SELECT emotion, COUNT(*)
        FROM interviews
        GROUP BY emotion
    """)
    emotions = cursor.fetchall()

    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        total_users=total_users,
        total_interviews=total_interviews,
        avg_score=avg_score,
        emotions=emotions
    )

@app.route("/admin/user/<int:user_id>")
def admin_user_history(user_id):

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT score, emotion, confidence, date
        FROM interviews
        WHERE user_id = ?
        ORDER BY date DESC
    """, (user_id,))

    interviews = cursor.fetchall()

    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    username = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_user_history.html",
        interviews=interviews,
        username=username
    )

@app.route("/predict_emotion", methods=["POST"])
def predict_emotion():
    try:
        data = request.json["image"]

        # Decode base64 image
        image_data = data.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"emotion": "Error", "confidence": 0})

        # -----------------------------
        # ✅ STEP 1: Resize frame
        # -----------------------------
        frame = cv2.resize(frame, (640, 480))

        # -----------------------------
        # ✅ STEP 2: Improve brightness
        # -----------------------------
        alpha = 1.3   # contrast control
        beta = 30     # brightness control
        frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # -----------------------------
        # ✅ STEP 3: Improve contrast
        # -----------------------------
        gray = cv2.equalizeHist(gray)

        # Slight blur to reduce noise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # -----------------------------
        # ✅ STEP 4: Better face detection
        # -----------------------------
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(30, 30)
        )

        if len(faces) == 0:
            return jsonify({"emotion": "No Face", "confidence": 0})

        # Take first detected face
        (x, y, w, h) = faces[0]
        face = gray[y:y+h, x:x+w]

        face = cv2.resize(face, (48, 48))
        face = transform(face).unsqueeze(0)

        with torch.no_grad():
            output = model(face)
            probabilities = torch.softmax(output, dim=1)
            confidence, predicted = torch.max(probabilities, 1)

        emotion = emotion_labels[predicted.item()]
        confidence = round(confidence.item() * 100, 2)
        print(f"Detected Emotion: {emotion} | Confidence: {confidence}%")


        return jsonify({
            "emotion": emotion,
            "confidence": confidence
        })

    except Exception as e:
        print("Emotion Error:", e)
        return jsonify({"emotion": "Error", "confidence": 0})

if __name__ == "__main__":
    init_db() 
    app.run()