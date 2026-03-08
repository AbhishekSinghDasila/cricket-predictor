"""
Cricket Win Predictor - Flask Application
==========================================
Routes:
  GET  /                → Main page (Manual Mode)
  POST /predict         → Manual prediction API
  GET  /live            → Live match simulation page
  GET  /api/live-update → SSE stream for live match updates
  GET  /api/teams       → Return team lists
  GET  /api/simulate    → Simulate next ball/over for demo live mode
"""

from flask import Flask, render_template, request, jsonify, Response
import pickle
import numpy as np
import time
import json
import random
import os

app = Flask(__name__)

# ─── LOAD MODEL ───────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "cricket_model.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        artifacts = pickle.load(f)
    model      = artifacts["model"]
    le_match   = artifacts["le_match"]
    le_bat     = artifacts["le_bat"]
    le_bowl    = artifacts["le_bowl"]
    le_venue   = artifacts["le_venue"]
    feat_cols  = artifacts["feature_cols"]
    IPL_TEAMS  = artifacts["ipl_teams"]
    ODI_TEAMS  = artifacts["odi_teams"]
    VENUES     = artifacts["venues"]
    MODEL_LOADED = True
    print("✅ Model loaded successfully!")
except Exception as e:
    MODEL_LOADED = False
    print(f"❌ Model not found: {e}")
    print("   Please run: python model/train_model.py")


# ─── HELPER: BUILD FEATURE VECTOR ─────────────────────────────────────────────

def build_features(data: dict) -> np.ndarray:
    """Convert raw match state dict into model feature array."""
    match_type   = data["match_type"]          # "T20" or "ODI"
    batting_team = data["batting_team"]
    bowling_team = data["bowling_team"]
    venue        = data.get("venue", VENUES[0])
    target       = int(data["target"])
    current_score= int(data["current_score"])
    wickets      = int(data["wickets"])
    balls_bowled = int(data["balls_bowled"])

    total_balls  = 120 if match_type == "T20" else 300
    balls_remaining = max(1, total_balls - balls_bowled)
    runs_needed  = max(0, target - current_score)
    crr = (current_score / balls_bowled * 6) if balls_bowled > 0 else 0
    rrr = (runs_needed / balls_remaining * 6) if balls_remaining > 0 else 99

    wickets_in_hand = 10 - wickets
    partnership     = int(data.get("partnership", 15))
    last_5_runs     = int(data.get("last_5_overs_runs", 30))
    pressure_index  = rrr / (crr + 0.001)

    # Encode categoricals — handle unseen labels gracefully
    def safe_encode(le, val, fallback=0):
        try:
            return le.transform([val])[0]
        except ValueError:
            return fallback

    row = {
        "match_type_enc":    safe_encode(le_match, match_type),
        "batting_team_enc":  safe_encode(le_bat, batting_team),
        "bowling_team_enc":  safe_encode(le_bowl, bowling_team),
        "venue_enc":         safe_encode(le_venue, venue),
        "target":            target,
        "current_score":     current_score,
        "wickets":           wickets,
        "balls_bowled":      balls_bowled,
        "balls_remaining":   balls_remaining,
        "runs_needed":       runs_needed,
        "crr":               round(crr, 3),
        "rrr":               round(rrr, 3),
        "wickets_in_hand":   wickets_in_hand,
        "partnership":       partnership,
        "last_5_overs_runs": last_5_runs,
        "pressure_index":    round(pressure_index, 3),
    }
    return np.array([[row[c] for c in feat_cols]])


def get_prediction(data: dict) -> dict:
    """Run model and return structured prediction result."""
    features = build_features(data)
    prob = model.predict_proba(features)[0]  # [P(bowling wins), P(batting wins)]

    bat_win_prob  = round(float(prob[1]) * 100, 1)
    bowl_win_prob = round(100 - bat_win_prob, 1)

    batting_team  = data["batting_team"]
    bowling_team  = data["bowling_team"]

    # Compute derived stats for display
    total_balls  = 120 if data["match_type"] == "T20" else 300
    balls_bowled = int(data["balls_bowled"])
    balls_remaining = max(1, total_balls - balls_bowled)
    current_score= int(data["current_score"])
    target       = int(data["target"])
    wickets      = int(data["wickets"])
    runs_needed  = max(0, target - current_score)
    crr = round((current_score / balls_bowled * 6) if balls_bowled > 0 else 0, 2)
    rrr = round((runs_needed / balls_remaining * 6) if balls_remaining > 0 else 99, 2)
    overs_done   = f"{balls_bowled // 6}.{balls_bowled % 6}"

    # Momentum indicator
    if bat_win_prob > 65:
        momentum = {"team": batting_team, "strength": "Strong"}
    elif bat_win_prob > 50:
        momentum = {"team": batting_team, "strength": "Slight"}
    elif bat_win_prob < 35:
        momentum = {"team": bowling_team, "strength": "Strong"}
    else:
        momentum = {"team": bowling_team, "strength": "Slight"}

    return {
        "batting_team":     batting_team,
        "bowling_team":     bowling_team,
        "bat_win_prob":     bat_win_prob,
        "bowl_win_prob":    bowl_win_prob,
        "current_score":    current_score,
        "target":           target,
        "wickets":          wickets,
        "runs_needed":      runs_needed,
        "overs_done":       overs_done,
        "balls_remaining":  balls_remaining,
        "crr":              crr,
        "rrr":              rrr,
        "momentum":         momentum,
        "match_type":       data["match_type"],
    }


# ─── LIVE MATCH SIMULATION STATE ──────────────────────────────────────────────
# Stored in memory (resets on server restart — fine for demo)

live_match = {
    "active": False,
    "match_type": "T20",
    "batting_team": "",
    "bowling_team": "",
    "venue": "",
    "target": 0,
    "current_score": 0,
    "wickets": 0,
    "balls_bowled": 0,
    "partnership": 0,
    "last_5_overs_runs": 0,
    "history": []   # list of {"balls_bowled", "bat_win_prob", "bowl_win_prob", "score", "wickets"}
}


def simulate_next_ball(match: dict) -> dict:
    """Simulate one ball in the live match."""
    total_balls = 120 if match["match_type"] == "T20" else 300
    if match["balls_bowled"] >= total_balls - 1 or match["current_score"] >= match["target"]:
        match["active"] = False
        return match

    # Random ball outcome
    r = random.random()
    if r < 0.05:          # wide / no ball
        match["current_score"] += 1
    elif r < 0.30:        # dot ball
        pass
    elif r < 0.52:        # 1 run
        match["current_score"] += 1
        match["partnership"]   += 1
        match["balls_bowled"]  += 1
    elif r < 0.67:        # 2 runs
        match["current_score"] += 2
        match["partnership"]   += 2
        match["balls_bowled"]  += 1
    elif r < 0.74:        # 3 runs
        match["current_score"] += 3
        match["partnership"]   += 3
        match["balls_bowled"]  += 1
    elif r < 0.86:        # 4
        match["current_score"] += 4
        match["partnership"]   += 4
        match["balls_bowled"]  += 1
    elif r < 0.91:        # 6
        match["current_score"] += 6
        match["partnership"]   += 6
        match["balls_bowled"]  += 1
    else:                  # wicket
        if match["wickets"] < 9:
            match["wickets"]   += 1
            match["partnership"] = 0
        match["balls_bowled"]  += 1

    # Last 5 overs running total (approximate)
    match["last_5_overs_runs"] = match["current_score"] % 50

    # Check win/loss
    if match["current_score"] >= match["target"]:
        match["active"] = False

    return match


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    teams_data = {
        "ipl_teams": IPL_TEAMS if MODEL_LOADED else [],
        "odi_teams": ODI_TEAMS if MODEL_LOADED else [],
        "venues":    VENUES    if MODEL_LOADED else [],
    }
    return render_template("index.html", **teams_data, model_loaded=MODEL_LOADED)


@app.route("/predict", methods=["POST"])
def predict():
    """Manual prediction endpoint."""
    if not MODEL_LOADED:
        return jsonify({"error": "Model not loaded. Run train_model.py first."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    try:
        result = get_prediction(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/live")
def live():
    teams_data = {
        "ipl_teams": IPL_TEAMS if MODEL_LOADED else [],
        "odi_teams": ODI_TEAMS if MODEL_LOADED else [],
        "venues":    VENUES    if MODEL_LOADED else [],
    }
    return render_template("live.html", **teams_data, model_loaded=MODEL_LOADED)


@app.route("/api/start-live", methods=["POST"])
def start_live():
    """Initialize a new live simulated match."""
    global live_match
    data = request.get_json()
    live_match = {
        "active": True,
        "match_type":   data.get("match_type", "T20"),
        "batting_team": data.get("batting_team", ""),
        "bowling_team": data.get("bowling_team", ""),
        "venue":        data.get("venue", VENUES[0]),
        "target":       int(data.get("target", 165)),
        "current_score": 0,
        "wickets": 0,
        "balls_bowled": 0,
        "partnership": 0,
        "last_5_overs_runs": 0,
        "history": []
    }
    return jsonify({"status": "started", "match": live_match})


@app.route("/api/next-ball", methods=["POST"])
def next_ball():
    """Advance live match by one ball and return new prediction."""
    global live_match
    if not live_match["active"]:
        return jsonify({"error": "No active match. Start one first."}), 400

    live_match = simulate_next_ball(live_match)

    # Get prediction for current state
    pred = get_prediction(live_match)

    # Save to history
    live_match["history"].append({
        "balls_bowled":  live_match["balls_bowled"],
        "bat_win_prob":  pred["bat_win_prob"],
        "bowl_win_prob": pred["bowl_win_prob"],
        "score":         live_match["current_score"],
        "wickets":       live_match["wickets"],
    })

    pred["match_active"] = live_match["active"]
    pred["history"]      = live_match["history"][-60:]  # last 60 balls

    return jsonify(pred)


@app.route("/api/teams")
def get_teams():
    return jsonify({
        "ipl_teams": IPL_TEAMS,
        "odi_teams": ODI_TEAMS,
        "venues": VENUES
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "model_loaded": MODEL_LOADED})


# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
