import json, urllib.request, datetime, os
from zoneinfo import ZoneInfo
UUID = "974e7dc9-08e9-441f-844f-7ab514e13d17"
# Today's recurring items, by kind: "habit" (done/not-done, no carryover) or "mustdo" (rolls over until done or snoozed)
RECURRING = {"Cardio + strength": "habit", "Meditate": "habit"}
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
    if src in ("board-snooze", "board-unsnooze", "board") and item and item not in seen:
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
    if src == "board-snooze" and until:
        items[item] = {"until": until, "ts": t}
    elif src == "board-unsnooze":
        items.pop(item, None)
done = {k: v for k, v in done.items() if v.get("date", "") >= today}
state["done"] = done
items = {k: v for k, v in items.items() if v.get("until", "") >= today}
state["items"] = items
state["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
json.dump(state, open(PATH, "w"), indent=1)
print("state:", json.dumps(items), "done:", json.dumps(done))
