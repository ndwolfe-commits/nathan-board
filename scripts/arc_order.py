import json, urllib.request, html, re
UUID = "974e7dc9-08e9-441f-844f-7ab514e13d17"
ARC_TITLES = ["Security & insurance", "Boys activities", "Estate planning", "PocketSmith",
          "LinkedIn profile fixes", "Sell the blue circular sofa + Persian rug; donate clothes",
          "Linking", "Tock password", "Kids scuba"]
try:
    with urllib.request.urlopen(f"https://webhook.site/token/{UUID}/requests?sorting=newest&per_page=50", timeout=20) as r:
        data = json.load(r).get("data", [])
except Exception as e:
    print("beacon fetch failed:", e); data = []

def newest(srcname):
    best = None
    for rec in data:
        q = rec.get("query") or {}
        if q.get("src") != srcname:
            continue
        ts = int(q.get("ts") or 0)
        order = (q.get("order") or "").split("|")
        if ts and (not best or ts > best[0]):
            best = (ts, order)
    return best

def drain_arcs():
    best = newest("board-arcorder")
    if not best:
        print("no board-arcorder beacon"); return
    ts, order = best
    if sorted(order) != sorted(ARC_TITLES):
        print("IGNORED arcorder ts=%s: titles not a permutation of the 9 arcs: %s" % (ts, order)); return
    # index.html: reorder #arclist li[data-arc]
    s = open("index.html").read()
    m = re.search(r'(<ul id="arclist">)(.*?)(</ul>)', s, re.S)
    lis = re.findall(r'<li data-arc="([^"]*)">.*?</li>', m.group(2), re.S)
    if sorted(html.unescape(x) for x in lis) != sorted(ARC_TITLES):
        print("index arclist mismatch, skipping arcs:", lis); return
    cur_ts = re.search(r'<section class="cols" data-orderts="(\d+)">', s).group(1)
    if int(cur_ts) >= ts:
        print("arcorder already baked at ts", cur_ts); return
    blocks = {}
    for blk, attr in re.findall(r'(<li data-arc="([^"]*)">.*?</li>)', m.group(2), re.S):
        blocks[html.unescape(attr)] = blk
    s = s[:m.start(2)] + "\n" + "\n".join(blocks[t] for t in order) + "\n" + s[m.end(2):]
    s = s.replace('<section class="cols" data-orderts="%s">' % cur_ts, '<section class="cols" data-orderts="%d">' % ts)
    open("index.html", "w").write(s)
    # arcs.html: reorder section.arc blocks (nested sections -> scanner)
    a = open("arcs.html").read()
    starts = [mm.start() for mm in re.finditer(r'<section class="arc" data-arc="([^"]*)">', a)]
    def block_end(pos):
        depth = 0
        for mm in re.finditer(r'<section\b|</section>', a[pos:]):
            if mm.group(0) == '<section': depth += 1
            else:
                depth -= 1
                if depth == 0:
                    return pos + mm.end()
        raise ValueError("unbalanced")
    segs = {}
    for st in starts:
        attr = re.match(r'<section class="arc" data-arc="([^"]*)">', a[st:]).group(1)
        segs[html.unescape(attr)] = a[st:block_end(st)]
    if sorted(segs.keys()) != sorted(ARC_TITLES):
        print("arcs.html sections mismatch, skipping arcs:", sorted(segs.keys())); return
    a = a[:starts[0]] + "\n".join(segs[t] for t in order) + a[block_end(starts[-1]):]
    cur_ts2 = re.search(r'<div class="wrap" data-orderts="(\d+)">', a).group(1)
    a = a.replace('<div class="wrap" data-orderts="%s">' % cur_ts2, '<div class="wrap" data-orderts="%d">' % ts)
    open("arcs.html", "w").write(a)
    print("BAKED arc order ts=%d: %s" % (ts, " > ".join(order)))

def drain_now():
    best = newest("board-noworder")
    if not best:
        print("no board-noworder beacon"); return
    ts, order = best
    s = open("index.html").read()
    m = re.search(r'(<ol class="num" id="nowlist" data-orderts="(\d+)">)(.*?)(</ol>)', s, re.S)
    blocks = {}
    for blk in re.findall(r'<li>.*?</li>|<li [^>]*>.*?</li>', m.group(3), re.S):
        b = re.search(r'<b>(.*?)</b>', blk, re.S)
        t = re.sub(r'^Task:\s*', '', html.unescape(b.group(1)).strip())
        blocks[t] = blk
    if sorted(order) != sorted(blocks.keys()):
        print("IGNORED noworder ts=%s: not a permutation of current Now items (board: %s / beacon: %s)" % (ts, sorted(blocks.keys()), order)); return
    cur_ts = m.group(2)
    if int(cur_ts) >= ts:
        print("noworder already baked at ts", cur_ts); return
    s = s[:m.start(3)] + "\n" + "\n".join(blocks[t] for t in order) + "\n" + s[m.end(3):]
    s = s.replace('id="nowlist" data-orderts="%s"' % cur_ts, 'id="nowlist" data-orderts="%d"' % ts)
    open("index.html", "w").write(s)
    print("BAKED now order ts=%d: %s" % (ts, " > ".join(order)))

drain_arcs()
drain_now()
