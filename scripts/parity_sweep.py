# Calendar parity sweep (Nathan, 3 Sep 00:26, maintenance follow-up item 4).
# Diff Task:/Task* events on the primary calendar against board lines.
#  - calendar task missing from the board -> ADD (note carried verbatim); one-offs wire directly,
#    series wire via RRULE->engine-attrs converter for known patterns, unsupported patterns FLAG
#  - calendar-backed board line whose event has vanished -> FLAG to Review page, never removed
# Exclusions: Pelacarsen (permanent, all surfaces) and Signature Pharmacy (retracted) are NEVER added.
# Run from repo root: python3 scripts/parity_sweep.py /tmp/cal.json   (cal.json = tools google-calendar search --include recurrence,description --json)
import json, re, sys, datetime

EXCLUDE = {"Pelacarsen lp(a) check", "Signature Pharmacy"}
# Calendar-backed board titles (mirror of internal/standing-rules.md list; update together).
CALENDAR_BACKED = {
    "HSBC cash run (counter service)", "Moth trap check", "Charge HUD Galileo", "Pay quarterly taxes",
    "Schedule annual with Dr Sera Shoukru (new GP)", "Last Month CMAs to Pocketsmith",
    "Financial account security hygiene", "Contact Don Caskey - Baktus D&O", "Consider employing boys",
    "Start SAD light therapy", "Extend UK credit card Travel Notice on Visa 0205",
    "Delete nw@nathanwolfe.net", "SHL", "Set up fidelity emails $15k", "Calendly BST",
    "Keep or cancel koko", "Economist renewal", "Pay rent 36 Gloucester",
    "Nudge Fairley House re Asa accommodations response",
    "Hire 2026 US CPA + open Claude Tax project for handoff brief",
    "Change Maison Estelle membership to just main club",
    "Custody script integrity check (editor access + Libraries)",
    "Design agent peer channel (Claude <-> Instinct)",
}
WD = {"SU":0,"MO":1,"TU":2,"WE":3,"TH":4,"FR":5,"SA":6}
# Calendar titles carry display suffixes/casing the board dropped; match on normalized form.
# Explicit aliases for variants normalization can't bridge (calendar normalized -> board normalized).
ALIASES = {"shl every 3 months": "shl", "economist renews may 3rd": "economist renewal"}
def norm(t):
    t = t.lower()
    t = re.split(r"\s+\(|\s+\u2014|\s+-{2,}", t)[0]
    return re.sub(r"\s+", " ", t).strip()

def esc(t):
    return (t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def rrule_to_attrs(rr, dtstart, note):
    """RRULE str -> engine data attrs for the known patterns, else None."""
    p = dict(kv.split("=",1) for kv in rr.split(";") if "=" in kv)
    f = p.get("FREQ"); iv = p.get("INTERVAL","1")
    anchor = f' data-anchor="{dtstart[:10]}"' if f in ("MONTHLY",) and iv != "1" else ""
    cmonthly = note and "completion-anchored" in note.lower()
    if cmonthly and f == "MONTHLY":
        return f'data-freq="cmonthly" data-interval="{iv}" data-date="{dtstart[:10]}"'
    if f == "MONTHLY" and "BYDAY" in p:
        m = re.fullmatch(r"(-?\d)([A-Z]{2})", p["BYDAY"])
        if not m: return None
        return f'data-freq="ordinal" data-interval="{iv}" data-ordinal="{m.group(1)}" data-weekday="{WD[m.group(2)]}"{anchor}'
    if f == "MONTHLY" and "BYMONTHDAY" in p:
        return f'data-freq="monthday" data-interval="{iv}" data-day="{p["BYMONTHDAY"]}"{anchor}'
    if f == "YEARLY" and "BYMONTH" in p and "BYMONTHDAY" in p:
        return f'data-freq="yearly" data-month="{p["BYMONTH"]}" data-day="{p["BYMONTHDAY"]}"'
    if f == "YEARLY" and "BYMONTH" in p and "BYDAY" in p:
        m = re.fullmatch(r"(-?\d)([A-Z]{2})", p["BYDAY"])
        if not m: return None
        return f'data-freq="yearly-ordinal" data-month="{p["BYMONTH"]}" data-ordinal="{m.group(1)}" data-weekday="{WD[m.group(2)]}"'
    return None

def dtlabel(dtstart):
    d = datetime.datetime.fromisoformat(dtstart)
    return d.strftime("%a %-d %b %H:%M")

def main(path):
    cal = json.load(open(path))
    events = cal.get("events", [])
    html = open("index.html").read()
    board_titles = set()
    for m in re.finditer(r"<b>(.*?)</b>", html, re.S):
        t = re.sub(r"<[^>]+>","",m.group(1)); t = re.sub(r"\s+"," ",t).strip()
        board_titles.add(norm(re.sub(r"^Task:\s*","",t.replace("&amp;","&"))))
    tasks = {}
    for e in events:
        s = e.get("summary") or ""
        if not (s.startswith("Task: ") or s.startswith("Task* ")): continue
        if e.get("status") == "cancelled": continue
        key = s.split(" ",1)[1].strip()
        nkey = ALIASES.get(norm(key), norm(key))
        if nkey not in tasks: tasks[nkey] = (key, e)
    wired, flags = [], []
    chip = '<a class="tapset" href="#set">set</a><a class="tapsnooze" href="#snooze">snooze</a><span class="snzmenu"><a data-days="1">1 day</a><a data-days="7">1 week</a><a data-days="custom">custom</a></span><a class="tapdone" href="#done" rel="noopener">done</a>'
    new_lis, new_map = [], []
    for nkey, (key, e) in tasks.items():
        if nkey in {norm(x) for x in EXCLUDE}:
            print(f"EXCLUDED (permanent): {key}"); continue
        if nkey in board_titles: continue
        rr = (e.get("recurrence") or [None])[0]
        start = e.get("start_time") or (e.get("start_date")+"T00:00:00+01:00")
        note = e.get("description") or ""
        if not rr:
            attrs = f'data-freq="once" data-date="{start[:10]}"'
        else:
            attrs = rrule_to_attrs(rr.split(":",1)[-1], start, note)
            if not attrs:
                flags.append(f"FLAG-SERIES: '{key}' RRULE '{rr}' has no engine mapping - needs manual wiring (rule 11)"); continue
        desc = f' <span class=d>{esc(re.sub(chr(10)+"+"," ",note).strip())}</span>' if note else ""
        new_lis.append(f'<li data-recur="mustdo" class="recur-hidden" {attrs}>{chip}<b>{esc(key)}</b> <span class=dt>- {dtlabel(start)}</span>{desc} </li>')
        new_map.append(f'    "{key.replace(chr(34), chr(34)*2)}": "mustdo",')
        wired.append(key)
    dry = "--dry-run" in sys.argv
    if new_lis:
        if dry:
            for k in wired: print(f"WOULD-WIRE: {k}")
        else:
            anchor = '<li data-recur="mustdo" class="recur-hidden" data-freq="once"'
            i = html.index(anchor)
            html = html[:i] + "\n".join(new_lis) + "\n" + html[i:]
            open("index.html","w").write(html)
            sp = open("scripts/snooze_sync.py").read()
            j = sp.index('    # one-off Task: events')
            sp = sp[:j] + "\n".join(new_map) + "\n" + sp[j:]
            open("scripts/snooze_sync.py","w").write(sp)
            for k in wired: print(f"WIRED: {k}")
    cal_keys = set(tasks)
    for key in sorted(CALENDAR_BACKED):
        if norm(key) not in cal_keys and key not in {w for w in wired}:
            flags.append(f"VANISHED: calendar-backed board line '{key}' has no live Task:/Task* event - flagged, NOT removed")
    if any(f.startswith("VANISHED") for f in flags) and not dry:
        rv = open("review.html").read()
        add = ""
        for f in flags:
            if f.startswith("VANISHED"):
                item = f.split("'")[1]
                if item not in rv:
                    add += f'<li><b>Parity flag ({datetime.date.today().isoformat()}):</b> {esc(item)} - calendar-backed but no live Task:/Task* event found; NOT removed from board (Nathan rule 3 Sep)</li>\n'
        if add:
            rv = rv.replace("</ul>", add + "</ul>", 1)
            open("review.html","w").write(rv)
            print("review.html updated with parity flags")
    for f in flags: print(f)
    if not wired and not flags: print("parity: clean")

if __name__ == "__main__":
    main(sys.argv[1])
