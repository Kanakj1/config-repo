# ExamPortal DoS Demo
### Flash Crowd vs Malicious DoS — A College Portal Scenario

---

## Project Files

```
college_dos/
├── server.py        ← Flask student portal (the "victim system")
├── flash_crowd.py   ← Legitimate students rushing during exam time
├── attacker.py      ← Malicious DoS attacker
├── dashboard.html   ← Live visual dashboard (open via localhost:8080)
├── requirements.txt ← Python dependencies
└── README.md        ← This file
```

---

## Setup (Do This Once)

### 1. Make sure Python 3.8+ is installed
```
python --version
```

### 2. Install dependencies
Navigate to the `college_dos` folder in a terminal and run:
```
pip install -r requirements.txt
```

---

## Running the Demo (4 Terminals + 2 Browser Tabs)

| Window | Command | Purpose |
|--------|---------|---------|
| Terminal 1 | `python server.py` | The student portal server |
| Terminal 2 | `python -m http.server 8080` | Serve the dashboard file |
| Terminal 3 | `python flash_crowd.py` | Legitimate student flood |
| Terminal 4 | `python attacker.py` | Malicious attacker |
| Browser Tab 1 | `http://localhost:8080/dashboard.html` | Live monitor |
| Browser Tab 2 | `http://127.0.0.1:5000/download` | The heavy endpoint |

---

## Step-by-Step Demo Sequence

### PHASE 1 — Normal Operation (2 min)

1. Start Terminal 1: `python server.py`
2. Start Terminal 2: `python -m http.server 8080`
3. Open `http://localhost:8080/dashboard.html`
4. Open `http://127.0.0.1:5000` in another tab
5. Browse around: Dashboard → Marks → Assignments → Question Paper
6. Show the audience: responses are fast (50–150ms), dashboard shows low RPS
7. **Say Phase 1 script** (see below)

### PHASE 2 — Flash Crowd (2 min)

1. Open Terminal 3 and run: `python flash_crowd.py`
2. Press Enter to begin
3. Watch the dashboard — RPS climbs, Avg Response starts rising
4. Try refreshing the Question Paper page — it gets slower
5. Show comparison table updating in dashboard
6. **Say Phase 2 script** (see below)

### PHASE 3 — DoS Attack (2 min)

1. Keep flash_crowd.py running!
2. Open Terminal 4 and run: `python attacker.py`
3. Press Enter to begin
4. Now watch the dashboard — RPS spikes dramatically
5. Try loading the Question Paper — it times out or takes 1–2 seconds
6. The "UNDER ATTACK" badge flashes
7. **Say Phase 3 script** (see below)

### PHASE 4 — Defense (2 min)

1. Click **"TOGGLE DEFENSE"** in the dashboard
2. Watch Blocked (429) counter climb rapidly
3. Response time starts dropping
4. Server becomes usable again
5. The comparison table now shows all 4 phases
6. **Say Phase 4 script** (see below)

### RESET for Another Run
- Click **RESET ALL** in the dashboard
- Press Ctrl+C in Terminals 3 and 4
- Re-run flash_crowd.py and attacker.py

---

## Complete Spoken Demo Script

### PHASE 1 — Normal
> "What you're seeing here is a simple college student portal — similar to
> what you'd use to check marks, submit assignments, or download exam papers.
> Right now, the server is healthy. Each page loads in under 150 milliseconds.
> The dashboard on the left shows a flat RPS line, meaning the server is
> barely under any load. This is day-to-day normal operation."

### PHASE 2 — Flash Crowd
> "Now let's simulate something that happens every semester without any
> hacker involvement. The college announces: 'Exam begins in 15 minutes,
> download your question paper now.' Every student — all 80 of them —
> tries to download the paper at the exact same moment.
>
> Watch the RPS graph. It's climbing. The average response time is rising too.
> Refresh the download page — see how it takes longer now? No one is attacking
> the system. These are real, legitimate users. But 80 people hitting one
> endpoint at the same time is still enough to degrade the server.
>
> This is called a FLASH CROWD. It's an accidental denial of service.
> The cause is human behavior, not malicious intent."

### PHASE 3 — DoS Attack
> "Now a bad actor enters the picture. They notice the portal is already
> struggling. So they launch an automated attack — 200 threads, all firing
> requests at the download endpoint as fast as possible.
>
> Look at the RPS graph — it's completely different now. We went from 20–30
> requests per second to hundreds. The attacker doesn't even need the paper.
> They just want to make sure no one ELSE can get it either.
>
> Try loading the question paper page now... it either times out or takes
> two full seconds to respond. For a student sitting in an exam hall waiting
> to download their paper — that's a real problem.
>
> This is the difference between a flash crowd and a DoS attack: one is
> accidental, the other is intentional. But the effect on the server is
> the same — or worse."

### PHASE 4 — Defense
> "So what can we do about it? Click the TOGGLE DEFENSE button.
>
> What just happened? The server now tracks how many requests each IP address
> sends per 5-second window. If any IP sends more than 8 requests in 5 seconds,
> it gets a 429 — Too Many Requests — error.
>
> Watch the Blocked counter — those are attacker requests being turned away.
> Watch the RPS on the graph — it's dropping. Watch the response time — coming
> back down to a reasonable level.
>
> The comparison table now shows all four states. A legitimate student sending
> one request per few seconds is completely unaffected. The attacker sending
> 50 requests per second is blocked.
>
> In the real world, this concept is implemented in NGINX, AWS WAF, Cloudflare —
> all of them use rate limiting and traffic analysis as their first line of
> defense against DoS and DDoS attacks."

---

## How the Defense Works (Simple Explanation)

```
Each IP address gets a "ticket list"
Each request → add a timestamp to that IP's list
Remove timestamps older than 5 seconds
If list length >= 8 → REJECT (429)
If list length < 8  → SERVE the request

A student making 1 request every few seconds:  list = [now] → LENGTH 1 → ✔ SERVED
An attacker firing 50 req/sec:                 list = [t,t,t,t,t,t,t,t...] → LENGTH 8+ → ✗ BLOCKED
```

---

## Tips for a Professional Presentation

1. **Layout**: Use two monitors — portal + attack scripts on one, dashboard on the other
2. **Zoom**: Set dashboard browser zoom to 110% so graphs are clearly visible
3. **Dramatic pause**: Let Phase 3 run for 60 seconds before enabling defense — the buildup is key
4. **Show the terminal**: The attack.py terminal with its ASCII display is visually impressive
5. **Live server log**: Run `tail -f portal.log` in a 5th terminal to show raw server logs
6. **Rehearse once**: Do one silent dry run so you know the timing before presenting
7. **More drama**: Use `python attacker.py --threads 350` for a bigger spike

---

## Flash Crowd vs DoS — Quick Reference Card

| Property | Flash Crowd | DoS Attack |
|----------|------------|------------|
| Intent | Innocent | Malicious |
| Source | Real users | Automated bots |
| Cause | Human behavior (exam time) | Deliberate overload |
| Pattern | Sudden spike, then drops | Sustained continuous flood |
| Solution | Scaling, queuing, CDN | Rate limiting, IP blocking, WAF |
| Example | Students downloading paper | Attacker using threading scripts |

Both produce the same result: server becomes slow or unresponsive for legitimate users.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dashboard shows "Server unreachable" | Must open via `http://localhost:8080/dashboard.html`, not by double-clicking the file |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Port 5000 in use | Change port in server.py line: `app.run(port=5001)` |
| Attack has no visible effect | Increase threads: `python attacker.py --threads 400` |
| Flash crowd too mild | Increase students: `python flash_crowd.py --students 150` |
