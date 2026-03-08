"""
Cricket Win Predictor - Model Training Script
=============================================
This script:
1. Generates realistic synthetic cricket match data (IPL T20 + ODI)
2. Engineers features that matter for win prediction
3. Trains a Random Forest model
4. Saves the model + preprocessing objects for Flask to use

Run this ONCE before starting the app:
    python model/train_model.py
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

# ─── SEED FOR REPRODUCIBILITY ───────────────────────────────────────────────
np.random.seed(42)

# ─── TEAMS ───────────────────────────────────────────────────────────────────
IPL_TEAMS = [
    "Mumbai Indians", "Chennai Super Kings", "Royal Challengers Bangalore",
    "Kolkata Knight Riders", "Delhi Capitals", "Punjab Kings",
    "Rajasthan Royals", "Sunrisers Hyderabad", "Lucknow Super Giants",
    "Gujarat Titans"
]

ODI_TEAMS = [
    "India", "Australia", "England", "Pakistan", "South Africa",
    "New Zealand", "West Indies", "Sri Lanka", "Bangladesh", "Afghanistan"
]

VENUES = [
    "Wankhede Stadium", "Eden Gardens", "Chepauk", "M. Chinnaswamy Stadium",
    "Arun Jaitley Stadium", "Narendra Modi Stadium", "Rajiv Gandhi Stadium",
    "MCG", "Lords", "SCG", "Old Trafford", "Wanderers"
]

# ─── SYNTHETIC DATA GENERATION ───────────────────────────────────────────────

def generate_t20_innings_data(n_samples=8000):
    """Generate realistic T20 match snapshots."""
    records = []
    for _ in range(n_samples):
        # Pick two different teams
        teams = np.random.choice(IPL_TEAMS, 2, replace=False)
        batting_team, bowling_team = teams[0], teams[1]
        venue = np.random.choice(VENUES)

        # Target (1st innings score + 1)
        target = np.random.randint(120, 230)

        # Current over (0.1 to 19.6 = overs 1 to 19, 2nd innings)
        over = round(np.random.uniform(0.1, 19.5), 1)
        over_int = int(over)
        ball_in_over = round((over - over_int) * 10)

        # Balls bowled so far in 2nd innings
        balls_bowled = min(over_int * 6 + ball_in_over, 119)
        balls_remaining = 120 - balls_bowled

        # Wickets (more likely to fall as match progresses)
        max_wickets = min(9, int(balls_bowled / 12) + np.random.randint(0, 4))
        wickets = np.random.randint(0, min(max_wickets + 1, 10))

        # Runs scored so far (realistic based on run rate + pressure)
        # Typical T20 CRR ~7-9 RPO
        base_runs = int(balls_bowled * np.random.uniform(0.8, 1.5))
        current_score = min(base_runs, target - 1 + np.random.randint(-20, 20))
        current_score = max(0, current_score)

        # Derived features
        runs_needed = target - current_score
        crr = (current_score / balls_bowled * 6) if balls_bowled > 0 else 0
        rrr = (runs_needed / balls_remaining * 6) if balls_remaining > 0 else 99

        # Partnership runs (recent momentum)
        partnership = np.random.randint(0, min(50, current_score + 1))

        # Last 5 overs runs
        last_5_overs_runs = np.random.randint(0, 65)

        # ── LABEL: Did batting team WIN? ──
        # Win probability increases when:
        # - rrr < crr (asking rate lower than current rate)
        # - wickets in hand (10 - wickets > 3)
        # - runs needed is manageable
        wickets_in_hand = 10 - wickets
        pressure = rrr / (crr + 0.001)  # > 1 means batting team under pressure

        # Sigmoid-style win probability
        win_prob_batting = 1 / (1 + np.exp(
            0.5 * pressure
            - 0.15 * wickets_in_hand
            + 0.02 * (runs_needed - balls_remaining * 0.9)
        ))

        # Add noise
        win_prob_batting = np.clip(win_prob_batting + np.random.normal(0, 0.05), 0.05, 0.95)
        winner = 1 if np.random.random() < win_prob_batting else 0  # 1 = batting team wins

        records.append({
            "match_type": "T20",
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "venue": venue,
            "target": target,
            "current_score": current_score,
            "wickets": wickets,
            "balls_bowled": balls_bowled,
            "balls_remaining": balls_remaining,
            "runs_needed": runs_needed,
            "crr": round(crr, 2),
            "rrr": round(rrr, 2),
            "wickets_in_hand": wickets_in_hand,
            "partnership": partnership,
            "last_5_overs_runs": last_5_overs_runs,
            "pressure_index": round(pressure, 3),
            "batting_team_wins": winner
        })

    return pd.DataFrame(records)


def generate_odi_innings_data(n_samples=7000):
    """Generate realistic ODI match snapshots."""
    records = []
    for _ in range(n_samples):
        teams = np.random.choice(ODI_TEAMS, 2, replace=False)
        batting_team, bowling_team = teams[0], teams[1]
        venue = np.random.choice(VENUES)

        target = np.random.randint(200, 380)
        over = round(np.random.uniform(0.1, 49.5), 1)
        over_int = int(over)
        ball_in_over = round((over - over_int) * 10)
        balls_bowled = min(over_int * 6 + ball_in_over, 299)
        balls_remaining = 300 - balls_bowled

        max_wickets = min(9, int(balls_bowled / 30) + np.random.randint(0, 3))
        wickets = np.random.randint(0, min(max_wickets + 1, 10))

        base_runs = int(balls_bowled * np.random.uniform(0.75, 1.4))
        current_score = min(base_runs, target - 1 + np.random.randint(-30, 30))
        current_score = max(0, current_score)

        runs_needed = target - current_score
        crr = (current_score / balls_bowled * 6) if balls_bowled > 0 else 0
        rrr = (runs_needed / balls_remaining * 6) if balls_remaining > 0 else 99
        wickets_in_hand = 10 - wickets
        partnership = np.random.randint(0, min(80, current_score + 1))
        last_10_overs_runs = np.random.randint(0, 100)
        pressure = rrr / (crr + 0.001)

        win_prob_batting = 1 / (1 + np.exp(
            0.4 * pressure
            - 0.12 * wickets_in_hand
            + 0.015 * (runs_needed - balls_remaining * 0.85)
        ))
        win_prob_batting = np.clip(win_prob_batting + np.random.normal(0, 0.05), 0.05, 0.95)
        winner = 1 if np.random.random() < win_prob_batting else 0

        records.append({
            "match_type": "ODI",
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "venue": venue,
            "target": target,
            "current_score": current_score,
            "wickets": wickets,
            "balls_bowled": balls_bowled,
            "balls_remaining": balls_remaining,
            "runs_needed": runs_needed,
            "crr": round(crr, 2),
            "rrr": round(rrr, 2),
            "wickets_in_hand": wickets_in_hand,
            "partnership": partnership,
            "last_5_overs_runs": last_10_overs_runs,
            "pressure_index": round(pressure, 3),
            "batting_team_wins": winner
        })

    return pd.DataFrame(records)


# ─── MAIN TRAINING ────────────────────────────────────────────────────────────

def train_and_save():
    print("🏏 Generating synthetic match data...")
    t20_df = generate_t20_innings_data(8000)
    odi_df = generate_odi_innings_data(7000)
    df = pd.concat([t20_df, odi_df], ignore_index=True)

    print(f"   Total samples: {len(df)}")
    print(f"   Win rate (batting team): {df['batting_team_wins'].mean():.2%}")

    # ── ENCODE CATEGORICAL FEATURES ──
    le_match  = LabelEncoder()
    le_bat    = LabelEncoder()
    le_bowl   = LabelEncoder()
    le_venue  = LabelEncoder()

    all_teams = list(set(IPL_TEAMS + ODI_TEAMS))

    le_match.fit(["T20", "ODI"])
    le_bat.fit(all_teams)
    le_bowl.fit(all_teams)
    le_venue.fit(VENUES)

    df["match_type_enc"] = le_match.transform(df["match_type"])
    df["batting_team_enc"] = le_bat.transform(df["batting_team"])
    df["bowling_team_enc"] = le_bowl.transform(df["bowling_team"])
    df["venue_enc"] = le_venue.transform(df["venue"])

    # ── FEATURE COLUMNS ──
    feature_cols = [
        "match_type_enc", "batting_team_enc", "bowling_team_enc", "venue_enc",
        "target", "current_score", "wickets", "balls_bowled", "balls_remaining",
        "runs_needed", "crr", "rrr", "wickets_in_hand", "partnership",
        "last_5_overs_runs", "pressure_index"
    ]

    X = df[feature_cols]
    y = df["batting_team_wins"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("\n🤖 Training Gradient Boosting model...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"   ✅ Test Accuracy: {acc:.2%}")
    print("\n📊 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Bowling Team Wins", "Batting Team Wins"]))

    # Feature importance
    print("\n🔍 Top Features by Importance:")
    importances = pd.Series(model.feature_importances_, index=feature_cols)
    for feat, imp in importances.nlargest(8).items():
        print(f"   {feat:30s}: {imp:.3f}")

    # ── SAVE MODEL & ENCODERS ──
    os.makedirs("model", exist_ok=True)
    artifacts = {
        "model": model,
        "le_match": le_match,
        "le_bat": le_bat,
        "le_bowl": le_bowl,
        "le_venue": le_venue,
        "feature_cols": feature_cols,
        "ipl_teams": IPL_TEAMS,
        "odi_teams": ODI_TEAMS,
        "venues": VENUES
    }

    with open("model/cricket_model.pkl", "wb") as f:
        pickle.dump(artifacts, f)

    print("\n✅ Model saved to model/cricket_model.pkl")
    print("🚀 You can now run: python app.py")


if __name__ == "__main__":
    train_and_save()
