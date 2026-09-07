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
    "Nudge Fairley House re Asa accommodations response": "mustdo",
    "Hire 2026 US CPA + open Claude Tax project for handoff brief": "mustdo",
    "Change Maison Estelle membership to just main club": "mustdo",
    "Custody script integrity check (editor access + Libraries)": "mustdo",
    "Design agent peer channel (Claude <-> Instinct)": "mustdo",
}

# LATE-DONE GUARD (Nathan, 2 Sep 23:52, spec 5.1): date-sensitive recurring items only.
# Mirrors the occurrence engine in index.html (lastOccurrence): raw occurrence dates per the
# li data attrs, shifted FORWARD off weekends to Monday; anchor filters pre-anchor months/dates;
# FLOOR 2026-09-02 (pre-floor occurrences assumed handled). If an li's data attrs change, update here.
# cmonthly (completion-anchored), freq=once, and habits are exempt from the guard.
FLOOR = "2026-09-02"
RECURRENCE = {  # title -> attrs, copied from index.html li data-* (2 Sep)
    "Pay quarterly taxes":            {"freq":"monthday","interval":3,"day":4,"anchor":"2026-09-04"},
    "Schedule annual with Dr Sera Shoukru (new GP)": {"freq":"yearly-ordinal","month":9,"ordinal":2,"weekday":2},
    "Last Month CMAs to Pocketsmith": {"freq":"ordinal","interval":1,"ordinal":1,"weekday":1},
    "Financial account security hygiene": {"freq":"ordinal","interval":1,"ordinal":2,"weekday":3},
    "Contact Don Caskey - Baktus D&O": {"freq":"yearly-ordinal","month":9,"ordinal":2,"weekday":5},
    "Moth trap check":                {"freq":"ordinal","interval":1,"ordinal":1,"weekday":1},
    "Consider employing boys":        {"freq":"yearly-ordinal","month":9,"ordinal":2,"weekday":1},
    "Start SAD light therapy":        {"freq":"yearly-ordinal","month":10,"ordinal":1,"weekday":4},
    "Extend UK credit card Travel Notice on Visa 0205": {"freq":"ordinal","interval":3,"ordinal":2,"weekday":1,"anchor":"2026-10-12"},
    "Delete nw@nathanwolfe.net":      {"freq":"ordinal","interval":6,"ordinal":2,"weekday":3,"anchor":"2026-10-14"},
    "SHL":                            {"freq":"ordinal","interval":3,"ordinal":2,"weekday":2,"anchor":"2026-11-10"},
    "Set up fidelity emails $15k":    {"freq":"yearly-ordinal","month":11,"ordinal":2,"weekday":4},
    "Calendly BST":                   {"freq":"yearly-ordinal","month":2,"ordinal":-1,"weekday":5},
    "Keep or cancel koko":            {"freq":"yearly-ordinal","month":4,"ordinal":2,"weekday":4},
    "Economist renewal":              {"freq":"yearly-ordinal","month":4,"ordinal":-1,"weekday":4},
    "Pay rent 36 Gloucester":         {"freq":"monthday","interval":1,"day":5,"anchor":"2027-01-05"},
}

def ordinal_date(y, m0, ord_, wd_js):
    # nth weekday (JS getDay numbering: Sun=0..Sat=6) of month m0 (0-based); ord_=-1 => last
    wd = 7 if wd_js == 0 else wd_js  # python isoweekday
    days = []
    d = datetime.date(y, m0+1, 1)
    while d.month == m0+1:
        if d.isoweekday() == wd: days.append(d)
        d += datetime.timedelta(days=1)
    return days[ord_-1] if ord_ > 0 else days[-1]

def shift_fwd(d):
    while d.isoweekday() in (6, 7): d += datetime.timedelta(days=1)
    return d

def occurrences(attrs, upto):
    # displayed occurrence dates (weekend-shifted forward) in [FLOOR, upto], anchor-honoring
    f = attrs["freq"]; out = set()
    y0, y1 = int(FLOOR[:4]), upto.year
    anchor = attrs.get("anchor")
    if f in ("ordinal", "monthday"):
        iv = attrs.get("interval", 1)
        am = (int(anchor[:4]), int(anchor[5:7])-1) if anchor else None
        y, m = int(FLOOR[:4]), int(FLOOR[5:7])-1
        while (y, m) <= (upto.year, upto.month-1):
            raw = None
            if am:
                diff = (y*12+m) - (am[0]*12+am[1])
                if diff % iv != 0: raw = "skip"
            if raw != "skip":
                if f == "ordinal":
                    raw = ordinal_date(y, m, attrs["ordinal"], attrs["weekday"])
                else:
                    dim = [31,29 if y%4==0 and (y%100!=0 or y%400==0) else 28,31,30,31,30,31,31,30,31,30,31][m]
                    raw = datetime.date(y, m+1, min(attrs["day"], dim))
                if anchor and raw.isoformat() < anchor: raw = None
                if raw and FLOOR <= raw.isoformat() <= upto.isoformat():
                    out.add(shift_fwd(raw).isoformat())
            m += 1
            if m == 12: y, m = y+1, 0
    else:  # yearly / yearly-ordinal
        for y in range(y0, y1+1):
            mo = attrs["month"]-1
            if f == "yearly":
                raw = datetime.date(y, mo+1, attrs["day"])
            else:
                raw = ordinal_date(y, mo, attrs["ordinal"], attrs["weekday"])
            if FLOOR <= raw.isoformat() <= upto.isoformat():
                out.add(shift_fwd(raw).isoformat())
    return sorted(out)

PATH = "snooze-state.json"
today = datetime.datetime.now(ZoneInfo("Europe/London")).date().isoformat()
state = {"items": {}}
if os.path.exists(PATH):
    try: state = json.load(open(PATH))
    except Exception: pass
items = state.get("items", {})
flags = state.get("flags", [])
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
    if src in ("board-snooze", "board-unsnooze", "board-custom-snooze", "board-set", "board") and item and item not in seen:
        seen[item] = (t, src, q.get("until") or q.get("when"))
done = state.get("done", {})
flagged_keys = {(f.get("item"), f.get("ts")) for f in flags}
for item, (t, src, until) in seen.items():
    if src == "board" and item in RECURRING:
        cur = done.get(item)
        if not cur or cur.get("ts", "") < t:
            d = datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/London")).date()
            # late-done guard: date-sensitive recurring only (Nathan, 2 Sep 23:52)
            if item in RECURRENCE and (item, t) not in flagged_keys:
                prev = cur.get("date") if cur else None
                occs = occurrences(RECURRENCE[item], d)
                open_occs = [o for o in occs if not prev or o > prev]
                if len(open_occs) >= 2:
                    flags.append({"item": item, "ts": t, "tap_date": d.isoformat(),
                                  "first_open": open_occs[0], "would_close": open_occs[-1]})
                    flagged_keys.add((item, t))
                    print(f"LATE-DONE FLAG: {item} tap={d.isoformat()} first_open={open_occs[0]} would_close={open_occs[-1]}")
                    continue  # do NOT auto-close
            done[item] = {"date": d.isoformat(), "ts": t, "kind": RECURRING[item]}
        continue
    cur = items.get(item)
    if cur and cur.get("ts", "") >= t:
        continue
    if src in ("board-snooze", "board-custom-snooze", "board-set") and until:
        if RECURRING.get(item) == "habit":
            continue  # daily habits can't be snoozed (Nathan, 2 Sep)
        if src == "board-set":
            until = until[:10] + "T00:00"  # Set: hide until the date's morning - item resurfaces in Now on the date (Nathan, 2 Sep)
        items[item] = {"until": until, "ts": t}
    elif src == "board-unsnooze":
        items.pop(item, None)
cutoff_habit = today
cutoff_mustdo = (datetime.date.fromisoformat(today) - datetime.timedelta(days=366)).isoformat()
done = {k: v for k, v in done.items() if v.get("date", "") >= (cutoff_habit if v.get("kind") == "habit" else cutoff_mustdo)}
state["done"] = done
items = {k: v for k, v in items.items() if v.get("until", "") >= today}
state["items"] = items
state["flags"] = flags
state["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
json.dump(state, open(PATH, "w"), indent=1)
print("state:", json.dumps(items), "done:", json.dumps(done), "flags:", json.dumps(flags))
