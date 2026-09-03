#!/usr/bin/env python3
"""Drain-side check for the agent peer channel (spec 7.8).

Reads ~/board/internal/AGENT-LOG.md. Prints claude entries newer than
instinct's LAST_READ mark. With --mark, advances instinct's mark to the
newest claude entry seen (call only after the entries have been relayed).
Never touches claude's mark; never rewrites entries.
"""
import re, sys

LOG = '/home/sandbox/board/internal/AGENT-LOG.md'
ENTRY = re.compile(r'^- \[(?P<ts>[^\]]+)\] FROM: (?P<who>instinct|claude) - (?P<msg>.*)$')
MARK  = re.compile(r'^LAST_READ: instinct=(?P<i>\S+?), claude=(?P<c>\S+)\s*$')

def main():
    lines = open(LOG).read().splitlines()
    mark_i = ''
    for l in lines:
        m = MARK.match(l)
        if m: mark_i = m.group('i')
    new = [l for l in lines if (e := ENTRY.match(l)) and e.group('who') == 'claude' and e.group('ts') > mark_i]
    for l in new: print(l)
    if '--mark' in sys.argv and new:
        newest = max(ENTRY.match(l).group('ts') for l in new)
        out = [MARK.sub(f'LAST_READ: instinct={newest}, claude=\\g<c>', l) if MARK.match(l) else l for l in lines]
        open(LOG, 'w').write('\n'.join(out) + '\n')
        print(f'MARKED instinct={newest}', file=sys.stderr)

if __name__ == '__main__':
    main()
