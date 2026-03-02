# 🤖 AI Interview Assistant

An AI-powered mock interview web application that analyzes candidate performance using emotion detection, confidence scoring, communication evaluation, and generates a structured PDF performance report.

This system helps users practice interviews and receive intelligent feedback to improve their communication skills and confidence.

---

# 📌 What This Project Does

AI Interview Assistant simulates a real interview environment and evaluates:

- 🎯 Communication quality
- 😊 Facial emotion during interview
- 📊 Confidence percentage
- 🧠 AI-generated performance feedback
- 📄 Downloadable interview performance report

The system stores interview results and provides structured improvement suggestions.

---

# 🏗️ System Architecture Overview

The application follows this flow:

1. User registers and logs in
2. User selects interview category
3. Interview questions are displayed
4. User answers questions
5. Emotion detection runs in background
6. Emotion history is collected
7. Final score is calculated
8. Dominant emotion is determined
9. AI feedback is generated
10. Result is stored in database
11. PDF report is generated

---

# 🛠️ Technologies Used

## Backend
- Python
- Flask
- SQLite3
- ReportLab (PDF generation)
- Collections (Counter)
- Session management

## Frontend
- HTML
- CSS
- JavaScript

## AI / Machine Learning
- CNN-based Emotion Detection Model
- OpenCV (for frame processing)
- NumPy

---

# 🧠 Core Functionalities Explained

## 1️⃣ User Authentication System

- Secure user registration
- Login validation
- Session-based authentication
- User-specific interview history

---

## 2️⃣ Interview Answer Tracking

- Answers are temporarily stored using Flask sessions:
  
  ```python
  session.get("answers", [])
  ```

- After interview completion, answers are saved into database.
- Session data is cleared after processing.

---

## 3️⃣ Emotion Detection Logic

- Emotion is detected frame-by-frame.
- All detected emotions are stored in:

  ```python
  emotion_history
  ```

- Final dominant emotion is calculated using:

  ```python
  Counter(emotion_history).most_common(1)
  ```

- Emotion history is cleared after result generation.

### Possible Emotions:
- Happy
- Sad
- Fear
- Angry
- Surprise
- Neutral

---

## 4️⃣ Score Calculation System

Final score is calculated based on:

- Communication score
- Confidence score
- Emotional stability

### Grade Classification:

| Score Range | Grade |
|-------------|--------|
| > 80        | Excellent |
| > 60        | Good |
| <= 60       | Needs Improvement |

---

## 5️⃣ AI Feedback Logic

Feedback is generated using two layers:

### A. Score-Based Feedback
- High score → Strong performance feedback
- Medium score → Improvement suggestions
- Low score → Confidence improvement suggestions

### B. Emotion-Based Feedback
- Sad / Fear → Suggest relaxation and confidence
- Angry → Suggest emotional control
- Neutral → Suggest expressive engagement
- Happy / Surprise → Positive reinforcement

Final feedback combines both evaluations.

---

## 6️⃣ Database Design

SQLite database is used.

### Table: users
Stores:
- id
- username
- password

### Table: interviews
Stores:
- user_id
- score
- emotion
- confidence
- date

Data is inserted using:

```python
INSERT INTO interviews (user_id, score, emotion, confidence)
```

---

## 7️⃣ PDF Report Generation

PDF is generated using ReportLab.

The report includes:

- Candidate name
- Date and time
- Final score
- Dominant emotion
- Confidence percentage
- AI performance feedback
- Interview answers summary

The structure:
- Title section
- Summary table
- AI feedback section
- Answers list

---

# 📂 Project Structure

```
AI-INTERVIEW-ASSISTANT/
│
├── model/                 # Emotion detection model files
├── static/                # CSS, JS
├── templates/             # HTML files
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── interview.html
│   ├── result.html
│   └── select_category.html
│
├── app.py                 # Main Flask application
├── database.db            # SQLite database
├── requirements.txt       # Dependencies
├── .gitignore
└── README.md
```

---

# ⚙️ How To Run Locally

## 1️⃣ Clone Repository

```
git clone https://github.com/yourusername/ai-interview-assistant.git
cd ai-interview-assistant
```

## 2️⃣ Create Virtual Environment

```
python -m venv venv
```

Activate:

Windows:
```
venv\Scripts\activate
```

Mac/Linux:
```
source venv/bin/activate
```

## 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

## 4️⃣ Run Application

```
python app.py
```

Open:
```
http://127.0.0.1:5000
```

---

# 🚀 Deployment Notes

For production deployment:

- Use gunicorn
- Add Procfile
- Set environment variables
- Disable debug mode
- Use production secret key

Example Procfile:

```
web: gunicorn app:app
```

---

# 🔐 Production Improvements

- Use environment variable for SECRET_KEY
- Use PostgreSQL instead of SQLite for scaling
- Add password hashing
- Use HTTPS in production
- Add rate limiting

---

# 🎯 Future Enhancements

- Speech-to-text analysis
- Real-time emotion graph
- Resume-based dynamic question generation
- Admin analytics dashboard
- Multi-language support
- Cloud database integration

---

# 👨‍💻 Author

Likith Machireddy  
B.Tech CSE  
Aspiring Python Full Stack Developer  

---

# ⭐ If You Like This Project

Give it a star on GitHub ⭐
