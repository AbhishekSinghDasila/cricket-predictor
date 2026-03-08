/**
 * CricAI – Manual Prediction Page JS
 * Handles form interactions, API calls, and result rendering
 */

// ── TEAM LISTS ────────────────────────────────────────────────
// IPL_TEAMS, ODI_TEAMS, VENUES are injected from Flask template

// ── STATE ─────────────────────────────────────────────────────
let currentFormat = "T20";

// ── OVERS → BALLS CONVERSION ──────────────────────────────────
function oversToBalls(overs) {
  const intPart  = Math.floor(overs);
  const ballPart = Math.round((overs - intPart) * 10);
  return intPart * 6 + Math.min(ballPart, 5);
}

// ── FORMAT TOGGLE ─────────────────────────────────────────────
function setupFormatToggle() {
  const btnT20 = document.getElementById("btnT20");
  const btnODI = document.getElementById("btnODI");
  const matchTypeInput = document.getElementById("match_type");
  const batSel  = document.getElementById("batting_team");
  const bowlSel = document.getElementById("bowling_team");

  function populateTeams(format) {
    const teams = format === "T20" ? IPL_TEAMS : ODI_TEAMS;
    [batSel, bowlSel].forEach((sel, idx) => {
      const prev = sel.value;
      sel.innerHTML = "";
      teams.forEach((t, i) => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        if (teams.includes(prev) && t === prev) opt.selected = true;
        else if (!teams.includes(prev) && i === idx) opt.selected = true;
        sel.appendChild(opt);
      });
    });
  }

  [btnT20, btnODI].forEach(btn => {
    btn.addEventListener("click", () => {
      [btnT20, btnODI].forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFormat = btn.dataset.val;
      matchTypeInput.value = currentFormat;
      populateTeams(currentFormat);

      // Adjust overs label hints
      const overs = document.getElementById("overs_done");
      overs.max = currentFormat === "T20" ? 20 : 50;
      overs.value = currentFormat === "T20" ? "10.0" : "25.0";

      const target = document.getElementById("target");
      target.value = currentFormat === "T20" ? "165" : "275";
    });
  });
}

// ── FORM SUBMIT ───────────────────────────────────────────────
function setupForm() {
  const form = document.getElementById("predictForm");
  const btn  = document.getElementById("submitBtn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Validate teams
    const batTeam  = document.getElementById("batting_team").value;
    const bowlTeam = document.getElementById("bowling_team").value;
    if (batTeam === bowlTeam) {
      showError("Batting and Bowling teams must be different!");
      return;
    }

    const overs      = parseFloat(document.getElementById("overs_done").value);
    const balls      = oversToBalls(overs);
    const matchType  = document.getElementById("match_type").value;
    const totalBalls = matchType === "T20" ? 120 : 300;

    if (balls >= totalBalls) {
      showError("Overs done exceeds match length!");
      return;
    }

    const payload = {
      match_type:       matchType,
      batting_team:     batTeam,
      bowling_team:     bowlTeam,
      venue:            document.getElementById("venue").value,
      target:           document.getElementById("target").value,
      current_score:    document.getElementById("current_score").value,
      wickets:          document.getElementById("wickets").value,
      balls_bowled:     balls,
      partnership:      document.getElementById("partnership").value,
      last_5_overs_runs:document.getElementById("last_5_overs_runs").value,
    };

    btn.disabled = true;
    btn.innerHTML = `<span class="spin">⚡</span> Predicting...`;

    try {
      const resp = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (data.error) {
        showError(data.error);
      } else {
        renderResult(data);
      }
    } catch (err) {
      showError("Network error. Please try again.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span class="btn-icon">⚡</span> Predict Win Probability`;
    }
  });
}

// ── RENDER RESULT ─────────────────────────────────────────────
function renderResult(d) {
  const placeholder = document.getElementById("placeholder");
  const card        = document.getElementById("resultCard");

  placeholder.classList.add("hidden");
  card.classList.remove("hidden");
  card.classList.add("fade-in");

  // Header
  document.getElementById("resultFormat").textContent = d.match_type;
  document.getElementById("resultVenue").textContent  = document.getElementById("venue").value;

  // Team names
  document.getElementById("batTeamName").textContent  = d.batting_team;
  document.getElementById("bowlTeamName").textContent = d.bowling_team;

  // Bars + numbers — animate
  setTimeout(() => {
    document.getElementById("batBar").style.width   = d.bat_win_prob + "%";
    document.getElementById("bowlBar").style.width  = d.bowl_win_prob + "%";
    document.getElementById("batProb").textContent  = d.bat_win_prob + "%";
    document.getElementById("bowlProb").textContent = d.bowl_win_prob + "%";
  }, 50);

  // Stats
  document.getElementById("statScore").textContent    = `${d.current_score}/${d.wickets}`;
  document.getElementById("statNeeded").textContent   = `${d.runs_needed}`;
  document.getElementById("statBalls").textContent    = `${d.balls_remaining}`;
  document.getElementById("statCRR").textContent      = d.crr.toFixed(2);
  document.getElementById("statRRR").textContent      = d.rrr >= 99 ? "N/A" : d.rrr.toFixed(2);
  document.getElementById("statMomentum").textContent = `${d.momentum.team.split(" ")[0]} (${d.momentum.strength})`;

  // Verdict
  const winner = d.bat_win_prob > d.bowl_win_prob ? d.batting_team : d.bowling_team;
  const prob   = Math.max(d.bat_win_prob, d.bowl_win_prob);
  document.getElementById("verdictTeam").textContent = `${winner} (${prob}%)`;
}

// ── ERROR TOAST ───────────────────────────────────────────────
function showError(msg) {
  const existing = document.querySelector(".error-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "error-toast";
  toast.textContent = "⚠️ " + msg;
  toast.style.cssText = `
    position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%);
    background: rgba(255,82,82,0.2); border: 1px solid rgba(255,82,82,0.4);
    color: #ff7070; padding: 0.7rem 1.4rem; border-radius: 100px;
    font-size: 0.9rem; font-weight: 600; z-index: 999;
    animation: fadeIn 0.3s ease;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupFormatToggle();
  setupForm();
});
