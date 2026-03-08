# 🏏 CricAI — Cricket Win Probability Predictor

A full end-to-end Machine Learning web application that predicts which cricket team will win a match, with win percentages that update dynamically as runs increase and wickets fall.

**Supports:** IPL T20 + ODI formats  
**Stack:** Python · Flask · Scikit-Learn · Chart.js · HTML/CSS/JS  
**Deployment:** Render.com (free tier)

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| **Manual Mode** | Enter any match state manually and instantly get win predictions |
| **Live Simulation Mode** | Watch win probabilities shift ball-by-ball in real-time with animated charts |
| **ML Model** | Gradient Boosting Classifier trained on 15,000 match scenarios |
| **Key Metrics** | Shows CRR, RRR, balls remaining, momentum, runs needed |
| **Beautiful UI** | Dark stadium theme with green/amber accents |

---

## 📁 Project Structure

```
cricket-predictor/
│
├── app.py                    ← Flask web server (main entry point)
│
├── model/
│   ├── train_model.py        ← ML model training script
│   └── cricket_model.pkl     ← Saved trained model (generated after training)
│
├── templates/
│   ├── index.html            ← Manual prediction page
│   └── live.html             ← Live simulation page
│
├── static/
│   ├── css/
│   │   └── style.css         ← All styles
│   └── js/
│       ├── main.js           ← Manual mode logic
│       └── live.js           ← Live simulation logic + Chart.js
│
├── requirements.txt          ← Python packages
├── render.yaml               ← Render deployment config
└── README.md                 ← This file
```

---

## 🚀 How to Run Locally (Step-by-Step for Beginners)

### Step 1: Install Python
Make sure you have Python 3.9+ installed.  
Download from: https://www.python.org/downloads/

### Step 2: Open Terminal / Command Prompt
- Windows: Press `Win + R`, type `cmd`, press Enter
- Mac/Linux: Open Terminal

### Step 3: Navigate to the project folder
```bash
cd path/to/cricket-predictor
```

### Step 4: Create a virtual environment (recommended)
```bash
# Create it
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```
You'll see `(venv)` appear in your terminal — that's correct!

### Step 5: Install dependencies
```bash
pip install -r requirements.txt
```
This installs Flask, Scikit-Learn, NumPy, Pandas, and Gunicorn.  
Wait for it to finish (~1-2 minutes).

### Step 6: Train the ML model (IMPORTANT — do this once!)
```bash
python model/train_model.py
```
You'll see output like:
```
🏏 Generating synthetic match data...
🤖 Training Gradient Boosting model...
✅ Test Accuracy: 69.57%
✅ Model saved to model/cricket_model.pkl
```

### Step 7: Start the web app
```bash
python app.py
```
You'll see: `Running on http://0.0.0.0:5000`

### Step 8: Open in browser
Go to: **http://localhost:5000**

---

## 🧠 How the ML Model Works

### What data was used?
The model was trained on **15,000 synthetic but realistic match scenarios** covering IPL T20 and ODI formats. Each scenario represents a snapshot of a match at a particular ball, with realistic statistics.

### What features does the model use?
| Feature | Why it matters |
|---------|----------------|
| `pressure_index` | RRR ÷ CRR — how much pressure is on the batting team |
| `rrr` | Required Run Rate — runs needed per over |
| `crr` | Current Run Rate — runs scored per over so far |
| `runs_needed` | How many runs to win |
| `wickets_in_hand` | Remaining batters (10 - wickets fallen) |
| `balls_remaining` | Overs left to bat |
| `partnership` | Current batting partnership runs |
| `last_5_overs_runs` | Recent scoring momentum |
| `target` | First innings total to chase |
| `match_type` | T20 vs ODI (different scoring patterns) |
| `batting/bowling team` | Team quality encoded |
| `venue` | Home ground advantage |

### What algorithm?
**Gradient Boosting Classifier** (from Scikit-Learn)
- Builds many decision trees sequentially
- Each tree corrects errors of the previous one
- Outputs a probability between 0–100% for each team
- Achieves ~70% accuracy on test data

### Why 70% accuracy?
Cricket is inherently unpredictable! Even the best pro analysts can't predict with 100% certainty. 70% is strong for real-time match prediction, especially for middle-overs scenarios.

---


## 🔮 Future Improvements
- Connect to real CricAPI / Cricbuzz API for actual live match data
- Add player-level features (top scorer, bowling strike rate)
- Historical H2H team records
- More match formats (Test, T10)
- Mobile app version

---

## 📜 License
MIT License — free to use and modify.

---

Built with ❤️ using Python, Flask, Scikit-Learn, and Chart.js
