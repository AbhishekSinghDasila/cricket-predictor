/**
 * CricAI – Live Simulation Page JS
 * Handles: match setup, ball-by-ball simulation loop,
 *          Chart.js probability graph, ball log, controls
 */

// ── STATE ─────────────────────────────────────────────────────
let simInterval  = null;
let simSpeed     = 800;    // ms between balls
let isPaused     = false;
let chartInstance = null;
let matchActive  = false;

// ── CHART SETUP ───────────────────────────────────────────────
function initChart(batLabel, bowlLabel) {
  const ctx = document.getElementById("probChart").getContext("2d");

  if (chartInstance) {
    chartInstance.destroy();
  }

  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: batLabel,
          data: [],
          borderColor: "#00e676",
          backgroundColor: "rgba(0, 230, 118, 0.08)",
          borderWidth: 2.5,
          pointRadius: 0,
          fill: true,
          tension: 0.4,
        },
        {
          label: bowlLabel,
          data: [],
          borderColor: "#ffab00",
          backgroundColor: "rgba(255, 171, 0, 0.06)",
          borderWidth: 2.5,
          pointRadius: 0,
          fill: true,
          tension: 0.4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 }, // disable animation for real-time feel
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(10,15,13,0.9)",
          borderColor: "rgba(0,230,118,0.2)",
          borderWidth: 1,
          titleColor: "#f0f4f1",
          bodyColor: "#8fa898",
          callbacks: {
            title: (items) => `Ball ${items[0].label}`,
            label: (item) => `${item.dataset.label}: ${item.parsed.y}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)", drawBorder: false },
          ticks: {
            color: "#4d6257",
            font: { family: "'JetBrains Mono'", size: 10 },
            maxTicksLimit: 12
          }
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: "rgba(255,255,255,0.04)", drawBorder: false },
          ticks: {
            color: "#4d6257",
            font: { family: "'JetBrains Mono'", size: 10 },
            callback: (v) => v + "%",
            stepSize: 20,
          }
        }
      }
    }
  });
}

function updateChart(ballNum, batProb, bowlProb) {
  chartInstance.data.labels.push(ballNum);
  chartInstance.data.datasets[0].data.push(batProb);
  chartInstance.data.datasets[1].data.push(bowlProb);
  chartInstance.update();
}

// ── BALL LOG ──────────────────────────────────────────────────
function addBallEntry(data, prev) {
  const log = document.getElementById("ballLog");
  const scoreChange = data.current_score - (prev ? prev.current_score : 0);
  const wicketChange = data.wickets - (prev ? prev.wickets : 0);

  const entry = document.createElement("div");
  entry.className = "ball-entry";
  let label = "";
  if (wicketChange > 0) {
    entry.classList.add("wicket");
    label = `W ${data.overs_done}`;
  } else if (scoreChange === 6) {
    entry.classList.add("six");
    label = `6 ${data.overs_done}`;
  } else if (scoreChange === 4) {
    entry.classList.add("four");
    label = `4 ${data.overs_done}`;
  } else {
    label = `${scoreChange} ${data.overs_done}`;
  }
  entry.textContent = label;
  log.prepend(entry);
}

// ── UPDATE SCOREBOARD ─────────────────────────────────────────
let prevData = null;

function updateScoreboard(d) {
  document.getElementById("lv_batting_team").textContent = d.batting_team;
  document.getElementById("lv_score").textContent = `${d.current_score}/${d.wickets}`;
  document.getElementById("lv_overs").textContent  = `${d.overs_done} ov`;
  document.getElementById("lv_target").textContent  = d.target;
  document.getElementById("lv_needed").textContent  = d.runs_needed;
  document.getElementById("lv_balls").textContent   = d.balls_remaining;
  document.getElementById("lv_crr").textContent     = d.crr.toFixed(2);
  document.getElementById("lv_rrr").textContent     = d.rrr >= 99 ? "N/A" : d.rrr.toFixed(2);
}

function updateProbBars(d) {
  const batBar   = document.getElementById("ltp_bat");
  const bowlBar  = document.getElementById("ltp_bowl");
  const batLabel = document.getElementById("ltp_bat_label");
  const bowlLabel= document.getElementById("ltp_bowl_label");

  batBar.style.width   = d.bat_win_prob + "%";
  bowlBar.style.width  = d.bowl_win_prob + "%";
  batLabel.textContent = d.bat_win_prob + "%";
  bowlLabel.textContent= d.bowl_win_prob + "%";

  document.getElementById("lv_bat_name").textContent  = d.batting_team;
  document.getElementById("lv_bowl_name").textContent = d.bowling_team;
  document.getElementById("legend_bat").textContent   = d.batting_team;
  document.getElementById("legend_bowl").textContent  = d.bowling_team;
}

// ── FETCH NEXT BALL ───────────────────────────────────────────
async function fetchNextBall() {
  if (isPaused) return;

  try {
    const resp = await fetch("/api/next-ball", { method: "POST" });
    const data = await resp.json();

    if (data.error) {
      console.error(data.error);
      stopSim();
      return;
    }

    updateScoreboard(data);
    updateProbBars(data);
    addBallEntry(data, prevData);

    const ballNum = data.history.length;
    updateChart(ballNum, data.bat_win_prob, data.bowl_win_prob);

    prevData = data;

    if (!data.match_active) {
      stopSim(data);
    }
  } catch (err) {
    console.error("Fetch error:", err);
    stopSim();
  }
}

// ── START / STOP SIM ──────────────────────────────────────────
function startSim() {
  if (simInterval) clearInterval(simInterval);
  isPaused = false;
  matchActive = true;
  document.getElementById("pauseBtn").textContent = "⏸ Pause";

  // Set status tag
  const tag = document.getElementById("matchStatusTag");
  tag.textContent = "LIVE";
  tag.className = "match-status-tag live-tag";

  simInterval = setInterval(fetchNextBall, simSpeed);
}

function stopSim(data) {
  if (simInterval) clearInterval(simInterval);
  simInterval = null;
  matchActive = false;

  const tag = document.getElementById("matchStatusTag");
  tag.className = "match-status-tag done-tag";

  if (data) {
    const winner = data.bat_win_prob > data.bowl_win_prob
      ? data.batting_team
      : data.bowling_team;

    const scoreOrWickets = data.current_score >= data.target
      ? `${data.batting_team} won!`
      : `${data.bowling_team} won! (all out / overs up)`;

    tag.textContent = "FINISHED";
    showToast(`🏆 ${scoreOrWickets}`, "green");
  }
}

function showToast(msg, color = "green") {
  const existing = document.querySelector(".live-toast");
  if (existing) existing.remove();
  const c = color === "green" ? "#00e676" : "#ff5252";
  const bg = color === "green" ? "rgba(0,230,118,0.15)" : "rgba(255,82,82,0.15)";
  const border = color === "green" ? "rgba(0,230,118,0.3)" : "rgba(255,82,82,0.3)";

  const toast = document.createElement("div");
  toast.className = "live-toast";
  toast.textContent = msg;
  toast.style.cssText = `
    position: fixed; top: 5rem; left: 50%; transform: translateX(-50%);
    background: ${bg}; border: 1px solid ${border};
    color: ${c}; padding: 0.8rem 1.6rem; border-radius: 100px;
    font-size: 1rem; font-weight: 700; z-index: 999;
    animation: fadeIn 0.3s ease;
    font-family: 'Bebas Neue', cursive; letter-spacing: 2px;
  `;
  document.body.appendChild(toast);
}

// ── SETUP FORM ────────────────────────────────────────────────
function oversToBalls(overs) {
  const intPart  = Math.floor(overs);
  const ballPart = Math.round((overs - intPart) * 10);
  return intPart * 6 + Math.min(ballPart, 5);
}

function setupFormatToggle() {
  const btnT20 = document.getElementById("lbtnT20");
  const btnODI = document.getElementById("lbtnODI");
  const matchTypeInput = document.getElementById("l_match_type");
  const batSel  = document.getElementById("l_batting_team");
  const bowlSel = document.getElementById("l_bowling_team");

  function populateTeams(format) {
    const teams = format === "T20" ? IPL_TEAMS : ODI_TEAMS;
    [batSel, bowlSel].forEach((sel, idx) => {
      sel.innerHTML = "";
      teams.forEach((t, i) => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        if (i === idx) opt.selected = true;
        sel.appendChild(opt);
      });
    });
  }

  [btnT20, btnODI].forEach(btn => {
    btn.addEventListener("click", () => {
      [btnT20, btnODI].forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      matchTypeInput.value = btn.dataset.val;
      populateTeams(btn.dataset.val);
      const target = document.getElementById("l_target");
      target.value = btn.dataset.val === "T20" ? "165" : "275";
    });
  });
}

function setupSpeedButtons() {
  const btns = document.querySelectorAll(".speed-btn");
  const inp  = document.getElementById("sim_speed");
  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      btns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      simSpeed = parseInt(btn.dataset.ms);
      inp.value = simSpeed;
      // Restart interval with new speed if running
      if (simInterval) {
        clearInterval(simInterval);
        simInterval = setInterval(fetchNextBall, simSpeed);
      }
    });
  });
}

async function setupStartForm() {
  const form = document.getElementById("setupForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const batTeam  = document.getElementById("l_batting_team").value;
    const bowlTeam = document.getElementById("l_bowling_team").value;
    if (batTeam === bowlTeam) {
      showToast("Teams must be different!", "red");
      return;
    }

    const payload = {
      match_type:   document.getElementById("l_match_type").value,
      batting_team: batTeam,
      bowling_team: bowlTeam,
      venue:        document.getElementById("l_venue").value,
      target:       parseInt(document.getElementById("l_target").value),
    };

    simSpeed = parseInt(document.getElementById("sim_speed").value);

    try {
      await fetch("/api/start-live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      // Show match section, hide setup
      document.getElementById("setupSection").classList.add("hidden");
      document.getElementById("matchSection").classList.remove("hidden");

      // Clear log
      document.getElementById("ballLog").innerHTML = "";
      prevData = null;

      // Init chart
      initChart(batTeam, bowlTeam);

      // Init scoreboard labels
      document.getElementById("lv_batting_team").textContent = batTeam;
      document.getElementById("lv_bowl_name").textContent    = bowlTeam;
      document.getElementById("lv_bat_name").textContent     = batTeam;
      document.getElementById("legend_bat").textContent      = batTeam;
      document.getElementById("legend_bowl").textContent     = bowlTeam;

      startSim();
    } catch (err) {
      showToast("Failed to start match", "red");
    }
  });
}

function setupControls() {
  const pauseBtn = document.getElementById("pauseBtn");
  const resetBtn = document.getElementById("resetBtn");

  pauseBtn.addEventListener("click", () => {
    if (!matchActive) return;
    isPaused = !isPaused;
    pauseBtn.textContent = isPaused ? "▶️ Resume" : "⏸ Pause";
  });

  resetBtn.addEventListener("click", () => {
    if (simInterval) clearInterval(simInterval);
    simInterval = null;
    matchActive = false;
    isPaused = false;
    document.getElementById("matchSection").classList.add("hidden");
    document.getElementById("setupSection").classList.remove("hidden");
    prevData = null;
  });
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupFormatToggle();
  setupSpeedButtons();
  setupStartForm();
  setupControls();
});
