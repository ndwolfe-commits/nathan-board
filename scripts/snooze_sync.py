import json, urllib.request, datetime, os
from zoneinfo import ZoneInfo
UUID = "974e7dc9-08e9-441f-844f-7ab514e13d17"
# Today's recurring items, by kind: "habit" (done/not-done, no carryover) or "mustdo" (rolls over until done or snoozed)
RECURRING = {
    "Cardio + strength": "habit", "Meditate": "habit",
    "Moth trap check": "mustdo", "Charge HUD Galileo": "mustdo", "Pay quarterly taxes": "mustdo",
    "Schedule annual with Dr Sera Shoukru (new GP)": "mustdo",
    "Last Month CMAs to Pocketsmith": "mustdo",
    "Financial account security hygiene": "mustdo",
    "Contact Don Caskey - Baktus D&O": "mustdo",
    "Consider employing boys": "mustdo", "Start SAD light therapy": "mustdo",
    "Extend UK credit card Travel Notice on Visa 0205": "mustdo",
    "Delete nw@nathanwolfe.net": "mustdo", "SHL": "mustdo",
    "Set up fidelity emails $15k": "mustdo", "Calendly BST": "mustdo",
    "Keep or cancel koko": "mustdo", "Economist renewal": "mustdo",
    "Pay rent 36 Gloucester": "mustdo",
    # one-off Task: events (due-date must-dos, done hides permanently via 366d keep)
    "London residence recital + chase judgment packet": "mustdo",
    "Nudge Fairley House re Asa accommodations response": "mustdo",
    "Breathing Microbiome Chichester": "mustdo",
    "Change fidelity beneficiaries": "mustdo",
    "Hire 2026 US CPA + open Claude Tax project for handoff brief": "mustdo",
    "Call Francesca": "mustdo",
    "Change Maison Estelle membership to just main club": "mustdo",
}
PATH = "snooze-state.json"
today = datetime.datetime.now(ZoneInfo("Europe/London")).date().isoformat()
state = {"items": {}}
if os.path.exists(PATH):
    try: state = json.load(open(PATH))
    except Exception: pass
items = state.get("items", {})
try:
    with urllib.request.urlopen(f"https://webhook.site/token/{UUID}/requests?sorting=newest&per_page=50", timeout=20) as r:
        data = json.load(r).get("data", [])
except Exception as e:
    print("beacon fetch failed:", e); data = []
seen = {}
for rec in data:
    q = rec.get("query") or {}
    src, item = q.get("src"), q.get("item")
    t = q.get("t") or rec.get("created_at", "")
    if src in ("board-snooze", "board-unsnooze", "board-custom-snooze", "board") and item and item not in seen:
        seen[item] = (t, src, q.get("until"))
done = state.get("done", {})
for item, (t, src, until) in seen.items():
    if src == "board" and item in RECURRING:
        cur = done.get(item)
        if not cur or cur.get("ts", "") < t:
            d = datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/London")).date().isoformat()
            done[item] = {"date": d, "ts": t, "kind": RECURRING[item]}
        continue
    cur = items.get(item)
    if cur and cur.get("ts", "") >= t:
        continue
    if src in ("board-snooze", "board-custom-snooze") and until:
        items[item] = {"until": until, "ts": t}
    elif src == "board-unsnooze":
        items.pop(item, None)
cutoff_habit = today
cutoff_mustdo = (datetime.date.fromisoformat(today) - datetime.timedelta(days=366)).isoformat()
done = {k: v for k, v in done.items() if v.get("date", "") >= (cutoff_habit if v.get("kind") == "habit" else cutoff_mustdo)}
state["done"] = done
items = {k: v for k, v in items.items() if v.get("until", "") >= today}
state["items"] = items
state["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
json.dump(state, open(PATH, "w"), indent=1)
print("state:", json.dumps(items), "done:", json.dumps(done))
