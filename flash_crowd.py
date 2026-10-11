"""
CollegePortal DoS Demo — flash_crowd.py
=========================================
Simulates a LEGITIMATE flash crowd:
  - Students suddenly rush to download the question paper at exam time
  - All requests are "real" students (no malicious intent)
  - Still causes server overload due to sheer volume

Usage:
  python flash_crowd.py                  # 80 concurrent students (default)
  python flash_crowd.py --students 150   # more students
"""

import threading, requests, time, argparse, os, random

parser = argparse.ArgumentParser()
parser.add_argument("--students", type=int, default=80)
parser.add_argument("--url",      default="http://127.0.0.1:5000")
args = parser.parse_args()

URL      = args.url
STUDENTS = args.students
TIMEOUT  = 10

# Fake student names for realistic logging
NAMES = [
    "Rahul Sharma","Priya Nair","Aman Verma","Sneha Patil","Rohan Mehta",
    "Ananya Iyer","Karan Gupta","Divya Reddy","Arjun Singh","Pooja Joshi",
    "Vikram Das","Neha Tiwari","Saurabh Rao","Meera Pillai","Nikhil Bose",
    "Tanvi Shah","Abhishek Kumar","Riya Malhotra","Harsh Pandey","Kavya Nambiar",
]

lock    = threading.Lock()
sent    = 0
success = 0
slow    = 0   # responses > 500ms
failed  = 0
stop    = threading.Event()

# ── Colors ────────────────────────────────────────────────────────────────────
def C(t, code): return f"\033[{code}m{t}\033[0m"
G = lambda t: C(t,"92"); Y = lambda t: C(t,"93")
R = lambda t: C(t,"91"); B = lambda t: C(t,"96")
BOLD = lambda t: C(t,"1"); DIM = lambda t: C(t,"2")

BAR_W = 38
def bar(v, mx, char="█", empty="░"):
    f = int(BAR_W * min(v, mx) / mx) if mx else 0
    return char * f + empty * (BAR_W - f)

def clear(): os.system("cls" if os.name=="nt" else "clear")

# ── Worker ────────────────────────────────────────────────────────────────────
def student_worker(name, student_id):
    global sent, success, slow, failed
    session = requests.Session()
    # Each student browses a bit first (realistic), then downloads
    pages = ["/dashboard", "/marks", "/download?kind=student"]
    for page in pages:
        if stop.is_set(): return
        t0 = time.time()
        try:
            r   = session.get(URL + page, timeout=TIMEOUT)
            ms  = round((time.time()-t0)*1000)
            with lock:
                sent += 1
                if r.status_code == 200:
                    success += 1
                    if ms > 500: slow += 1
                else:
                    failed += 1
        except Exception:
            with lock:
                sent   += 1
                failed += 1
        time.sleep(random.uniform(0.2, 0.8))   # human-like pacing

# ── Display ───────────────────────────────────────────────────────────────────
def display():
    start = time.time()
    while not stop.is_set():
        time.sleep(0.8)
        now     = time.time()
        elapsed = int(now - start)
        with lock:
            s, ok, sl, fa = sent, success, slow, failed

        clear()
        print(B("╔══════════════════════════════════════════════════════╗"))
        print(B("║") + Y("  📚 FLASH CROWD SIMULATOR — Exam Paper Download     ") + B("║"))
        print(B("╚══════════════════════════════════════════════════════╝"))
        print(f"\n  Scenario : {BOLD('Exam starts in 15 minutes — all students rush to download')}")
        print(f"  Students : {BOLD(str(STUDENTS))}  |  Elapsed: {elapsed}s")
        print()
        print(f"  {BOLD('REQUESTS SENT')}   {B(str(s)):>8}   {DIM(bar(s, STUDENTS*3))}")
        print(f"  {G('SUCCESSFUL')}    {G(str(ok)):>8}   {DIM(bar(ok, STUDENTS*3))}")
        print(f"  {Y('SLOW (>500ms)')} {Y(str(sl)):>8}   {DIM(bar(sl, STUDENTS))}")
        print(f"  {R('FAILED/TIMEOUT')}{R(str(fa)):>8}   {DIM(bar(fa, STUDENTS))}")
        print()
        if sl > 5:
            print(f"  {Y('⚠  Server slowing down due to flash crowd!')}")
        if fa > 10:
            print(f"  {R('✗  Server dropping requests — overloaded!')}")
        print()
        print(DIM("  Ctrl+C to stop"))

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Tell server we're in flash-crowd phase
    try:
        requests.get(f"{URL}/set-phase/flash", timeout=3)
    except: pass

    clear()
    print(B("\n╔════════════════════════════════════════════╗"))
    print(B("║") + Y("   📚 FLASH CROWD SIMULATOR") + B("                 ║"))
    print(B("╚════════════════════════════════════════════╝"))
    print(f"\n  Simulating {BOLD(str(STUDENTS))} students downloading the exam paper")
    print(f"  Target: {BOLD(URL)}")
    print(f"\n  {Y('This represents LEGITIMATE traffic — no malicious intent.')}")
    print(f"  {Y('The server overloads simply because too many real users')}")
    print(f"  {Y('hit it at the same time (exam announcement effect).')}")
    print()
    input(f"  Press {BOLD('Enter')} to simulate the flash crowd...")

    threads = []
    for i in range(STUDENTS):
        name = NAMES[i % len(NAMES)] + f" #{i+1}"
        sid  = f"NU2024{i+1:03d}"
        t    = threading.Thread(target=student_worker, args=(name, sid), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(random.uniform(0.01, 0.05))   # staggered start, like a real crowd

    try:
        display()
    except KeyboardInterrupt:
        stop.set()
        # Reset phase
        try: requests.get(f"{URL}/set-phase/normal", timeout=2)
        except: pass
        print(G("\n  Flash crowd stopped."))
        time.sleep(0.5)
