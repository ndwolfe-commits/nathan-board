import json, urllib.request, html, re
UUID = "974e7dc9-08e9-441f-844f-7ab514e13d17"
TITLES = ["Security & insurance", "Boys activities", "Estate planning", "PocketSmith",
          "LinkedIn profile fixes", "Sell the blue circular sofa + Persian rug; donate clothes",
          "Linking", "Tock password", "Kids scuba"]
try:
    with urllib.request.urlopen(f"https://webhook.site/token/{UUID}/requests?sorting=newest&per_page=50", timeout=20) as r:
        data = json.load(r).get("data", [])
except Exception as e:
    print("beacon fetch failed:", e); raise SystemExit(0)
best = None
for rec in data:
    q = rec.get("query") or {}
    if q.get("src") != "board-arcorder":
        continue
    ts = int(q.get("ts") or 0)
    order = (q.get("order") or "").split("|")
    if ts and (not best or ts > best[0]):
        best = (ts, order)
if not best:
    print("no board-arcorder beacon"); raise SystemExit(0)
ts, order = best
if sorted(order) != sorted(TITLES):
    print("IGNORED arcorder ts=%s: titles not a permutation of the 9 arcs: %s" % (ts, order)); raise SystemExit(0)

def esc(t): return html.escape(t, quote=True)

# index.html: reorder #arclist li[data-arc]
s = open("index.html").read()
m = re.search(r'(<ul id="arclist">)(.*?)(</ul>)', s, re.S)
lis = re.findall(r'<li data-arc="([^"]*)">.*?</li>', m.group(2), re.S)
if sorted(html.unescape(x) for x in lis) != sorted(TITLES):
    print("index arclist mismatch, aborting:", lis); raise SystemExit(1)
cur_ts = re.search(r'<section class="cols" data-orderts="(\d+)">', s).group(1)
if int(cur_ts) >= ts:
    print("already baked at ts", cur_ts); raise SystemExit(0)
body = m.group(2)
blocks2 = {}
for blk, attr in re.findall(r'(<li data-arc="([^"]*)">.*?</li>)', body, re.S):
    blocks2[html.unescape(attr)] = blk
newbody = "\n".join(blocks2[t] for t in order)
s = s[:m.start(2)] + "\n" + newbody + "\n" + s[m.end(2):]
s = s.replace('<section class="cols" data-orderts="%s">' % cur_ts, '<section class="cols" data-orderts="%d">' % ts)
open("index.html", "w").write(s)

# arcs.html: reorder section.arc blocks (nested sections -> scanner)
a = open("arcs.html").read()
starts = [mm.start() for mm in re.finditer(r'<section class="arc" data-arc="([^"]*)">', a)]
def block_end(pos):
    depth = 0; i = pos
    for mm in re.finditer(r'<section\b|</section>', a[pos:]):
        tok = mm.group(0)
        if tok == '<section': depth += 1
        else:
            depth -= 1
            if depth == 0:
                return pos + mm.end()
    raise ValueError("unbalanced")
segs = {}
for st in starts:
    attr = re.match(r'<section class="arc" data-arc="([^"]*)">', a[st:]).group(1)
    segs[html.unescape(attr)] = a[st:block_end(st)]
if sorted(segs.keys()) != sorted(TITLES):
    print("arcs.html sections mismatch, aborting:", sorted(segs.keys())); raise SystemExit(1)
first, last = starts[0], block_end(starts[-1])
a = a[:first] + "\n".join(segs[t] for t in order) + a[last:]
cur_ts2 = re.search(r'<div class="wrap" data-orderts="(\d+)">', a).group(1)
a = a.replace('<div class="wrap" data-orderts="%s">' % cur_ts2, '<div class="wrap" data-orderts="%d">' % ts)
open("arcs.html", "w").write(a)
print("BAKED arc order ts=%d: %s" % (ts, " > ".join(order)))

# --- Now-list order (src=board-noworder): validate against current #nowlist titles, reorder, bump ts ---
best = None
for rec in data:
    q = rec.get("query") or {}
    if q.get("src") != "board-noworder":
        continue
    ts = int(q.get("ts") or 0)
    order = (q.get("order") or "").split("|")
    if ts and (not best or ts > best[0]):
        best = (ts, order)
if not best:
    print("no board-noworder beacon"); raise SystemExit(0)
ts, order = best
s = open("index.html").read()
m = re.search(r'(<ol class="num" id="nowlist" data-orderts="(\d+)">)(.*?)(</ol>)', s, re.S)
blocks2 = {}
for blk in re.findall(r'<li>.*?</li>|<li [^>]*>.*?</li>', m.group(3), re.S):
    b = re.search(r'<b>(.*?)</b>', blk, re.S)
    t = html.unescape(b.group(1)).strip()
    t = re.sub(r'^Task:\s*', '', t)
    blocks2[t] = blk
if sorted(order) != sorted(blocks2.keys()):
    print("IGNORED noworder ts=%s: not a permutation of current Now items (board: %s / beacon: %s)" % (ts, sorted(blocks2.keys()), order)); raise SystemExit(0)
cur_ts = m.group(2)
if int(cur_ts) >= ts:
    print("noworder already baked at ts", cur_ts); raise SystemExit(0)
newbody = "\n".join(blocks2[t] for t in order)
s = s[:m.start(3)] + "\n" + newbody + "\n" + s[m.end(3):]
s = s.replace('id="nowlist" data-orderts="%s"' % cur_ts, 'id="nowlist" data-orderts="%d"' % ts)
open("index.html", "w").write(s)
print("BAKED now order ts=%d: %s" % (ts, " > ".join(order)))
