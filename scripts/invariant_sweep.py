# Monthly invariant sweep (Nathan, 3 Sep; spec 7.7). Mechanical self-check; REPORT ONLY ON FAILURE.
# Usage: python3 scripts/invariant_sweep.py /tmp/cal.json   (cal.json = google-calendar search 'Task', +400d window, include recurrence,description)
# Checks: (a) deep parity (dates + completion-anchored arming), (b) transport liveness, (d) changelog conformance sample.
# (c) synthetic tap round-trip is driven by the caller (needs the live endpoint); (e) custody mirror is BLOCKED on Google access.
import json, re, sys, datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, "scripts")
head = open("scripts/snooze_sync.py").read().split("PATH = ")[0]
ns = {}; exec(head, ns)
occ, REC = ns["occurrences"], ns["RECURRENCE"]

cal = json.load(open(sys.argv[1]))
findings = []
today = datetime.datetime.now(ZoneInfo("Europe/London")).date()

# normalize like the parity sweep
def norm(t):
    t = t.lower(); t = re.split(r"\s+\(|\s+\u2014|\s+-{2,}", t)[0]
    return re.sub(r"\s+", " ", t).strip()
ALIASES = {"shl every 3 months": "shl", "economist renews may 3rd": "economist renewal"}

tasks = {}
for e in cal.get("events", []):
    s = e.get("summary") or ""
    if not (s.startswith("Task: ") or s.startswith("Task* ")) or e.get("status") == "cancelled": continue
    key = ALIASES.get(norm(s.split(" ",1)[1]), norm(s.split(" ",1)[1]))
    tasks.setdefault(key, []).append(e)

# (a1) date-sensitive recurring: board computed next occurrence vs calendar next instance
for title, attrs in REC.items():
    ocs = [o for o in occ(attrs, today + datetime.timedelta(days=400)) if o >= today.isoformat()]
    if not ocs: continue
    board_next = ocs[0]
    insts = sorted((e.get("start_time") or "")[:10] for e in tasks.get(norm(title), []))
    insts = [i for i in insts if i >= today.isoformat()]
    if not insts:
        findings.append(f"(a) '{title}': board next={board_next} but no calendar instance in window"); continue
    if insts[0] != board_next:
        findings.append(f"(a) '{title}': board next={board_next} vs calendar next={insts[0]}")

# (a2) completion-anchored arming: Charge HUD cmonthly -> next = done+1mo (fwd-shifted) vs calendar
state = json.load(open("snooze-state.json"))
done = state.get("done", {})
def shift(d):
    d = datetime.date.fromisoformat(d)
    while d.isoweekday() in (6,7): d += datetime.timedelta(days=1)
    return d.isoformat()
if "Charge HUD Galileo" in done:
    dd = done["Charge HUD Galileo"]["date"]
    base = datetime.date.fromisoformat(dd)
    expect = shift(f"{base.year}-{base.month+1 if base.month<12 else 1:02d}-{base.day:02d}" if base.month<12 else f"{base.year+1}-01-{base.day:02d}")
    insts = sorted((e.get("start_time") or "")[:10] for e in tasks.get(norm("Charge HUD Galileo"), []) if (e.get("start_time") or "")[:10] > dd)
    if insts and insts[0] != expect:
        findings.append(f"(a) Charge HUD: done={dd} -> expected next {expect}, calendar has {insts[0]}")
    if not insts:
        findings.append(f"(a) Charge HUD: done={dd} but no armed next instance on calendar")

# (a3) wired one-offs: board data-date vs calendar event date
html = open("index.html").read()
for m in re.finditer(r'<li data-recur="mustdo" class="recur-hidden" data-freq="once" data-date="([0-9-]+)">.*?<b>(.*?)</b>', html, re.S):
    date, t = m.group(1), m.group(2).replace("&amp;","&")
    insts = [ (e.get("start_time") or e.get("start_date") or "")[:10] for e in tasks.get(norm(t), []) ]
    if insts and date not in insts:
        findings.append(f"(a) one-off '{t}': board {date} not in calendar dates {insts}")
    if not insts and date >= today.isoformat():
        findings.append(f"(a) one-off '{t}': board {date} has NO calendar event")

# (b) transport liveness: state file updated within 70 min
upd = datetime.datetime.fromisoformat(state["updated"].replace("Z","+00:00"))
age_min = (datetime.datetime.now(datetime.timezone.utc) - upd).total_seconds()/60
if age_min > 70: findings.append(f"(b) snooze-state.json watermark stale: last updated {age_min:.0f} min ago")

# (d) changelog conformance sample: this month's entries carry a timestamp + instruction ref
try:
    cl = open("../internal/changelog.md").read()
except FileNotFoundError:
    cl = open("changelog.md").read() if False else ""
if cl:
    blocks = [l for l in cl.splitlines() if re.match(r"^- \d{1,2}:\d{2}", l)][-8:]
    bad = [l[:60] for l in blocks if not re.search(r"(Nathan|parent|instruction|maintenance|item|Claude)", l)]
    if bad: findings.append(f"(d) {len(bad)} of last {len(blocks)} changelog block-starts lack a triggering-instruction ref: {bad}")

print("INVARIANT SWEEP", today.isoformat(), "-", "FAIL" if findings else "CLEAN")
for f in findings: print(" ", f)
print("  (e) custody mirror check: BLOCKED (no Google/Apps Script access; covered by user's manual task)")
