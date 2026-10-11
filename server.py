"""
CollegePortal DoS Demo — server.py
====================================
A realistic student portal with:
  - /             Login page
  - /dashboard    Student home (light)
  - /marks        Marks page (light)
  - /assignments  Assignments page (light)
  - /download     Question-paper download (HEAVY — simulates DB + file read)
  - /stats        JSON stats feed for the live dashboard
  - /toggle-defense  Enable/disable rate limiting
  - /set-phase    Tell server which demo phase we're in (for logging)
  - /reset        Reset all counters

Run:  python server.py
"""

from flask import Flask, jsonify, request, render_template_string
import time, threading, logging, random, string, os

app = Flask(__name__)

# ── Thread-safe shared state ─────────────────────────────────────────────────
_lock = threading.Lock()
state = {
    "phase":      "normal",   # normal | flash | attack
    "defense":    False,
    "start_time": time.time(),
    # counters
    "total":      0,
    "students":   0,   # legitimate (flash crowd)
    "attackers":  0,   # malicious
    "blocked":    0,
    "errors":     0,
    # response-time accumulator
    "rt_sum":     0.0,
    "rt_count":   0,
    # history for graph (one entry per second)
    "history":    [],  # [{t, rps, avg_ms, blocked_rps}]
}

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler("portal.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ── Background RPS tracker ───────────────────────────────────────────────────
_prev_total   = 0
_prev_blocked = 0
_prev_time    = time.time()

def _tracker():
    global _prev_total, _prev_blocked, _prev_time
    while True:
        time.sleep(1)
        now = time.time()
        with _lock:
            dt      = now - _prev_time
            rps     = round((state["total"]   - _prev_total)   / dt, 1) if dt else 0
            blk_rps = round((state["blocked"] - _prev_blocked) / dt, 1) if dt else 0
            avg_ms  = round(state["rt_sum"] / state["rt_count"] * 1000, 1) if state["rt_count"] else 0
            ts      = round(now - state["start_time"], 1)
            state["history"].append({"t": ts, "rps": rps, "avg_ms": avg_ms, "blk": blk_rps})
            if len(state["history"]) > 120:
                state["history"].pop(0)
            _prev_total   = state["total"]
            _prev_blocked = state["blocked"]
            _prev_time    = now
            state["rt_sum"]   = 0.0   # reset per-second accumulators
            state["rt_count"] = 0

threading.Thread(target=_tracker, daemon=True).start()

# ── Simple sliding-window rate limiter ───────────────────────────────────────
_rl: dict[str, list] = {}   # ip → [timestamps]
RL_WINDOW  = 5      # seconds
RL_MAX_REQ = 8      # max requests per window per IP

def _rate_limited(ip: str) -> bool:
    if not state["defense"]:
        return False
    now  = time.time()
    hits = [t for t in _rl.get(ip, []) if now - t < RL_WINDOW]
    if len(hits) >= RL_MAX_REQ:
        return True
    hits.append(now)
    _rl[ip] = hits
    return False

# ── Simulate server work ─────────────────────────────────────────────────────
def _work(base_ms: int) -> float:
    """Sleep for base_ms + load penalty, return actual seconds slept."""
    phase = state["phase"]
    # Under flash crowd: moderate slowdown
    # Under attack: severe slowdown (threads starved)
    penalty = 0.0
    if phase == "flash":
        penalty = random.uniform(0.05, 0.3)
    elif phase == "attack":
        penalty = random.uniform(0.3, 1.2)
    delay = base_ms / 1000 + penalty
    time.sleep(delay)
    return delay

def _record(ip: str, kind: str, delay: float, status: int):
    with _lock:
        state["total"] += 1
        if kind == "student":
            state["students"] += 1
        elif kind == "attacker":
            state["attackers"] += 1
        elif kind == "blocked":
            state["blocked"] += 1
        state["rt_sum"]   += delay
        state["rt_count"] += 1
    log.info(f"{kind.upper():8s}  {ip:15s}  {status}  {delay*1000:.0f}ms")

# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL PAGES
# ══════════════════════════════════════════════════════════════════════════════

STYLE = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&family=DM+Mono&display=swap');
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'DM Sans',sans-serif; background:#f0f4ff; color:#1a1f3a; min-height:100vh; }
  .topbar {
    background:#1a237e; color:#fff; padding:.9rem 2rem;
    display:flex; justify-content:space-between; align-items:center;
  }
  .topbar h1 { font-size:1.1rem; letter-spacing:1px; }
  .topbar span { font-size:.8rem; opacity:.7; }
  nav {
    background:#fff; border-bottom:1px solid #dde;
    padding:.6rem 2rem; display:flex; gap:1.4rem;
  }
  nav a { color:#1a237e; text-decoration:none; font-size:.85rem; font-weight:600; }
  nav a:hover { text-decoration:underline; }
  main { max-width:900px; margin:2rem auto; padding:0 1.5rem; }
  .card {
    background:#fff; border-radius:10px; padding:1.8rem 2rem;
    box-shadow:0 2px 16px #1a237e14; margin-bottom:1.4rem;
  }
  h2 { font-size:1.2rem; color:#1a237e; margin-bottom:1rem; }
  table { width:100%; border-collapse:collapse; font-size:.88rem; }
  th,td { padding:.55rem .8rem; text-align:left; border-bottom:1px solid #eef; }
  th { background:#f0f4ff; color:#1a237e; font-weight:600; }
  .badge { display:inline-block; padding:.2rem .6rem; border-radius:4px; font-size:.75rem; font-weight:600; }
  .green { background:#e6f9f0; color:#1a7a4a; }
  .blue  { background:#e8eeff; color:#1a237e; }
  .red   { background:#ffe8ec; color:#c0002a; }
  .btn {
    display:inline-block; background:#1a237e; color:#fff;
    padding:.7rem 1.6rem; border-radius:6px; font-size:.88rem;
    font-weight:600; text-decoration:none; cursor:pointer;
    border:none; margin-top:.8rem;
  }
  .btn:hover { background:#283593; }
  .btn.danger { background:#c0002a; }
  .timing { font-family:'DM Mono',monospace; font-size:.78rem; color:#888; margin-top:.8rem; }
</style>
"""

NAV = """
<nav>
  <a href="/dashboard">🏠 Dashboard</a>
  <a href="/marks">📊 Marks</a>
  <a href="/assignments">📋 Assignments</a>
  <a href="/download">📥 Question Paper</a>
</nav>
"""

@app.route("/")
def login():
    t0 = time.time()
    delay = _work(20)
    _record(request.remote_addr, "student", delay, 200)
    return render_template_string(STYLE + """
    <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f0f4ff;">
      <div style="background:#fff;padding:2.5rem 3rem;border-radius:12px;box-shadow:0 4px 32px #1a237e20;width:340px;">
        <div style="text-align:center;margin-bottom:1.5rem;">
          <div style="font-size:2rem;">🎓</div>
          <h2 style="color:#1a237e;font-size:1.3rem;margin:.5rem 0 .2rem;">ExamPortal</h2>
          <p style="font-size:.8rem;color:#888;">Northgate University</p>
        </div>
        <div style="margin-bottom:.9rem;">
          <label style="font-size:.8rem;color:#555;display:block;margin-bottom:.3rem;">Student ID</label>
          <input style="width:100%;padding:.6rem .8rem;border:1px solid #dde;border-radius:5px;font-size:.9rem;" value="NU2024001" readonly>
        </div>
        <div style="margin-bottom:1.2rem;">
          <label style="font-size:.8rem;color:#555;display:block;margin-bottom:.3rem;">Password</label>
          <input type="password" style="width:100%;padding:.6rem .8rem;border:1px solid #dde;border-radius:5px;font-size:.9rem;" value="••••••••" readonly>
        </div>
        <a href="/dashboard" class="btn" style="display:block;text-align:center;">Login →</a>
        <p class="timing">Page served in {{ ms }}ms</p>
      </div>
    </div>
    """ + STYLE, ms=round(delay*1000))

@app.route("/dashboard")
def dashboard():
    delay = _work(30)
    _record(request.remote_addr, "student", delay, 200)
    return render_template_string(STYLE + """
    <div class="topbar"><h1>🎓 ExamPortal — Northgate University</h1><span>Student: Rahul Sharma (NU2024001)</span></div>
    """ + NAV + """
    <main>
      <div class="card">
        <h2>📢 Notice Board</h2>
        <p style="background:#fff8e1;border-left:4px solid #ffc107;padding:.8rem 1rem;border-radius:4px;font-size:.88rem;">
          <strong>⚠ Exam Alert:</strong> Mid-semester question papers are now available for download under <em>Question Paper</em> tab.
          Exam begins at 10:00 AM. All students must download before 9:45 AM.
        </p>
      </div>
      <div class="card">
        <h2>📅 Today's Schedule</h2>
        <table>
          <tr><th>Time</th><th>Subject</th><th>Room</th><th>Status</th></tr>
          <tr><td>10:00 AM</td><td>Computer Networks</td><td>B-204</td><td><span class="badge green">Upcoming</span></td></tr>
          <tr><td>02:00 PM</td><td>Database Systems</td><td>A-101</td><td><span class="badge blue">Scheduled</span></td></tr>
        </table>
        <p class="timing">Loaded in {{ ms }}ms</p>
      </div>
    </main>
    """, ms=round(delay*1000))

@app.route("/marks")
def marks():
    delay = _work(25)
    _record(request.remote_addr, "student", delay, 200)
    return render_template_string(STYLE + """
    <div class="topbar"><h1>🎓 ExamPortal — Northgate University</h1><span>Student: Rahul Sharma</span></div>
    """ + NAV + """
    <main>
      <div class="card">
        <h2>📊 Semester Marks</h2>
        <table>
          <tr><th>Subject</th><th>Internal</th><th>Practical</th><th>Total</th><th>Grade</th></tr>
          <tr><td>Computer Networks</td><td>38/50</td><td>24/25</td><td>62/75</td><td><span class="badge green">A</span></td></tr>
          <tr><td>Database Systems</td><td>41/50</td><td>23/25</td><td>64/75</td><td><span class="badge green">A+</span></td></tr>
          <tr><td>Operating Systems</td><td>35/50</td><td>20/25</td><td>55/75</td><td><span class="badge blue">B+</span></td></tr>
          <tr><td>Cybersecurity</td><td>45/50</td><td>25/25</td><td>70/75</td><td><span class="badge green">O</span></td></tr>
        </table>
        <p class="timing">Loaded in {{ ms }}ms</p>
      </div>
    </main>
    """, ms=round(delay*1000))

@app.route("/assignments")
def assignments():
    delay = _work(25)
    _record(request.remote_addr, "student", delay, 200)
    return render_template_string(STYLE + """
    <div class="topbar"><h1>🎓 ExamPortal — Northgate University</h1><span>Student: Rahul Sharma</span></div>
    """ + NAV + """
    <main>
      <div class="card">
        <h2>📋 Assignments</h2>
        <table>
          <tr><th>Assignment</th><th>Subject</th><th>Due Date</th><th>Status</th></tr>
          <tr><td>Network Topology Lab</td><td>Computer Networks</td><td>Nov 20</td><td><span class="badge green">Submitted</span></td></tr>
          <tr><td>SQL Query Optimization</td><td>Database Systems</td><td>Nov 22</td><td><span class="badge blue">Pending</span></td></tr>
          <tr><td>Process Scheduling</td><td>Operating Systems</td><td>Nov 25</td><td><span class="badge red">Overdue</span></td></tr>
        </table>
        <p class="timing">Loaded in {{ ms }}ms</p>
      </div>
    </main>
    """, ms=round(delay*1000))

@app.route("/download")
def download():
    """
    The HEAVY endpoint — simulates:
      - Auth check
      - Database query to verify enrollment
      - Reading a large file from disk
      - Generating a download token
    This is the bottleneck that causes DoS under flash crowd / attack.
    """
    ip   = request.remote_addr
    kind = request.args.get("kind", "student")   # student | attacker

    # Rate limiting check
    if _rate_limited(ip):
        with _lock:
            state["blocked"] += 1
            state["total"]   += 1
        log.warning(f"BLOCKED   {ip:15s}  429  rate-limited")
        return render_template_string(STYLE + """
        <div class="topbar"><h1>🎓 ExamPortal</h1></div>""" + NAV + """
        <main><div class="card" style="border-left:4px solid #c0002a;">
          <h2 style="color:#c0002a;">⛔ 429 — Too Many Requests</h2>
          <p>You are sending requests too fast. Please wait a moment and try again.</p>
          <p style="margin-top:.6rem;font-size:.85rem;color:#888;">Rate limit: 8 requests per 5 seconds per IP</p>
        </div></main>
        """), 429

    # Simulate heavy server work (DB + file generation)
    delay = _work(150)

    # Generate fake paper content
    paper_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    _record(ip, kind, delay, 200)

    return render_template_string(STYLE + """
    <div class="topbar"><h1>🎓 ExamPortal — Northgate University</h1><span>Student: Rahul Sharma</span></div>
    """ + NAV + """
    <main>
      <div class="card">
        <h2>📥 Question Paper Download</h2>
        <p style="background:#e8f5e9;border-left:4px solid #43a047;padding:.8rem 1rem;border-radius:4px;font-size:.88rem;margin-bottom:1rem;">
          ✅ Authentication verified. Paper ready.
        </p>
        <table>
          <tr><th>Subject</th><td>Computer Networks (CN-401)</td></tr>
          <tr><th>Date</th><td>November 22, 2024</td></tr>
          <tr><th>Duration</th><td>3 Hours</td></tr>
          <tr><th>Max Marks</th><td>100</td></tr>
          <tr><th>Paper Token</th><td><code>{{ token }}</code></td></tr>
        </table>
        <a href="#" class="btn" style="margin-top:1rem;">⬇ Download PDF</a>
        <p class="timing">⏱ Server response time: <strong>{{ ms }}ms</strong>
          {% if ms > 500 %} &nbsp;<span style="color:#c0002a;">⚠ Server under load!</span>{% endif %}
        </p>
      </div>
    </main>
    """, token=paper_id, ms=round(delay*1000))

# ── Control & Stats endpoints ─────────────────────────────────────────────────

@app.route("/stats")
def stats():
    with _lock:
        elapsed = round(time.time() - state["start_time"], 1)
        rps = state["history"][-1]["rps"] if state["history"] else 0
        avg_ms = state["history"][-1]["avg_ms"] if state["history"] else 0
        return jsonify({
            "phase":    state["phase"],
            "defense":  state["defense"],
            "total":    state["total"],
            "students": state["students"],
            "attackers":state["attackers"],
            "blocked":  state["blocked"],
            "elapsed":  elapsed,
            "rps":      rps,
            "avg_ms":   avg_ms,
            "history":  state["history"][-60:],
        })

@app.route("/set-phase/<phase>")
def set_phase(phase):
    if phase not in ("normal", "flash", "attack"):
        return jsonify({"error": "unknown phase"}), 400
    with _lock:
        state["phase"] = phase
    log.info(f"PHASE → {phase.upper()}")
    return jsonify({"phase": phase})

@app.route("/toggle-defense")
def toggle_defense():
    with _lock:
        state["defense"] = not state["defense"]
        s = state["defense"]
    log.info(f"DEFENSE → {'ON' if s else 'OFF'}")
    return jsonify({"defense": s})

@app.route("/reset")
def reset():
    with _lock:
        state.update({
            "phase":"normal","defense":False,"start_time":time.time(),
            "total":0,"students":0,"attackers":0,"blocked":0,"errors":0,
            "rt_sum":0.0,"rt_count":0,"history":[],
        })
        _rl.clear()
    log.info("RESET")
    return jsonify({"ok": True})

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "═"*58)
    print("   COLLEGE PORTAL DoS DEMO SERVER")
    print("   Portal    →  http://127.0.0.1:5000")
    print("   Dashboard →  open dashboard.html via http://localhost:8080")
    print("   Stats API →  http://127.0.0.1:5000/stats")
    print("═"*58 + "\n")
    app.run(host="0.0.0.0", port=5000, threaded=True)
